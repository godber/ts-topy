# ts-topy

A monitoring tool for Teraslice distributed computing clusters, built on Python
with Textual.

## Overview

This is a rewrite of [teraslice-top](https://github.com/godber/teraslice-top)
in Python, designed to provide better scalability and UX for monitoring
Teraslice clusters with many jobs.

## Installation

```bash
# Coming soon
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

## Development

```bash
# Install dependencies
uv sync

# Run the application
uv run ts-topy
```

## License

MIT
