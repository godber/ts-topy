# ts-topy

A Python-based monitoring tool for Teraslice distributed computing clusters, built with Textual.

## Overview

This is a rewrite of [teraslice-top](https://github.com/godber/teraslice-top) in Python, designed to provide better scalability and UX for monitoring Teraslice clusters with many jobs.

## Features

- **Real-time monitoring** of Teraslice cluster state
- **Five-pane display** showing:
  - Nodes
  - Workers
  - Controllers
  - Jobs
  - Execution Contexts
- **Global search/filter** across all data
- **Auto-refresh** with configurable intervals
- **Terminal UI** built with Textual

## Technology Stack

- **Python 3.10+**
- **uv** - Python project and package manager
- **Textual** - Terminal UI framework
- **httpx** - Async HTTP client
- **Pydantic** - Data validation and models
- **Typer** - CLI interface

## Implementation Plan

### Phase 1: Project Setup & Data Layer

1. Initial setup - Create basic project structure with uv, pyproject.toml
2. API Client - Build httpx client to connect to Teraslice master
3. Data Models - Define Pydantic models for the 5 entity types
4. Test API client - Verify we can fetch and parse all 5 endpoints

### Phase 2: Basic Textual UI

5. Hello World - Create minimal Textual app that runs
6. Single pane - Display data from one endpoint in a DataTable widget
7. Layout - Add all 5 panes with responsive layout
8. Auto-refresh - Add timer to poll APIs and update display

### Phase 3: Polish

9. Search/Filter - Add input widget and filtering logic
10. Styling - Improve colors, headers, formatting
11. CLI args - Add host/port/timeout options
12. Error handling - Handle connection errors, empty responses gracefully

## Installation

```bash
# Install from PyPI
pip install ts-topy

# Or using pipx (recommended for CLI tools)
pipx install ts-topy

# Or using uv
uv tool install ts-topy
```

## Usage

```bash
# Connect to localhost:5678 (default)
ts-topy

# Specify custom URL
ts-topy https://teraslice.example.com:8000

# Set refresh interval (default: 5s)
ts-topy http://localhost:5678 --interval 5
ts-topy http://localhost:5678 -i 5

# Set request timeout (default: 10s)
ts-topy http://localhost:5678 --request-timeout 30

# All options
ts-topy https://teraslice.example.com:8000 -i 5 --request-timeout 30
```

## Development

```bash
# Initialize project
uv init

# Install dependencies
uv sync

# Run the application
uv run ts-topy
```

## Development Status

✅ **Released** - Available on [PyPI](https://pypi.org/project/ts-topy/)

## License

MIT
