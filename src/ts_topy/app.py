"""Textual application for monitoring Teraslice clusters."""

import json

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, DataTable, Button, Input, Select, OptionList
from textual.widgets.option_list import Option

from ts_topy.client import TerasliceClient


class JsonModal(ModalScreen):
    """Modal screen to display JSON data."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    JsonModal {
        align: center middle;
    }

    JsonModal > Vertical {
        width: 90%;
        height: 90%;
        background: $panel;
        border: thick $primary;
    }

    JsonModal .modal-title {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: $primary;
    }

    JsonModal VerticalScroll {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }

    JsonModal Button {
        width: 20;
        margin: 1 2;
    }
    """

    def __init__(self, json_data: dict, title: str = "JSON Details", url: str | None = None) -> None:
        """Initialize the JSON modal.

        Args:
            json_data: Dictionary to display as JSON
            title: Title for the modal
            url: Optional URL to display
        """
        super().__init__()
        self.json_data = json_data
        self.modal_title = title
        self.url = url

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        from rich.text import Text

        formatted_json = json.dumps(self.json_data, indent=2, default=str)

        if self.url:
            # Create title with clickable link
            title = Text()
            title.append(self.modal_title, style="bold")
            title.append("\n")
            title.append(self.url, style=f"link {self.url}")
        else:
            title = Text(self.modal_title, style="bold")

        yield Vertical(
            Static(title, classes="modal-title"),
            VerticalScroll(Static(formatted_json)),
            Button("Close", variant="primary", id="close-button"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss()


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

    #filter-container {
        height: auto;
        padding: 0 2;
    }

    #filter-input {
        width: 100%;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr;
        height: 1fr;
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

    #execution-contexts-content {
        height: 1fr;
        layout: horizontal;
    }

    #execution-contexts-table {
        width: 3fr;
        height: 100%;
    }

    #status-filter-section {
        width: 1fr;
        height: 100%;
        border-left: solid $primary;
        padding: 0 1;
    }

    #status-filter-header {
        text-style: bold;
        background: $boost;
        padding: 0 1;
    }

    #status-option-list {
        height: 1fr;
    }

    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "blur_filter", "Blur Filter"),
        ("ctrl+x", "clear_filter", "Clear Filter"),
        ("ctrl+s", "clear_status_filter", "Clear Status Filter"),
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
        self.job_id_map: dict[int, str] = {}  # Maps row index to full job_id
        self.controller_id_map: dict[int, str] = {}  # Maps row index to ex_id
        self.ex_id_map: dict[int, str] = {}  # Maps row index to ex_id
        self.filter_text: str = ""  # Global filter text
        self.status_filter: set[str] = {"running"}  # Status filter for execution contexts (multi-select)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Loading cluster data...", id="cluster-info")
        yield Container(
            Input(placeholder="Filter by Name, Ex ID, or Job ID...", id="filter-input"),
            id="filter-container",
        )
        yield Container(
            # Row 1: Execution Contexts (full width, with status filter embedded)
            Container(
                Static("Execution Contexts", classes="table-header"),
                Container(
                    DataTable(id="execution-contexts-table"),
                    Container(
                        Static("Status Filter", id="status-filter-header"),
                        OptionList(id="status-option-list"),
                        id="status-filter-section",
                    ),
                    id="execution-contexts-content",
                ),
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

        # Update status filter display to show "running" as selected
        self.update_status_filter_display()

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

            # Prepare controller rows and ID mapping
            controller_rows = []
            controller_id_map = {}
            for idx, ctrl in enumerate(controllers_sorted):
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
                controller_id_map[idx] = ctrl.ex_id

            # Prepare job rows and ID mapping
            job_rows = []
            job_id_map = {}
            for idx, job in enumerate(jobs_sorted):
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
                job_id_map[idx] = job.job_id

            # Prepare execution context rows and ID mapping
            ex_rows = []
            ex_id_map = {}
            for idx, ex in enumerate(execution_contexts_sorted):
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
                ex_id_map[idx] = ex.ex_id

            self.call_from_thread(
                self.update_display,
                cluster_info,
                controller_rows,
                job_rows,
                ex_rows,
                controller_id_map,
                job_id_map,
                ex_id_map,
            )

        except Exception as e:
            error_msg = f"[b red]Error:[/b red] {str(e)}"
            self.call_from_thread(self.update_display, error_msg, [], [], [], {}, {}, {})

    def update_display(
        self,
        cluster_info: str,
        controller_rows: list,
        job_rows: list,
        ex_rows: list,
        controller_id_map: dict[int, str],
        job_id_map: dict[int, str],
        ex_id_map: dict[int, str],
    ) -> None:
        """Update the display widgets (called from main thread)."""
        # Update cluster info
        info_widget = self.query_one("#cluster-info", Static)
        info_widget.update(cluster_info)

        # Apply global filter
        filter_lower = self.filter_text

        # Filter controllers (by name or ex_id)
        filtered_controllers = []
        filtered_controller_id_map = {}
        for idx, row in enumerate(controller_rows):
            ctrl_id = controller_id_map[idx]
            name = row[0].lower()  # Name column
            ex_id = ctrl_id.lower()
            if not filter_lower or filter_lower in name or filter_lower in ex_id:
                filtered_idx = len(filtered_controllers)
                filtered_controllers.append(row)
                filtered_controller_id_map[filtered_idx] = ctrl_id

        # Filter jobs (by name or job_id)
        filtered_jobs = []
        filtered_job_id_map = {}
        for idx, row in enumerate(job_rows):
            job_id = job_id_map[idx]
            name = row[0].lower()  # Name column
            job_id_lower = job_id.lower()
            if not filter_lower or filter_lower in name or filter_lower in job_id_lower:
                filtered_idx = len(filtered_jobs)
                filtered_jobs.append(row)
                filtered_job_id_map[filtered_idx] = job_id

        # Filter execution contexts (by name, ex_id, job_id, and status)
        filtered_ex = []
        filtered_ex_id_map = {}
        for idx, row in enumerate(ex_rows):
            ex_id = ex_id_map[idx]
            name = row[0].lower()  # Name column
            ex_id_lower = ex_id.lower()
            job_id_lower = row[2].lower()  # Job ID column (shortened)
            status = row[3].lower()  # Status column

            # Apply text filter (name, ex_id, or job_id)
            text_matches = not filter_lower or filter_lower in name or filter_lower in ex_id_lower or filter_lower in job_id_lower

            # Apply status filter (multi-select: must be in the selected set, or no filter if set is empty)
            status_matches = not self.status_filter or status in self.status_filter

            if text_matches and status_matches:
                filtered_idx = len(filtered_ex)
                filtered_ex.append(row)
                filtered_ex_id_map[filtered_idx] = ex_id

        # Update controllers table - preserve selection by ID
        controllers_table = self.query_one("#controllers-table", DataTable)
        selected_ctrl_id = self.controller_id_map.get(controllers_table.cursor_row)
        controllers_table.clear()
        for row in filtered_controllers:
            controllers_table.add_row(*row)
        self.controller_id_map = filtered_controller_id_map
        # Find the same controller in the new data
        if selected_ctrl_id:
            for idx, ctrl_id in filtered_controller_id_map.items():
                if ctrl_id == selected_ctrl_id:
                    controllers_table.move_cursor(row=idx)
                    break

        # Update jobs table - preserve selection by ID
        jobs_table = self.query_one("#jobs-table", DataTable)
        selected_job_id = self.job_id_map.get(jobs_table.cursor_row)
        jobs_table.clear()
        for row in filtered_jobs:
            jobs_table.add_row(*row)
        self.job_id_map = filtered_job_id_map
        # Find the same job in the new data
        if selected_job_id:
            for idx, job_id in filtered_job_id_map.items():
                if job_id == selected_job_id:
                    jobs_table.move_cursor(row=idx)
                    break

        # Update execution contexts table - preserve selection by ID
        ex_table = self.query_one("#execution-contexts-table", DataTable)
        selected_ex_id = self.ex_id_map.get(ex_table.cursor_row)
        ex_table.clear()
        for row in filtered_ex:
            ex_table.add_row(*row)
        self.ex_id_map = filtered_ex_id_map
        # Find the same execution context in the new data
        if selected_ex_id:
            for idx, ex_id in filtered_ex_id_map.items():
                if ex_id == selected_ex_id:
                    ex_table.move_cursor(row=idx)
                    break

    def update_status_filter_display(self) -> None:
        """Update the status filter OptionList to show selected items with checkmarks."""
        status_list = self.query_one("#status-option-list", OptionList)

        # Save current highlight position
        current_highlight = status_list.highlighted

        # Clear and rebuild options with checkmarks for selected statuses
        status_list.clear_options()
        statuses = [
            "completed", "failed", "failing", "initializing", "paused",
            "pending", "recovering", "rejected", "running", "scheduling",
            "stopped", "stopping", "terminated"
        ]

        for status in statuses:
            prefix = "✓ " if status in self.status_filter else "  "
            status_list.add_option(Option(f"{prefix}{status}", id=status))

        # Restore highlight position
        if current_highlight is not None:
            status_list.highlighted = current_highlight

    def refresh_data(self) -> None:
        """Refresh data (called by timer or manually)."""
        self.run_worker(self.fetch_data, thread=True, exclusive=True)

    def action_refresh(self) -> None:
        """Manual refresh action (triggered by 'r' key)."""
        self.refresh_data()

    def action_blur_filter(self) -> None:
        """Blur the filter input to allow app-level keybindings."""
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.has_focus:
            self.set_focus(None)

    def action_clear_filter(self) -> None:
        """Clear the filter input."""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.value = ""
        self.filter_text = ""
        self.refresh_data()

    def action_clear_status_filter(self) -> None:
        """Clear the status filter."""
        self.status_filter.clear()
        self.update_status_filter_display()
        self.refresh_data()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        if event.input.id == "filter-input":
            self.filter_text = event.value.lower()
            # Trigger a refresh to apply the filter
            self.refresh_data()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle status filter option selection."""
        if event.option_list.id == "status-option-list":
            option_id = str(event.option.id)
            # Toggle the status in the filter set
            if option_id in self.status_filter:
                self.status_filter.remove(option_id)
            else:
                self.status_filter.add(option_id)
            # Update the display to show checkmarks
            self.update_status_filter_display()
            # Trigger a refresh to apply the filter
            self.refresh_data()

    def on_key(self, event) -> None:
        """Handle key events globally."""
        # Allow Ctrl+C to quit even when input is focused
        if event.key == "ctrl+c":
            self.action_quit()
            event.prevent_default()
            event.stop()
        # Allow Ctrl+X to clear filter even when input is focused
        elif event.key == "ctrl+x":
            self.action_clear_filter()
            event.prevent_default()
            event.stop()
        # Allow Ctrl+S to clear status filter
        elif event.key == "ctrl+s":
            self.action_clear_status_filter()
            event.prevent_default()
            event.stop()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data tables."""
        row_index = event.cursor_row

        if event.data_table.id == "jobs-table":
            if row_index in self.job_id_map:
                job_id = self.job_id_map[row_index]
                self.run_worker(lambda: self.fetch_and_show_job(job_id), thread=True, exclusive=False)

        elif event.data_table.id == "execution-contexts-table":
            if row_index in self.ex_id_map:
                ex_id = self.ex_id_map[row_index]
                self.run_worker(lambda: self.fetch_and_show_ex(ex_id), thread=True, exclusive=False)

        elif event.data_table.id == "controllers-table":
            if row_index in self.controller_id_map:
                ex_id = self.controller_id_map[row_index]
                self.run_worker(lambda: self.fetch_and_show_ex(ex_id), thread=True, exclusive=False)

    def fetch_and_show_job(self, job_id: str) -> None:
        """Fetch job details and show modal (runs in thread)."""
        try:
            job_data = self.client.fetch_job_by_id(job_id)
            self.call_from_thread(self.show_job_modal, job_data, job_id)
        except Exception as e:
            error_data = {"error": str(e)}
            self.call_from_thread(self.show_job_modal, error_data, job_id)

    def show_job_modal(self, job_data: dict, job_id: str) -> None:
        """Show the job details modal (called from main thread)."""
        job_url = f"{self.url}/v1/jobs/{job_id}"
        modal = JsonModal(job_data, title=f"Job Details: {job_id[:8]}", url=job_url)
        self.push_screen(modal)

    def fetch_and_show_ex(self, ex_id: str) -> None:
        """Fetch execution context details and show modal (runs in thread)."""
        try:
            ex_data = self.client.fetch_execution_context_by_id(ex_id)
            self.call_from_thread(self.show_ex_modal, ex_data, ex_id)
        except Exception as e:
            error_data = {"error": str(e)}
            self.call_from_thread(self.show_ex_modal, error_data, ex_id)

    def show_ex_modal(self, ex_data: dict, ex_id: str) -> None:
        """Show the execution context details modal (called from main thread)."""
        ex_url = f"{self.url}/v1/ex/{ex_id}"
        modal = JsonModal(ex_data, title=f"Execution Context: {ex_id[:8]}", url=ex_url)
        self.push_screen(modal)

    def action_quit(self) -> None:
        """Quit the application."""
        # Exit immediately without waiting for HTTP requests to complete
        # The httpx client will be cleaned up when the process exits
        self.exit()
