# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ts-topy is a Python-based monitoring tool for Teraslice distributed computing clusters. It provides a real-time terminal UI (TUI) built with Textual to monitor cluster state, jobs, execution contexts, controllers, and workers.

## Commands

### Development

```bash
# Install dependencies
uv sync

# Run the application
uv run ts-topy

# Run with custom options
uv run ts-topy http://localhost:5678 --interval 5 --request-timeout 30
```

## Architecture

### Data Flow

1. **TerasliceClient** (`src/ts_topy/client.py`) - HTTP client that fetches data from Teraslice API endpoints:
   - `/v1/cluster/state` - Cluster nodes and workers
   - `/v1/cluster/controllers` - Active execution controllers
   - `/v1/jobs` - All jobs
   - `/v1/ex` - Execution contexts

2. **Pydantic Models** (`src/ts_topy/models.py`) - Data validation and parsing:
   - `ClusterState` - Contains nodes and workers with computed properties
   - `Controller` - Execution controller (slicer) information
   - `Job` - Job configuration and status
   - `ExecutionContext` - Execution context state with slicer stats
   - Custom validators handle "N/A" values from API

3. **Textual App** (`src/ts_topy/app.py`) - TUI application:
   - Grid layout with 3 data tables (execution contexts, controllers, jobs)
   - Threaded data fetching to prevent UI blocking
   - Auto-refresh timer based on interval parameter
   - Cluster summary statistics displayed at top

4. **CLI Entry Point** (`src/ts_topy/__main__.py`) - Typer-based CLI with arguments:
   - `url` - Teraslice master URL (default: http://localhost:5678)
   - `--interval/-i` - Refresh interval in seconds (default: 5)
   - `--request-timeout` - HTTP timeout in seconds (default: 10)

### Key Design Patterns

- **Threaded Data Fetching**: `fetch_data()` runs in worker thread and uses `call_from_thread()` to update UI on main thread
- **Pagination**: Jobs and execution contexts support `size` and `from_` parameters (default fetches 1000)
- **Timestamp Sorting**: Data tables display most recently updated items first
- **ID Truncation**: UUIDs are truncated to 8 characters for display

### Dependencies

- **httpx** - Async-capable HTTP client (used synchronously)
- **pydantic** - Data validation with custom validators for API quirks
- **textual** - Terminal UI framework with DataTable widgets
- **typer** - CLI argument parsing
