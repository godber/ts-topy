"""Main entry point for py-ts-top CLI."""

from typing import Annotated

import typer

from py_ts_top.app import TerasliceApp

app = typer.Typer()


@app.command()
def main(
    url: Annotated[str, typer.Argument(help="Teraslice master URL (e.g., http://localhost:5678)")] = "http://localhost:5678",
    interval: Annotated[int, typer.Option("--interval", "-i", help="Refresh interval in seconds")] = 2,
    request_timeout: Annotated[int, typer.Option("--request-timeout", help="HTTP request timeout in seconds")] = 10,
) -> None:
    """Monitor a Teraslice cluster in real-time."""
    tui_app = TerasliceApp(
        url=url,
        interval=interval,
        request_timeout=request_timeout,
    )
    tui_app.run()


if __name__ == "__main__":
    app()
