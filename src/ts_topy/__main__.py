"""Main entry point for ts-topy CLI."""

from typing import Annotated, Optional

import typer

from ts_topy import __version__
from ts_topy.aliases import ClusterAliases
from ts_topy.app import TerasliceApp
from ts_topy.cluster_selector import ClusterSelectorApp

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    url: Annotated[Optional[str], typer.Option("--url", "-u", help="Teraslice master URL (e.g., http://localhost:5678)")] = None,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Refresh interval in seconds")] = 5,
    request_timeout: Annotated[int, typer.Option("--request-timeout", help="HTTP request timeout in seconds")] = 10,
    version: Annotated[Optional[bool], typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit")] = None,
) -> None:
    """Monitor a Teraslice cluster in real-time.

    Run without options to show the cluster selector, or specify a URL with --url.
    """
    # If a subcommand was invoked, don't run the main logic
    if ctx.invoked_subcommand is not None:
        return

    # Determine the URL to use
    target_url = url

    # If no URL provided, show selector
    if target_url is None:
        aliases = ClusterAliases()

        # Always show selector - this allows users to add clusters via the UI
        selector_app = ClusterSelectorApp(aliases)
        selector_app.run()
        target_url = selector_app.selected_url

        # If user quit without selecting, exit
        if target_url is None:
            typer.echo("No cluster selected. Exiting.")
            raise typer.Exit()

    tui_app = TerasliceApp(
        url=target_url,
        interval=interval,
        request_timeout=request_timeout,
    )
    tui_app.run()


@app.command()
def mock_server(
    host: Annotated[str, typer.Option("--host", "-h", help="Host to bind the server to")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to run the server on")] = 5678,
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload on code changes")] = False,
) -> None:
    """Run a mock Teraslice API server for testing and development.

    This starts a FastAPI server that mimics the Teraslice API with randomly
    generated mock data. Requires the 'mock' optional dependencies:

    uv sync --extra mock
    """
    try:
        import uvicorn
    except ImportError:
        typer.echo("Error: FastAPI and uvicorn are required to run the mock server.")
        typer.echo("Install with: uv sync --extra mock")
        raise typer.Exit(code=1)

    typer.echo(f"Starting mock Teraslice API server on http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop the server")
    typer.echo("")
    typer.echo("Available endpoints:")
    typer.echo("  GET  /v1/cluster/state")
    typer.echo("  GET  /v1/cluster/controllers")
    typer.echo("  GET  /v1/jobs")
    typer.echo("  GET  /v1/jobs/{job_id}")
    typer.echo("  GET  /v1/ex")
    typer.echo("  GET  /v1/ex/{ex_id}")
    typer.echo("  POST /v1/data/refresh  (regenerate all mock data)")
    typer.echo("")

    uvicorn.run(
        "ts_topy.mock_server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
