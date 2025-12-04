"""Mock Teraslice API server for testing and development."""

import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse


# Status definitions from state flow diagram
INITIAL_STATES = {"pending", "scheduling", "initializing"}
RUNNING_STATES = {"recovering", "running", "failing", "paused", "stopping"}
TERMINAL_STATES = {"rejected", "completed", "stopped", "terminated", "failed"}
NON_TERMINAL_STATES = INITIAL_STATES | RUNNING_STATES


def select_execution_status(age_seconds: int) -> str | None:
    """Select an appropriate execution status based on age.

    Simulates realistic state transitions:
    - Very recent (< 10s): INITIAL states (pending → scheduling → initializing)
    - Recent (10s - 1min): Mostly running, rarely recovering/failing
    - Older (> 1min): Overwhelmingly running, very rarely paused
    - stopping → stopped after 30-90s (returns None to indicate terminal)
    - recovering/failing are rare and transition back to running

    Args:
        age_seconds: Age of the execution context in seconds

    Returns:
        A status string from NON_TERMINAL_STATES, or None if should be terminal
    """
    if age_seconds < 3:
        # Very fresh - in pending state
        return "pending"
    elif age_seconds < 6:
        # Progressing through initial states
        return random.choice(["scheduling", "initializing"])
    elif age_seconds < 10:
        # Just transitioned to running or might still be initializing
        return random.choice(["initializing", "running", "running", "running"])
    elif age_seconds < 60:
        # Recently started - mostly running, very rarely other states
        # stopping only appears in the 30-90s window
        if 30 <= age_seconds <= 90:
            weights = [0.88, 0.04, 0.03, 0.03, 0.02]  # running, recovering, failing, stopping, paused
            statuses = ["running", "recovering", "failing", "stopping", "paused"]
        else:
            weights = [0.90, 0.04, 0.03, 0.03]  # running, recovering, failing, paused
            statuses = ["running", "recovering", "failing", "paused"]

        status = random.choices(statuses, weights=weights)[0]

        # If recovering/failing for too long, back to running
        if status in ["recovering", "failing"] and age_seconds > 120:
            return "running"

        return status
    else:
        # Long-running - overwhelmingly in running state
        # Very rarely in paused, almost never in recovering/failing
        # stopping jobs don't last this long - they transition to stopped
        weights = [0.97, 0.02, 0.005, 0.005]  # running, paused, recovering, failing
        status = random.choices(
            ["running", "paused", "recovering", "failing"],
            weights=weights
        )[0]

        # recovering/failing should have transitioned back to running by now
        if status in ["recovering", "failing"] and age_seconds > 300:
            return "running"

        return status


def generate_worker() -> dict[str, Any]:
    """Generate a mock worker."""
    return {
        "worker_id": random.randint(1, 100),
        "assignment": random.choice(["execution_controller", "worker"]),
        "pid": random.randint(1000, 99999),
    }


def generate_node(node_id: str) -> dict[str, Any]:
    """Generate a mock node."""
    total_slots = random.randint(5, 20)
    active_workers_count = random.randint(0, total_slots)

    return {
        "node_id": node_id,
        "hostname": f"worker-{random.randint(1, 100)}.example.com",
        "pid": random.randint(1000, 99999),
        "node_version": "v20.10.0",
        "teraslice_version": "v3.0.0",
        "total": total_slots,
        "state": "connected",
        "available": total_slots - active_workers_count,
        "active": [generate_worker() for _ in range(active_workers_count)],
    }


def generate_cluster_state() -> dict[str, dict[str, Any]]:
    """Generate mock cluster state."""
    num_nodes = random.randint(3, 8)
    nodes = {}

    for i in range(num_nodes):
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        nodes[node_id] = generate_node(node_id)

    return nodes


