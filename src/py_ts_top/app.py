"""Textual application for monitoring Teraslice clusters."""

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static, DataTable

from py_ts_top.client import TerasliceClient


class TerasliceApp(App):
    """A Textual app to monitor Teraslice clusters."""

    CSS = """
    Screen {
        overflow: hidden;
    }

    #cluster-info {
        height: auto;
        padding: 1 2;
        background: $panel;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr;
        height: 100%;
    }

    .table-container {
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    .table-header {
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    #execution-contexts-container {
        column-span: 2;
    }

    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        url: str = "http://localhost:5678",
        interval: int = 5,
        request_timeout: int = 10,
    ):
        """Initialize the Teraslice monitoring app.

        Args:
            url: Teraslice master URL
            interval: Refresh interval in seconds
            request_timeout: HTTP request timeout in seconds
        """
        super().__init__()
        self.url = url
        self.interval = interval
        self.request_timeout = request_timeout
        self.client = TerasliceClient(url, timeout=request_timeout)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Loading cluster data...", id="cluster-info")
        yield Container(
            # Row 1: Execution Contexts (full width)
            Container(
                Static("Execution Contexts", classes="table-header"),
                DataTable(id="execution-contexts-table"),
                classes="table-container",
                id="execution-contexts-container",
            ),
            # Row 2: Controllers and Jobs
            Container(
                Static("Controllers", classes="table-header"),
                DataTable(id="controllers-table"),
                classes="table-container",
            ),
            Container(
                Static("Jobs", classes="table-header"),
                DataTable(id="jobs-table"),
                classes="table-container",
            ),
            id="main-grid",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = "Teraslice Top"
        self.sub_title = self.url

        # Set up controllers table
        controllers_table = self.query_one("#controllers-table", DataTable)
        controllers_table.add_columns("Name", "Ex ID", "Started", "Workers", "Processed", "Failed", "Queued")
        controllers_table.cursor_type = "row"

        # Set up jobs table
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.add_columns("Name", "Job ID", "Lifecycle", "Workers", "Active", "Ops", "Created", "Updated")
        jobs_table.cursor_type = "row"

        # Set up execution contexts table
        ex_table = self.query_one("#execution-contexts-table", DataTable)
        ex_table.add_columns("Name", "Ex ID", "Job ID", "Status", "Workers", "Slicers", "Processed", "Failed", "Created", "Updated")
        ex_table.cursor_type = "row"

        # Initial fetch
        self.run_worker(self.fetch_data, thread=True, exclusive=True)

        # Set up auto-refresh timer
        self.set_interval(self.interval, self.refresh_data)

    def fetch_data(self) -> None:
        """Fetch data from Teraslice cluster (runs in thread)."""
        try:
            # Fetch all data
            cluster_state = self.client.fetch_cluster_state()
            controllers = self.client.fetch_controllers()
            jobs = self.client.fetch_jobs(size=1000)
            execution_contexts = self.client.fetch_execution_contexts(size=1000)

            # Sort data by timestamps (most recent first)
            jobs_sorted = sorted(jobs, key=lambda j: j.updated, reverse=True)
            execution_contexts_sorted = sorted(execution_contexts, key=lambda e: e.updated, reverse=True)
            controllers_sorted = sorted(
                controllers,
                key=lambda c: c.started if c.started else "",
                reverse=True
            )

            # Format cluster info
            cluster_info = (
                f"[b]Nodes:[/b] {cluster_state.total_nodes}  "
                f"[b]Workers:[/b] {cluster_state.active_workers}/{cluster_state.total_workers}  "
                f"[b]Available:[/b] {cluster_state.available_workers}  "
                f"[b]Controllers:[/b] {len(controllers)}  "
                f"[b]Jobs:[/b] {len(jobs)}  "
                f"[b]Execution Contexts:[/b] {len(execution_contexts)}"
            )

            # Prepare controller rows
            controller_rows = []
            for ctrl in controllers_sorted:
                ex_id_short = ctrl.ex_id[:8] if len(ctrl.ex_id) > 8 else ctrl.ex_id
                started = ctrl.started.strftime("%Y-%m-%d %H:%M:%S") if ctrl.started else "N/A"
                controller_rows.append([
                    ctrl.name[:30],
                    ex_id_short,
                    started,
                    f"{ctrl.workers_active}/{ctrl.workers_available}",
                    str(ctrl.processed),
                    str(ctrl.failed),
                    str(ctrl.queued),
                ])

            # Prepare job rows
            job_rows = []
            for job in jobs_sorted:
                active_status = "Yes" if job.active else "No" if job.active is not None else "N/A"
                job_id_short = job.job_id[:8] if len(job.job_id) > 8 else job.job_id
                created = job.created.strftime("%Y-%m-%d %H:%M:%S")
                updated = job.updated.strftime("%Y-%m-%d %H:%M:%S")
                job_rows.append([
                    job.name[:30],
                    job_id_short,
                    job.lifecycle,
                    str(job.workers),
                    active_status,
                    str(len(job.operations)),
                    created,
                    updated,
                ])

            # Prepare execution context rows
            ex_rows = []
            for ex in execution_contexts_sorted:
                ex_id_short = ex.ex_id[:8] if len(ex.ex_id) > 8 else ex.ex_id
                job_id_short = ex.job_id[:8] if len(ex.job_id) > 8 else ex.job_id
                processed = str(ex.slicer_stats.processed) if ex.slicer_stats else "0"
                failed = str(ex.slicer_stats.failed) if ex.slicer_stats else "0"
                created = ex.created.strftime("%Y-%m-%d %H:%M:%S")
                updated = ex.updated.strftime("%Y-%m-%d %H:%M:%S")
                ex_rows.append([
                    ex.name[:30],
                    ex_id_short,
                    job_id_short,
                    ex.status,
                    str(ex.workers),
                    str(ex.slicers),
                    processed,
                    failed,
                    created,
                    updated,
                ])

            self.call_from_thread(
                self.update_display,
                cluster_info,
                controller_rows,
                job_rows,
                ex_rows,
            )

        except Exception as e:
            error_msg = f"[b red]Error:[/b red] {str(e)}"
            self.call_from_thread(self.update_display, error_msg, [], [], [])

    def update_display(
        self,
        cluster_info: str,
        controller_rows: list,
        job_rows: list,
        ex_rows: list,
    ) -> None:
        """Update the display widgets (called from main thread)."""
        # Update cluster info
        info_widget = self.query_one("#cluster-info", Static)
        info_widget.update(cluster_info)

        # Update controllers table
        controllers_table = self.query_one("#controllers-table", DataTable)
        controllers_table.clear()
        for row in controller_rows:
            controllers_table.add_row(*row)

        # Update jobs table
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.clear()
        for row in job_rows:
            jobs_table.add_row(*row)

        # Update execution contexts table
        ex_table = self.query_one("#execution-contexts-table", DataTable)
        ex_table.clear()
        for row in ex_rows:
            ex_table.add_row(*row)

    def refresh_data(self) -> None:
        """Refresh data (called by timer or manually)."""
        self.run_worker(self.fetch_data, thread=True, exclusive=True)

    def action_refresh(self) -> None:
        """Manual refresh action (triggered by 'r' key)."""
        self.refresh_data()

    def action_quit(self) -> None:
        """Quit the application."""
        self.client.close()
        self.exit()
