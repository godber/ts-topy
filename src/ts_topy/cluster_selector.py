"""Cluster selection screen for ts-topy."""

from typing import Dict, Callable, Optional
from pathlib import Path

import httpx

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Static, OptionList, Button, Input, Label
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from ts_topy.aliases import ClusterAliases


class FirstClusterModal(ModalScreen):
    """Modal screen to inform user about the aliases file being created."""

    BINDINGS = [
        ("escape", "dismiss", "OK"),
    ]

    DEFAULT_CSS = """
    FirstClusterModal {
        align: center middle;
    }

    FirstClusterModal > Vertical {
        width: 80;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
    }

    FirstClusterModal .modal-title {
        width: 100%;
        text-align: center;
        padding: 1;
        background: $success;
        text-style: bold;
    }

    FirstClusterModal .modal-content {
        width: 100%;
        padding: 2;
    }

    FirstClusterModal .button-row {
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    FirstClusterModal Button {
        width: 20;
    }
    """

    def __init__(self, aliases_path: Path):
        """Initialize the first cluster modal.

        Args:
            aliases_path: Path to the aliases file that was created
        """
        super().__init__()
        self.aliases_path = aliases_path

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Vertical(
            Static("Cluster Saved Successfully!", classes="modal-title"),
            Static(
                f"Your cluster has been saved to:\n\n{self.aliases_path}\n\n"
                "You can manually edit this file to add or modify clusters.\n"
                "The file will be used for future connections.",
                classes="modal-content"
            ),
            Horizontal(
                Button("OK", variant="primary", id="ok-button"),
                classes="button-row",
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "ok-button":
            self.dismiss()


class AddClusterModal(ModalScreen):
    """Modal screen to add a new cluster."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
    ]

    DEFAULT_CSS = """
    AddClusterModal {
        align: center middle;
    }

    AddClusterModal > Vertical {
        width: 70;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    AddClusterModal .modal-title {
        width: 100%;
        text-align: center;
        padding: 1;
        background: $primary;
        text-style: bold;
    }

    AddClusterModal .form-row {
        height: auto;
        margin: 1 0;
    }

    AddClusterModal Label {
        width: 15;
        padding: 1 0;
    }

    AddClusterModal Input {
        width: 1fr;
    }

    AddClusterModal .button-row {
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    AddClusterModal Button {
        margin: 0 1;
    }

    AddClusterModal .error-message {
        color: $error;
        padding: 0 1;
        height: auto;
    }

    AddClusterModal .success-message {
        color: $success;
        padding: 0 1;
        height: auto;
    }

    AddClusterModal .info-message {
        color: $text;
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, aliases: ClusterAliases, on_added: Callable[[str, str], None], is_first_cluster: bool = False):
        """Initialize the add cluster modal.

        Args:
            aliases: ClusterAliases instance to save to
            on_added: Callback when cluster is added (name, url)
            is_first_cluster: Whether this is the first cluster being added
        """
        super().__init__()
        self.aliases = aliases
        self.on_added = on_added
        self.saved_cluster: Optional[tuple[str, str]] = None  # (name, url) if saved
        self.is_first_cluster = is_first_cluster

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Vertical(
            Static("Add New Cluster", classes="modal-title"),
            Horizontal(
                Label("Name:"),
                Input(placeholder="e.g., production", id="cluster-name"),
                classes="form-row",
            ),
            Horizontal(
                Label("Host URL:"),
                Input(placeholder="e.g., http://localhost:5678", id="cluster-host"),
                classes="form-row",
            ),
            Static("", id="status-message", classes="info-message"),
            Horizontal(
                Button("Test Connection", variant="default", id="test-button"),
                Button("Save", variant="primary", id="save-button"),
                Button("Cancel", variant="default", id="cancel-button"),
                classes="button-row",
            ),
        )

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#cluster-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(self.saved_cluster)
        elif event.button.id == "save-button":
            self._save_cluster()
        elif event.button.id == "test-button":
            self._test_connection()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in inputs."""
        if event.input.id == "cluster-name":
            # Move to host input
            self.query_one("#cluster-host", Input).focus()
        elif event.input.id == "cluster-host":
            # Submit the form
            self._save_cluster()

    def _test_connection(self) -> None:
        """Test connection to the cluster."""
        host_input = self.query_one("#cluster-host", Input)
        status_msg = self.query_one("#status-message", Static)
        test_button = self.query_one("#test-button", Button)

        host = host_input.value.strip()

        if not host:
            status_msg.update("Error: Host URL is required")
            status_msg.styles.color = "red"
            host_input.focus()
            return

        if not host.startswith(("http://", "https://")):
            status_msg.update("Error: Host URL must start with http:// or https://")
            status_msg.styles.color = "red"
            host_input.focus()
            return

        # Disable button and show testing message
        test_button.disabled = True
        status_msg.update("Testing connection...")
        status_msg.styles.color = "white"

        # Run the test in a worker thread
        self.run_worker(lambda: self._do_test_connection(host), thread=True)

    def _do_test_connection(self, host: str) -> tuple[bool, str]:
        """Test connection in worker thread.

        Args:
            host: The host URL to test

        Returns:
            Tuple of (success, message)
        """
        try:
            client = httpx.Client(timeout=5.0)
            response = client.get(f"{host}/v1/cluster/state")
            client.close()

            if response.status_code == 200:
                return (True, f"Connection successful! (Status: {response.status_code})")
            else:
                return (False, f"Connection failed: HTTP {response.status_code}")
        except httpx.TimeoutException:
            return (False, "Connection timeout (5s)")
        except httpx.ConnectError:
            return (False, "Connection refused - check URL and port")
        except Exception as e:
            return (False, f"Connection error: {str(e)}")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion."""
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            status_msg = self.query_one("#status-message", Static)
            test_button = self.query_one("#test-button", Button)
            save_button = self.query_one("#save-button", Button)

            # Check if this is a test-only result or a test-and-save result
            if len(result) == 2:
                # Test only
                success, message = result
                status_msg.update(message)
                if success:
                    status_msg.styles.color = "green"
                else:
                    status_msg.styles.color = "red"
                test_button.disabled = False
            elif len(result) == 4:
                # Test and save
                success, message, name, host = result
                status_msg.update(message)
                if success:
                    status_msg.styles.color = "green"
                    self.on_added(name, host)
                    self.saved_cluster = (name, host)

                    # If this is the first cluster, show info modal
                    if self.is_first_cluster:
                        def handle_info_dismissed(result) -> None:
                            self.dismiss(self.saved_cluster)

                        info_modal = FirstClusterModal(self.aliases.aliases_path)
                        self.app.push_screen(info_modal, handle_info_dismissed)
                    else:
                        self.dismiss(self.saved_cluster)
                else:
                    status_msg.styles.color = "red"
                    save_button.disabled = False

    def _save_cluster(self) -> None:
        """Validate and save the cluster."""
        name_input = self.query_one("#cluster-name", Input)
        host_input = self.query_one("#cluster-host", Input)
        status_msg = self.query_one("#status-message", Static)
        save_button = self.query_one("#save-button", Button)

        name = name_input.value.strip()
        host = host_input.value.strip()

        # Validation
        if not name:
            status_msg.update("Error: Cluster name is required")
            status_msg.styles.color = "red"
            name_input.focus()
            return

        if not host:
            status_msg.update("Error: Host URL is required")
            status_msg.styles.color = "red"
            host_input.focus()
            return

        if not host.startswith(("http://", "https://")):
            status_msg.update("Error: Host URL must start with http:// or https://")
            status_msg.styles.color = "red"
            host_input.focus()
            return

        # Disable save button and test connection first
        save_button.disabled = True
        status_msg.update("Testing connection before saving...")
        status_msg.styles.color = "white"

        # Run the test in a worker thread, then save if successful
        self.run_worker(lambda: self._test_and_save(name, host), thread=True)

    def _test_and_save(self, name: str, host: str) -> tuple[bool, str, str, str]:
        """Test connection and save if successful.

        Args:
            name: Cluster name
            host: Cluster host URL

        Returns:
            Tuple of (success, message, name, host)
        """
        # Test the connection
        success, message = self._do_test_connection(host)

        # If successful, save the cluster
        if success:
            try:
                self.aliases.add_cluster(name, host)
                return (True, "Connection successful! Cluster saved.", name, host)
            except Exception as e:
                return (False, f"Connection successful but save failed: {str(e)}", name, host)
        else:
            return (False, message, name, host)


class ClusterSelectorScreen(Screen):
    """Screen for selecting a Teraslice cluster."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("a", "add_cluster", "Add Cluster"),
    ]

    CSS = """
    ClusterSelectorScreen {
        align: center middle;
    }

    #selector-container {
        width: 80;
        height: auto;
        max-height: 80%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    #title {
        width: 100%;
        text-align: center;
        padding: 1;
        background: $primary;
        text-style: bold;
    }

    #option-list {
        width: 100%;
        height: auto;
        max-height: 30;
        margin: 1 0;
    }

    #add-button-container {
        width: 100%;
        align: center middle;
        height: auto;
        margin: 1 0;
    }

    #add-cluster-button {
        width: 30;
    }

    #no-clusters-message {
        width: 100%;
        text-align: center;
        padding: 2;
    }
    """

    def __init__(self, aliases: ClusterAliases):
        """Initialize the cluster selector.

        Args:
            aliases: ClusterAliases instance
        """
        super().__init__()
        self.aliases = aliases
        self.selected_url: str | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        clusters = self.aliases.get_clusters()

        # If no clusters exist, show a message
        if not clusters:
            yield Container(
                Static("Select a Teraslice Cluster", id="title"),
                Static(
                    "No clusters configured yet.\nClick 'Add New Cluster' to get started.",
                    id="no-clusters-message"
                ),
                Horizontal(
                    Button("Add New Cluster", id="add-cluster-button"),
                    id="add-button-container",
                ),
                id="selector-container"
            )
        else:
            options = [
                Option(f"{name}: {url}", id=name)
                for name, url in sorted(clusters.items())
            ]

            yield Container(
                Static("Select a Teraslice Cluster", id="title"),
                OptionList(*options, id="option-list"),
                Horizontal(
                    Button("Add New Cluster", id="add-cluster-button"),
                    id="add-button-container",
                ),
                id="selector-container"
            )
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        clusters = self.aliases.get_clusters()

        if clusters:
            option_list = self.query_one("#option-list", OptionList)
            option_list.focus()
        else:
            # If no clusters, automatically show the add cluster modal
            self.action_add_cluster()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        cluster_name = event.option.id
        if cluster_name:
            url = self.aliases.get_url(cluster_name)
            if url:
                self.selected_url = url
                self.dismiss(self.selected_url)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "add-cluster-button":
            self.action_add_cluster()

    def action_add_cluster(self) -> None:
        """Show the add cluster modal."""
        # Check if this will be the first cluster
        is_first = not self.aliases.has_aliases()

        def handle_cluster_added(name: str, host: str) -> None:
            # Refresh the option list
            self._refresh_clusters()

        def handle_modal_dismissed(result: Optional[tuple[str, str]]) -> None:
            # If a cluster was saved, automatically select it
            if result:
                name, host = result
                self.selected_url = host
                self.dismiss(self.selected_url)
            else:
                # Just refresh the list
                self._refresh_clusters()

        modal = AddClusterModal(self.aliases, handle_cluster_added, is_first_cluster=is_first)
        self.app.push_screen(modal, handle_modal_dismissed)

    def _refresh_clusters(self) -> None:
        """Refresh the cluster list."""
        clusters = self.aliases.get_clusters()

        # If we now have clusters but didn't before, we need to rebuild the UI
        if clusters:
            try:
                option_list = self.query_one("#option-list", OptionList)
                option_list.clear_options()
                for name, url in sorted(clusters.items()):
                    option_list.add_option(Option(f"{name}: {url}", id=name))
                option_list.focus()
            except Exception:
                # OptionList doesn't exist (first cluster case), ignore
                pass

    def action_quit(self) -> None:
        """Quit without selecting."""
        self.dismiss(None)


class ClusterSelectorApp(App):
    """Temporary app to show cluster selector."""

    def __init__(self, aliases: ClusterAliases):
        """Initialize the selector app.

        Args:
            aliases: ClusterAliases instance
        """
        super().__init__()
        self.aliases = aliases
        self.selected_url: str | None = None

    def on_mount(self) -> None:
        """Show the selector screen on mount."""
        def handle_result(url: str | None) -> None:
            self.selected_url = url
            self.exit()

        selector = ClusterSelectorScreen(self.aliases)
        self.push_screen(selector, handle_result)
