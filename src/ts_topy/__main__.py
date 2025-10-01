"""Main entry point for ts-topy CLI."""

from typing import Annotated, Optional

import typer

from ts_topy.aliases import ClusterAliases
from ts_topy.app import TerasliceApp
from ts_topy.cluster_selector import ClusterSelectorApp

app = typer.Typer()


@app.command()
def main(
    url: Annotated[Optional[str], typer.Argument(help="Teraslice master URL (e.g., http://localhost:5678)")] = None,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Refresh interval in seconds")] = 5,
    request_timeout: Annotated[int, typer.Option("--request-timeout", help="HTTP request timeout in seconds")] = 10,
) -> None:
    """Monitor a Teraslice cluster in real-time."""
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


if __name__ == "__main__":
    app()
