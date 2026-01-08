# Mock Teraslice API Server

The mock server provides a development and testing environment for ts-topy without requiring a real Teraslice cluster.

## Installation

Install the mock server dependencies:

```bash
uv sync --extra mock
```

## Running the Mock Server

Start the mock server on the default port (5678):

```bash
uv run ts-topy mock-server
```

### Options

- `--host, -h`: Host to bind the server to (default: 127.0.0.1)
- `--port, -p`: Port to run the server on (default: 5678)
- `--reload`: Enable auto-reload on code changes (useful for development)

### Examples

Run on a different port:

```bash
uv run ts-topy mock-server --port 8080
```

Run with auto-reload for development:

```bash
uv run ts-topy mock-server --reload
```

Make the server accessible from other machines:

```bash
uv run ts-topy mock-server --host 0.0.0.0
```

## Using the Mock Server

Once the server is running, you can:

1. **Monitor it with ts-topy** (in a separate terminal):

```bash
uv run ts-topy http://localhost:5678
```

2. **Query endpoints directly** with curl or httpx:

```bash
# Get cluster state
curl http://localhost:5678/v1/cluster/state

# Get controllers
curl http://localhost:5678/v1/cluster/controllers

# Get jobs (with pagination)
curl "http://localhost:5678/v1/jobs?size=10&from=0"

# Get execution contexts
curl http://localhost:5678/v1/ex

# Get a specific job
curl http://localhost:5678/v1/jobs/<job_id>

# Regenerate all mock data
curl -X POST http://localhost:5678/v1/data/refresh
```

## Available Endpoints

### GET /v1/cluster/state

Returns the cluster state with nodes and workers.

### GET /v1/cluster/controllers

Returns a list of active execution controllers.

### GET /v1/jobs

Returns a list of jobs with optional pagination.

Query parameters:
- `size`: Number of jobs to return (default: 100, max: 10000)
- `from`: Starting offset for pagination (default: 0)

### GET /v1/jobs/{job_id}

Returns a specific job by ID.

### GET /v1/ex

Returns a list of execution contexts with optional pagination.

Query parameters:

- `size`: Number of execution contexts to return (default: 100, max: 10000)
- `from`: Starting offset for pagination (default: 0)

### GET /v1/ex/{ex_id}

Returns a specific execution context by ID.

### POST /v1/data/refresh

Regenerates all mock data. Useful for getting a fresh set of random data.

## Mock Data Characteristics

The mock server generates realistic, time-aware data that simulates a live Teraslice cluster:

### Data Consistency

- **Jobs, Execution Contexts, and Controllers are synchronized**:
  - Execution contexts inherit `job_id`, `name`, `lifecycle`, `workers`, and `operations` from their parent job
  - Controllers inherit `ex_id`, `job_id`, `name`, and worker counts from their execution context
  - All three share the same `job_id` for easy tracking

### State Management

- **Dynamic state transitions** following the Teraslice state flowchart:
  - **INITIAL states** (pending → scheduling → initializing → running): Progress in 3-4 second intervals
  - **RUNNING states**: Most executions stay in "running" for long periods (hours/days)
  - **Transient states**:
    - `recovering` → `running` (after 3 minutes)
    - `failing` → `failed`/`terminated` (after 2 minutes)
    - `stopping` → `stopped` (after 60 seconds)
  - **TERMINAL states** (completed, stopped, failed, terminated, rejected): Never change
  - **Invalid transitions are prevented** (e.g., `stopping` cannot go to `running`)

### Worker Statistics

- **Workers running almost always equals total requested** (95% of the time):
  - `workers_joined` = total workers (95%) or slightly less (5%)
  - `workers_active` = workers_joined (95%) or slightly less (5%)
  - `workers_available` = slots not yet filled
  - Disconnected/reconnected workers are rare (<25% of joined workers)

### Slice Statistics

- **Processed slices increase steadily over time**:
  - ~1 slice per 10 seconds per active worker
  - Grows linearly with execution duration

- **Failed slices are mostly zero**:
  - 90% of executions: `failed = 0`
  - 10% of executions: `failed = 0.05-0.5%` of processed slices

- **Queued slices equal active worker count**:
  - `queued = workers_active` (one slice per worker)

- **Subslices** are 1.0-1.5x the number of processed slices

### Lifecycle Events

- **Automatic job start/stop events** every 3 minutes:
  - 50% chance of either starting a new execution or stopping an existing one
  - New executions start in `pending` state and progress naturally
  - Stopped executions transition to `stopped` state with final statistics

### Data Distribution

- **Execution age distribution**:
  - 20% are fresh (< 10 seconds) - in INITIAL states
  - 15% are recent (10s - 5 minutes)
  - 20% are hours old
  - 45% are days/weeks/months old (long-running)

- **State distribution**: Random UUIDs, realistic timestamps, multiple operation types (elasticsearch_reader, noop, elasticsearch_bulk), and lifecycle types (once, persistent)

### Real-Time Updates

- States update automatically based on elapsed real time (no refresh needed)
- Slice statistics recalculate on each query to show current progress
- Controllers are dynamically generated for current non-terminal executions only

Data is regenerated on server startup and can be refreshed via the `/v1/data/refresh` endpoint.

## Development

The mock server code is located in `src/ts_topy/mock_server.py` and uses FastAPI for the web framework.

To modify the mock data generation:

1. Edit the generator functions in `mock_server.py`
2. Restart the server (or use `--reload` for automatic restart)
3. Test with curl or the ts-topy TUI

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:5678/docs
- **ReDoc**: http://localhost:5678/redoc
