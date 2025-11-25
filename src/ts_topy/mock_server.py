"""Mock Teraslice API server for testing and development."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse


app = FastAPI(title="Mock Teraslice API")


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


def generate_controller() -> dict[str, Any]:
    """Generate a mock execution controller."""
    ex_id = uuid.uuid4().hex
    job_id = uuid.uuid4().hex
    started = datetime.now() - timedelta(hours=random.randint(0, 48))

    workers_joined = random.randint(1, 20)
    workers_active = random.randint(0, workers_joined)

    return {
        "ex_id": ex_id,
        "job_id": job_id,
        "name": f"job_{random.choice(['etl', 'ingest', 'export', 'transform'])}",
        "workers_available": random.randint(0, 5),
        "workers_active": workers_active,
        "workers_joined": workers_joined,
        "workers_reconnected": random.randint(0, 5),
        "workers_disconnected": random.randint(0, 3),
        "failed": random.randint(0, 100),
        "subslices": random.randint(0, 1000),
        "queued": random.randint(0, 500),
        "slice_range_expansion": random.randint(0, 10),
        "processed": random.randint(1000, 1000000),
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


def generate_slicer_stats() -> dict[str, Any]:
    """Generate mock slicer stats."""
    started = datetime.now() - timedelta(hours=random.randint(0, 48))
    queuing_complete = None
    if random.random() > 0.5:
        queuing_complete = started + timedelta(minutes=random.randint(1, 60))

    workers_joined = random.randint(1, 20)
    workers_active = random.randint(0, workers_joined)

    return {
        "workers_active": workers_active,
        "workers_joined": workers_joined,
        "queued": random.randint(0, 500),
        "job_duration": random.randint(100, 100000),
        "subslice_by_key": random.randint(0, 100),
        "failed": random.randint(0, 100),
        "subslices": random.randint(0, 1000),
        "slice_range_expansion": random.randint(0, 10),
        "processed": random.randint(1000, 1000000),
        "workers_available": random.randint(0, 5),
        "workers_reconnected": random.randint(0, 5),
        "workers_disconnected": random.randint(0, 3),
        "slicers": random.randint(1, 3),
        "started": started.isoformat(),
        "queuing_complete": queuing_complete.isoformat() if queuing_complete else None,
    }


def generate_execution_context() -> dict[str, Any]:
    """Generate a mock execution context."""
    ex_id = uuid.uuid4().hex
    job_id = uuid.uuid4().hex
    created = datetime.now() - timedelta(days=random.randint(0, 30))
    updated = created + timedelta(hours=random.randint(0, 24))

    status = random.choice(["running", "completed", "stopped", "failed", "pending"])

    return {
        "ex_id": ex_id,
        "job_id": job_id,
        "name": f"ex_{random.choice(['etl_pipeline', 'data_sync', 'log_processor', 'export_job'])}",
        "lifecycle": random.choice(["once", "persistent"]),
        "analytics": random.choice([True, False]),
        "max_retries": random.randint(0, 5),
        "probation_window": random.randint(0, 300000),
        "slicers": random.randint(1, 3),
        "workers": random.randint(1, 20),
        "operations": [generate_operation() for _ in range(random.randint(2, 4))],
        "_created": created.isoformat(),
        "_updated": updated.isoformat(),
        "_context": "ex",
        "_status": status,
        "slicer_hostname": f"worker-{random.randint(1, 100)}.example.com",
        "slicer_port": random.randint(45678, 45700),
        "_has_errors": random.choice([True, False]),
        "_slicer_stats": generate_slicer_stats() if status == "running" else None,
    }


# In-memory storage for generated data
_cluster_state: dict[str, dict[str, Any]] | None = None
_controllers: list[dict[str, Any]] = []
_jobs: list[dict[str, Any]] = []
_execution_contexts: list[dict[str, Any]] = []


def initialize_data() -> None:
    """Initialize mock data."""
    global _cluster_state, _controllers, _jobs, _execution_contexts

    _cluster_state = generate_cluster_state()
    _controllers = [generate_controller() for _ in range(random.randint(2, 10))]
    _jobs = [generate_job() for _ in range(random.randint(5, 30))]
    _execution_contexts = [generate_execution_context() for _ in range(random.randint(5, 25))]


@app.on_event("startup")
async def startup_event():
    """Initialize data on startup."""
    initialize_data()


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
    """Get all active execution controllers."""
    if not _controllers:
        initialize_data()
    return JSONResponse(content=_controllers)


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
    """Get all execution contexts with optional pagination."""
    if not _execution_contexts:
        initialize_data()

    # Apply pagination
    end_idx = from_ + size
    paginated_contexts = _execution_contexts[from_:end_idx]

    return JSONResponse(content=paginated_contexts)


@app.get("/v1/ex/{ex_id}")
async def get_execution_context_by_id(ex_id: str):
    """Get a specific execution context by ID."""
    if not _execution_contexts:
        initialize_data()

    # Try to find existing execution context
    for context in _execution_contexts:
        if context["ex_id"] == ex_id:
            return JSONResponse(content=context)

    # Generate a new execution context with the specified ID
    context = generate_execution_context()
    context["ex_id"] = ex_id
    return JSONResponse(content=context)


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
