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

The mock server generates realistic-looking data with:

- Random UUIDs for IDs
- Realistic timestamps (created/updated dates within the last 30 days)
- Various job and execution context states (running, completed, stopped, failed, pending)
- Random worker counts and statistics
- Multiple operation types (elasticsearch_reader, noop, elasticsearch_bulk)
- Lifecycle types (once, persistent)

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