def generate_controller(ex_id: str, job_id: str, name: str, started: datetime, total_workers: int) -> dict[str, Any]:
    """Generate a mock execution controller for a running execution context.

    Args:
        ex_id: Execution context ID
        job_id: Job ID
        name: Job name
        started: When the execution started
        total_workers: Total workers requested by the execution context
    """
    # Workers that have joined - 95% of the time, all workers have joined
    if random.random() < 0.95:
        workers_joined = total_workers
    else:
        # Occasionally some workers haven't joined yet
        workers_joined = max(1, total_workers - random.randint(1, 3))

    # Workers currently active - 95% of the time, all joined workers are active
    if random.random() < 0.95:
        workers_active = workers_joined
    else:
        # Occasionally some workers are idle/disconnected
        workers_active = max(1, workers_joined - random.randint(1, 2))

    # Workers available = slots not yet filled
    workers_available = total_workers - workers_joined

    # Some workers may have disconnected and reconnected (rare)
    workers_disconnected = random.randint(0, min(2, workers_joined // 4))
    workers_reconnected = random.randint(0, workers_disconnected)

    # Calculate realistic slice statistics based on execution duration
    now = datetime.now()
    time_running_seconds = (now - started).total_seconds()

    # Processed slices increase steadily: ~1 slice per 10 seconds per worker
    # Add some variation but keep it growing with time
    base_processed = int((time_running_seconds / 10) * workers_active)
    processed = max(0, base_processed + random.randint(-base_processed // 10, base_processed // 10))

    # Failed slices: mostly 0, occasionally a small percentage of processed
    if random.random() < 0.90:  # 90% of the time, no failures
        failed = 0
    else:
        # 10% of the time, failures are 0.05-0.5% of processed slices
        failed = max(0, int(processed * random.uniform(0.0005, 0.005)))

    # Queued should equal the number of active workers (one slice per worker)
    queued = workers_active

    # Subslices and other stats related to processed
    subslices = int(processed * random.uniform(1.0, 1.5))  # Typically more subslices than slices

    return {
        "ex_id": ex_id,
        "job_id": job_id,
        "name": name,
        "workers_available": workers_available,
        "workers_active": workers_active,
        "workers_joined": workers_joined,
        "workers_reconnected": workers_reconnected,
        "workers_disconnected": workers_disconnected,
        "failed": failed,
        "subslices": subslices,
        "queued": queued,
        "slice_range_expansion": random.randint(0, 10),
        "processed": processed,
        "slicers": random.randint(1, 3),
        "subslice_by_key": random.randint(0, 100),
        "started": started.isoformat(),
    }


def generate_operation() -> dict[str, Any]:
    """Generate a mock operation."""
    op_types = ["elasticsearch_reader", "noop", "elasticsearch_bulk"]
    return {
        "_op": random.choice(op_types),
    }


def generate_job() -> dict[str, Any]:
    """Generate a mock job."""
    job_id = uuid.uuid4().hex
    created = datetime.now() - timedelta(days=random.randint(0, 30))
    updated = created + timedelta(hours=random.randint(0, 24))

    return {
        "name": f"job_{random.choice(['daily_etl', 'hourly_sync', 'export_data', 'process_logs'])}",
        "lifecycle": random.choice(["once", "persistent"]),
        "workers": random.randint(1, 20),
        "operations": [generate_operation() for _ in range(random.randint(2, 4))],
        "job_id": job_id,
        "_created": created.isoformat(),
        "_updated": updated.isoformat(),
        "_context": "ex",
        "active": random.choice([True, False]),
    }


def generate_slicer_stats(started: datetime, total_workers: int = 10) -> dict[str, Any]:
    """Generate mock slicer stats with a given start time and worker count.

    Args:
        started: When the execution started
        total_workers: Total workers for this execution
    """
    queuing_complete = None
    if random.random() > 0.5:
        queuing_complete = started + timedelta(minutes=random.randint(1, 60))

    # Workers that have joined - 95% of the time, all workers have joined
    if random.random() < 0.95:
        workers_joined = total_workers
    else:
        workers_joined = max(1, total_workers - random.randint(1, 3))

    # Workers currently active - 95% of the time, all joined workers are active
    if random.random() < 0.95:
        workers_active = workers_joined
    else:
        workers_active = max(1, workers_joined - random.randint(1, 2))

    # Calculate realistic slice statistics based on execution duration
    now = datetime.now()
    time_running_seconds = (now - started).total_seconds()
    job_duration = int(time_running_seconds)

    # Processed slices increase steadily: ~1 slice per 10 seconds per worker
    base_processed = int((time_running_seconds / 10) * workers_active)
    processed = max(0, base_processed + random.randint(-base_processed // 10, base_processed // 10))

    # Failed slices: mostly 0, occasionally a small percentage of processed
    if random.random() < 0.90:  # 90% of the time, no failures
        failed = 0
    else:
        failed = max(0, int(processed * random.uniform(0.0005, 0.005)))

    # Queued should equal the number of active workers (one slice per worker)
    queued = workers_active

    # Subslices and other stats related to processed
    subslices = int(processed * random.uniform(1.0, 1.5))

    return {
        "workers_active": workers_active,
        "workers_joined": workers_joined,
        "queued": queued,
        "job_duration": job_duration,
        "subslice_by_key": random.randint(0, 100),
        "failed": failed,
        "subslices": subslices,
        "slice_range_expansion": random.randint(0, 10),
        "processed": processed,
        "workers_available": total_workers - workers_joined,
        "workers_reconnected": random.randint(0, min(2, workers_joined // 4)),
        "workers_disconnected": random.randint(0, min(2, workers_joined // 4)),
        "slicers": random.randint(1, 3),
        "started": started.isoformat(),
        "queuing_complete": queuing_complete.isoformat() if queuing_complete else None,
    }


def generate_execution_context(job: dict[str, Any], status: str, age_seconds: int = 0) -> dict[str, Any]:
    """Generate a mock execution context based on a job with a specific status and age.

    Args:
        job: The parent job
        status: Execution status
        age_seconds: How old the execution is (seconds ago it was created)
    """
    ex_id = uuid.uuid4().hex
    now = datetime.now()

    # Calculate creation time based on age
    created = now - timedelta(seconds=age_seconds)

    # Updated time is recent for non-terminal, older for terminal
    if status in NON_TERMINAL_STATES:
        # Non-terminal: updated recently (last few seconds)
        updated = now - timedelta(seconds=random.randint(0, 5))
    else:
        # Terminal: updated when it finished (some time ago)
        updated = created + timedelta(seconds=random.randint(60, age_seconds // 2))

    # Determine started time
    # For non-terminal: used for controller
    # For terminal: used for final slicer_stats
    started = None
    if status in NON_TERMINAL_STATES or status in TERMINAL_STATES:
        # Started shortly after creation
        # Handle edge case where age_seconds is 0 or very small
        max_offset = max(1, min(60, age_seconds))
        started = created + timedelta(seconds=random.randint(0, max_offset))

    return {
        "ex_id": ex_id,
        "job_id": job["job_id"],
        "name": job["name"],  # Same name as job
        "lifecycle": job["lifecycle"],  # Same lifecycle as job
        "analytics": random.choice([True, False]),
        "max_retries": random.randint(0, 5),
        "probation_window": random.randint(0, 300000),
        "slicers": random.randint(1, 3),
        "workers": job["workers"],  # Same worker count as job
        "operations": job["operations"],  # Same operations as job
        "_created": created.isoformat(),
        "_updated": updated.isoformat(),
        "_context": "ex",
        "_status": status,
        "slicer_hostname": f"worker-{random.randint(1, 100)}.example.com" if status in NON_TERMINAL_STATES else None,
        "slicer_port": random.randint(45678, 45700) if status in NON_TERMINAL_STATES else None,
        "_has_errors": random.choice([True, False]),
        # _slicer_stats only populated for TERMINAL states (final stats after completion)
        # While running, stats are "live" on the controller only
        "_slicer_stats": generate_slicer_stats(started, job["workers"]) if status in TERMINAL_STATES and started else None,
    }


# In-memory storage for generated data
_cluster_state: dict[str, dict[str, Any]] | None = None
_controllers: list[dict[str, Any]] = []
_jobs: list[dict[str, Any]] = []
_execution_contexts: list[dict[str, Any]] = []

# Metadata for dynamic state tracking
# Maps ex_id to execution start time (when it began in real life)
_execution_metadata: dict[str, datetime] = {}

# Track actual current state and when it was last updated
# Maps ex_id to (current_state, last_state_change_time)
_execution_states: dict[str, tuple[str, datetime]] = {}

# Track when we last processed lifecycle events (starts/stops)
_last_event_check: datetime | None = None
EVENT_CHECK_INTERVAL = 180  # seconds (3 minutes)


def get_next_state(current_state: str, time_in_state: float, ex_id: str = "") -> str | None:
    """Determine the next state following valid transitions from the flowchart.

    Args:
        current_state: Current execution state
        time_in_state: Seconds since entering this state
        ex_id: Execution context ID (for deterministic random choices)

    Returns:
        Next state, or None to stay in current state
    """
    # Terminal states never change
    if current_state in TERMINAL_STATES:
        return None

    # INITIAL states progress forward
    if current_state == "pending":
        if time_in_state >= 3:
            return "scheduling"
    elif current_state == "scheduling":
        if time_in_state >= 3:
            return "initializing"
    elif current_state == "initializing":
        if time_in_state >= 4:
            return "running"

    # RUNNING state transitions
    elif current_state == "running":
        # Stay in running (long-lived state)
        # Transitions out of running are triggered by external events, not time
        return None

    elif current_state == "recovering":
        # recovering → running after 2-5 minutes
        # Use fixed threshold of 3 minutes for consistency
        if time_in_state >= 180:
            return "running"

    elif current_state == "failing":
        # failing → failed or terminated after 2 minutes
        if time_in_state >= 120:
            # Use hash of ex_id for deterministic but random-looking choice
            return "failed" if hash(ex_id) % 2 == 0 else "terminated"

    elif current_state == "paused":
        # paused stays paused (requires external action to resume)
        return None

    elif current_state == "stopping":
        # stopping → stopped after 60s
        # or stopping → completed if job finishes first (10% chance, deterministic)
        if time_in_state >= 60:
            return "completed" if hash(ex_id) % 10 == 0 else "stopped"

    return None


def calculate_current_state(ex_id: str, start_time: datetime, initial_state: str, workers: int = 10) -> tuple[str, datetime, dict[str, Any] | None]:
    """Calculate the current state following valid state transitions.

    Args:
        ex_id: Execution context ID
        start_time: When the execution started
        initial_state: The state when first created
        workers: Total workers for this execution

    Returns:
        Tuple of (current_status, last_state_change_time, slicer_stats or None)
    """
    # Terminal executions don't change state
    if initial_state in TERMINAL_STATES:
        return initial_state, start_time, None

    now = datetime.now()

    # Get tracked state or use initial
    if ex_id in _execution_states:
        current_state, last_change = _execution_states[ex_id]
    else:
        current_state, last_change = initial_state, start_time

    # Check if we should transition
    time_in_state = (now - last_change).total_seconds()
    next_state = get_next_state(current_state, time_in_state, ex_id)

    if next_state:
        # State transition occurred
        print(f"[State Transition] {ex_id[:8]}: {_execution_states.get(ex_id, (initial_state,))[0]} → {next_state}")
        current_state = next_state
        last_change = now
        # Update tracked state
        _execution_states[ex_id] = (current_state, last_change)

    # Generate slicer stats for terminal states only
    slicer_stats = None
    if current_state in TERMINAL_STATES:
        slicer_stats = generate_slicer_stats(start_time, workers)

    return current_state, last_change, slicer_stats


def apply_dynamic_state(ctx: dict[str, Any]) -> dict[str, Any]:
    """Apply dynamic state transitions to an execution context.

    Updates the execution context following valid state transitions from the flowchart.

    Args:
        ctx: Execution context dict

    Returns:
        Updated execution context with current state
    """
    ex_id = ctx["ex_id"]

    # If not tracked, return as-is (shouldn't happen)
    if ex_id not in _execution_metadata:
        return ctx

    start_time = _execution_metadata[ex_id]
    initial_status = ctx["_status"]
    workers = ctx.get("workers", 10)

    # Calculate current state following valid transitions
    current_status, last_change, slicer_stats = calculate_current_state(ex_id, start_time, initial_status, workers)

    # Update context with current state
    ctx = ctx.copy()
    ctx["_status"] = current_status
    ctx["_updated"] = datetime.now().isoformat()

    # Update slicer_stats
    if current_status in TERMINAL_STATES:
        ctx["_slicer_stats"] = slicer_stats
        ctx["slicer_hostname"] = None
        ctx["slicer_port"] = None
    else:
        ctx["_slicer_stats"] = None
        # Keep slicer_hostname and slicer_port for non-terminal

    return ctx


def process_lifecycle_events() -> None:
    """Process lifecycle events: randomly start new executions or stop existing ones.

    Called periodically (every 3 minutes) with a 50% chance of creating
    a lifecycle event (either starting a new execution or stopping an existing one).
    """
    global _execution_contexts, _execution_metadata, _last_event_check

    now = datetime.now()

    # Initialize last check time if needed
    if _last_event_check is None:
        _last_event_check = now
        return

    # Check if enough time has passed
    elapsed = (now - _last_event_check).total_seconds()
    if elapsed < EVENT_CHECK_INTERVAL:
        return

    # Update last check time
    _last_event_check = now

    # 50% chance of a lifecycle event
    if random.random() > 0.5:
        return

    # Apply dynamic states to see current situation
    updated_contexts = [apply_dynamic_state(ctx) for ctx in _execution_contexts]

    # Decide: start a new execution or stop an existing one
    # Find jobs with/without active executions
    active_by_job: dict[str, dict[str, Any]] = {}
    inactive_jobs: list[dict[str, Any]] = []

    for ctx in updated_contexts:
        if ctx["_status"] in NON_TERMINAL_STATES:
            active_by_job[ctx["job_id"]] = ctx

    for job in _jobs:
        if job["job_id"] not in active_by_job:
            inactive_jobs.append(job)

    # Decide what to do
    can_start = len(inactive_jobs) > 0
    can_stop = len(active_by_job) > 0

    if can_start and can_stop:
        # Randomly choose start or stop
        action = random.choice(["start", "stop"])
    elif can_start:
        action = "start"
    elif can_stop:
        action = "stop"
    else:
        return

    if action == "start":
        # Start a new execution for an inactive job
        job = random.choice(inactive_jobs)
        # Create new execution in pending state (age 0)
        new_ctx = generate_execution_context(job, "pending", age_seconds=0)
        _execution_contexts.append(new_ctx)
        _execution_metadata[new_ctx["ex_id"]] = now
        _execution_states[new_ctx["ex_id"]] = ("pending", now)
        print(f"[Lifecycle Event] Started new execution {new_ctx['ex_id'][:8]} for job {job['name']}")

    else:  # stop
        # Stop a random active execution
        active_contexts = list(active_by_job.values())
        ctx_to_stop = random.choice(active_contexts)

        # Find and update the context in the list
        for i, ctx in enumerate(_execution_contexts):
            if ctx["ex_id"] == ctx_to_stop["ex_id"]:
                # Update to stopped state
                _execution_contexts[i] = ctx.copy()
                _execution_contexts[i]["_status"] = "stopped"
                _execution_contexts[i]["_updated"] = now.isoformat()
                # Add final slicer stats
                if ctx["ex_id"] in _execution_metadata:
                    start_time = _execution_metadata[ctx["ex_id"]]
                    workers = ctx.get("workers", 10)
                    _execution_contexts[i]["_slicer_stats"] = generate_slicer_stats(start_time, workers)
                _execution_contexts[i]["slicer_hostname"] = None
                _execution_contexts[i]["slicer_port"] = None
                # Update state tracking
                _execution_states[ctx["ex_id"]] = ("stopped", now)
                print(f"[Lifecycle Event] Stopped execution {ctx['ex_id'][:8]} for job {ctx_to_stop['name']}")
                break


def initialize_data() -> None:
    """Initialize mock data with consistent relationships.

    Ensures each job has at most one execution context in a non-terminal state,
    representing the active execution, plus optional historical (terminal) executions.

    Simulates realistic state transitions where:
    - Very recent executions are in INITIAL states (pending → scheduling → initializing)
    - Most active executions are in "running" state for long periods
    - Some are in other RUNNING states (recovering, paused, failing, stopping)

    States dynamically update based on real elapsed time.
    """
    global _cluster_state, _controllers, _jobs, _execution_contexts, _execution_metadata, _execution_states, _last_event_check

    # Reset metadata
    _execution_metadata = {}
    _execution_states = {}
    _last_event_check = datetime.now()

    # Generate cluster state (independent of jobs)
    _cluster_state = generate_cluster_state()

    # Generate jobs first
    num_jobs = random.randint(10, 30)
    _jobs = [generate_job() for _ in range(num_jobs)]

    # Generate execution contexts based on jobs
    # Each job can have:
    # - At most one non-terminal execution context (active)
    # - Zero or more terminal execution contexts (historical runs)
    _execution_contexts = []
    now = datetime.now()

    for job in _jobs:
        # 60% chance of having an active (non-terminal) execution
        if random.random() < 0.6:
            # Determine age of execution - include more in transitional states for demo
            age_distribution = random.random()
            if age_distribution < 0.20:
                # 20% are very fresh (< 10 seconds) - in INITIAL states (will transition)
                age_seconds = random.randint(0, 10)
            elif age_distribution < 0.35:
                # 15% are recent (10s - 5min) - might be in transitional states
                age_seconds = random.randint(10, 300)
            elif age_distribution < 0.55:
                # 20% are hours old
                age_seconds = random.randint(300, 86400)  # 5min - 1day
            else:
                # 45% are days/weeks/months old (long-running)
                age_seconds = random.randint(86400, 86400 * 90)  # 1-90 days

            # Select status based on age to simulate realistic transitions
            status = select_execution_status(age_seconds)

            # If status is None, it means the execution transitioned to terminal
            # (e.g., stopping → stopped after 90s)
            if status is None:
                # Create as a stopped terminal execution instead
                status = "stopped"
                ctx = generate_execution_context(job, status, age_seconds)
                _execution_contexts.append(ctx)
                # Store start time and initial state for dynamic state tracking
                start_time = now - timedelta(seconds=age_seconds)
                _execution_metadata[ctx["ex_id"]] = start_time
                _execution_states[ctx["ex_id"]] = (status, start_time)
            else:
                # Create as non-terminal execution
                ctx = generate_execution_context(job, status, age_seconds)
                _execution_contexts.append(ctx)
                # Store start time and initial state for dynamic state tracking
                start_time = now - timedelta(seconds=age_seconds)
                _execution_metadata[ctx["ex_id"]] = start_time
                _execution_states[ctx["ex_id"]] = (status, start_time)

        # Add 0-3 historical (terminal) execution contexts
        num_historical = random.randint(0, 3)
        for _ in range(num_historical):
            status = random.choice(list(TERMINAL_STATES))
            # Historical executions are older
            age_seconds = random.randint(86400, 86400 * 180)  # 1-180 days old
            ctx = generate_execution_context(job, status, age_seconds)
            _execution_contexts.append(ctx)
            # Store start time and state (terminal executions don't change state)
            start_time = now - timedelta(seconds=age_seconds)
            _execution_metadata[ctx["ex_id"]] = start_time
            _execution_states[ctx["ex_id"]] = (status, start_time)

    # Generate controllers only for non-terminal execution contexts
    # (running, pending, etc. - controllers exist for active executions)
    _controllers = []
    active_contexts = [ctx for ctx in _execution_contexts if ctx["_status"] in NON_TERMINAL_STATES]
    for ctx in active_contexts:
        # Extract started time from slicer_stats if available
        started_str = ctx["_slicer_stats"]["started"] if ctx.get("_slicer_stats") else ctx["_created"]
        started = datetime.fromisoformat(started_str)
        _controllers.append(
            generate_controller(
                ex_id=ctx["ex_id"],
                job_id=ctx["job_id"],
                name=ctx["name"],
                started=started,
                total_workers=ctx["workers"],
            )
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    initialize_data()
    yield
    # Shutdown (if needed)


app = FastAPI(title="Mock Teraslice API", lifespan=lifespan)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Mock Teraslice API Server", "version": "1.0.0"}


@app.get("/v1/cluster/state")
async def get_cluster_state():
    """Get cluster state with all nodes and workers."""
    if _cluster_state is None:
        initialize_data()
    return JSONResponse(content=_cluster_state)


@app.get("/v1/cluster/controllers")
async def get_controllers():
    """Get all active execution controllers.

    Controllers are dynamically generated based on current execution states.
    Only non-terminal execution contexts have controllers.
    """
    if not _execution_contexts:
        initialize_data()

    # Process lifecycle events (start/stop executions)
    process_lifecycle_events()

    # Apply dynamic state transitions to get current states
    updated_contexts = [apply_dynamic_state(ctx) for ctx in _execution_contexts]

    # Generate controllers for current non-terminal executions
    current_controllers = []
    for ctx in updated_contexts:
        if ctx["_status"] in NON_TERMINAL_STATES:
            # Extract or calculate started time
            if ctx.get("_slicer_stats") and ctx["_slicer_stats"].get("started"):
                started_str = ctx["_slicer_stats"]["started"]
            else:
                started_str = ctx["_created"]

            started = datetime.fromisoformat(started_str)
            current_controllers.append(
                generate_controller(
                    ex_id=ctx["ex_id"],
                    job_id=ctx["job_id"],
                    name=ctx["name"],
                    started=started,
                    total_workers=ctx["workers"],
                )
            )

    return JSONResponse(content=current_controllers)


@app.get("/v1/jobs")
async def get_jobs(
    size: int = Query(default=100, ge=1, le=10000),
    from_: int = Query(default=0, ge=0, alias="from"),
):
    """Get all jobs with optional pagination."""
    if not _jobs:
        initialize_data()

    # Apply pagination
    end_idx = from_ + size
    paginated_jobs = _jobs[from_:end_idx]

    return JSONResponse(content=paginated_jobs)


@app.get("/v1/jobs/{job_id}")
async def get_job_by_id(job_id: str):
    """Get a specific job by ID."""
    if not _jobs:
        initialize_data()

    # Try to find existing job
    for job in _jobs:
        if job["job_id"] == job_id:
            return JSONResponse(content=job)

    # Generate a new job with the specified ID
    job = generate_job()
    job["job_id"] = job_id
    return JSONResponse(content=job)


@app.get("/v1/ex")
async def get_execution_contexts(
    size: int = Query(default=100, ge=1, le=10000),
    from_: int = Query(default=0, ge=0, alias="from"),
):
    """Get all execution contexts with optional pagination.

    States are dynamically updated based on real elapsed time.
    Every 3 minutes, there's a 50% chance of a lifecycle event
    (starting a new execution or stopping an existing one).
    """
    if not _execution_contexts:
        initialize_data()

    # Process lifecycle events (start/stop executions)
    process_lifecycle_events()

    # Apply dynamic state transitions to all contexts
    updated_contexts = [apply_dynamic_state(ctx) for ctx in _execution_contexts]

    # Apply pagination
    end_idx = from_ + size
    paginated_contexts = updated_contexts[from_:end_idx]

    return JSONResponse(content=paginated_contexts)


@app.get("/v1/ex/{ex_id}")
async def get_execution_context_by_id(ex_id: str):
    """Get a specific execution context by ID.

    State is dynamically updated based on real elapsed time.
    """
    if not _execution_contexts:
        initialize_data()

    # Try to find existing execution context
    for context in _execution_contexts:
        if context["ex_id"] == ex_id:
            # Apply dynamic state transitions
            updated_context = apply_dynamic_state(context)
            return JSONResponse(content=updated_context)

    # If not found, return 404
    return JSONResponse(
        status_code=404,
        content={"error": f"Execution context {ex_id} not found"}
    )


@app.post("/v1/cluster/state/refresh")
async def refresh_cluster_state():
    """Regenerate cluster state data."""
    global _cluster_state
    _cluster_state = generate_cluster_state()
    return {"message": "Cluster state refreshed"}


@app.post("/v1/data/refresh")
async def refresh_all_data():
    """Regenerate all mock data."""
    initialize_data()
    return {
        "message": "All data refreshed",
        "counts": {
            "nodes": len(_cluster_state) if _cluster_state else 0,
            "controllers": len(_controllers),
            "jobs": len(_jobs),
            "execution_contexts": len(_execution_contexts),
        },
    }
