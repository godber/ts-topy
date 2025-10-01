# ts-topy

A monitoring tool for Teraslice distributed computing clusters, built on Python
with Textual.

## Overview

This is a rewrite of [teraslice-top](https://github.com/godber/teraslice-top)
in Python, designed to provide better scalability and UX for monitoring
Teraslice clusters with many jobs.

## Installation

```bash
# Install using uv (recommended for CLI tools)
uv tool install ts-topy

# Or from PyPI
pip install ts-topy

# Or using pipx
pipx install ts-topy
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

## Releasing

This project uses GitHub Actions for automated releases to PyPI. To create a new release:

1. **Bump the version** using the bump script:

  ```bash
  # For a patch release (bug fixes)
  python scripts/bump_version.py patch

  # For a minor release (new features)
  python scripts/bump_version.py minor

  # For a major release (breaking changes)
  python scripts/bump_version.py major

  # Or set a specific version
  python scripts/bump_version.py --set 1.2.3
  ```

2. **Review and commit the changes**:

   ```bash
   git diff  # Review the version change
   git add pyproject.toml
   git commit -m "Bump version to X.Y.Z"
   ```

3. **Create and push a git tag**:

   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

4. **GitHub Actions will automatically**:
   - Build the package
   - Create a GitHub release
   - Publish to PyPI

5. **Verify the release**:
   - Check the [GitHub releases page](https://github.com/godber/ts-topy/releases)
   - Verify on [PyPI](https://pypi.org/project/ts-topy/)

### Manual Release (if needed)

If you need to build and publish manually:

```bash
# Build the package
uv build

# Publish to PyPI (requires PyPI credentials)
uv publish
```

## License

MIT
