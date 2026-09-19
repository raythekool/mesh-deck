"""Primary Textual console for Mesh-Deck."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual import work
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, RichLog, Select, Static
from textual.widgets.option_list import Option

from mesh_deck.core.settings import Settings
from mesh_deck.i18n import command_descriptions, t
from mesh_deck.core.events import DeviceConnectionInfo, MeshMessage
from mesh_deck.ui.device_selector import DeviceSelectorScreen
from mesh_deck.ui.completer import Completion, MeshDeckCompleter
from mesh_deck.ui.tables import render_message

if TYPE_CHECKING:
    from mesh_deck.commands.dispatcher import CommandDispatcher
    from mesh_deck.core.radio_client import RadioClient


class TextualConsole:
    """Small Rich Console-compatible output bridge for command handlers."""

    def __init__(self, app: MeshDeckApp) -> None:
        self.app = app

    def print(self, *objects: Any, **kwargs: Any) -> None:
        for obj in objects:
            self._invoke(self.app.write_output, obj)

    def clear(self) -> None:
        self._invoke(self.app.clear_output)

    def open_node_explorer(self, node_store: Any, local_node: Any) -> None:
        self._invoke(self.app.open_node_explorer, node_store, local_node)

    def open_channel_chat(self, radio_client: Any) -> None:
        self._invoke(self.app.open_channel_chat, radio_client)

    def open_settings(self) -> None:
        self._invoke(self.app.open_settings)

    def update_language(self, language: str) -> None:
        self._invoke(self.app.update_language, language)

    def restart_console(self) -> None:
        self._invoke(self.app.restart_console)

    def notify_message(self, msg: MeshMessage) -> None:
        self._invoke(self.app.notify_message, msg)

    def _invoke(self, callback: Any, *args: Any) -> None:
        if self.app._thread_id == threading.get_ident():
            callback(*args)
        else:
            self.app.call_from_thread(callback, *args)


class SettingsScreen(ModalScreen[None]):
    """Edit persistent console preferences with native Textual controls."""

    CSS = """
    SettingsScreen { align: center middle; background: #000000aa; }
    #settings-dialog { width: 64; height: auto; padding: 1 2; background: #10212b; border: round #00f3ff; }
    #settings-dialog Label { margin-top: 1; color: #9fffd0; }
    #settings-actions { height: auto; margin-top: 2; align-horizontal: right; }
    #settings-actions Button { margin-left: 1; }
    """

    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Label(t("SETTINGS_DIALOG_TITLE", self.settings.language))
            yield Label(t("SETTINGS_LANGUAGE", self.settings.language))
            yield Select([("Italiano", "it"), ("English", "en")], value=self.settings.language, id="language")
            yield Label(t("SETTINGS_THEME", self.settings.language))
            yield Select([(theme, theme) for theme in ("cyberpunk", "high_contrast", "amber", "matrix")], value=self.settings.theme, id="theme")
            yield Label(t("SETTINGS_SORT", self.settings.language))
            yield Select([(sort, sort) for sort in ("last_heard", "snr", "hops", "name")], value=self.settings.default_sort, id="sort")
            yield Label(t("SETTINGS_PORT", self.settings.language))
            yield Input(value=self.settings.default_port or "", placeholder=t("SETTINGS_AUTO_PORT", self.settings.language), id="port")
            yield Label(t("SETTINGS_NOTIFICATIONS", self.settings.language))
            yield Select(
                [(t("SETTINGS_ON", self.settings.language), "on"), (t("SETTINGS_OFF", self.settings.language), "off")],
                value="on" if self.settings.notifications_enabled else "off",
                id="notifications",
            )
            yield Label(t("SETTINGS_HISTORY", self.settings.language))
            yield Select(
                [(t("SETTINGS_ON", self.settings.language), "on"), (t("SETTINGS_OFF", self.settings.language), "off")],
                value="on" if self.settings.history_enabled else "off",
                id="history",
            )
            with Horizontal(id="settings-actions"):
                yield Button(t("SETTINGS_CANCEL", self.settings.language), id="cancel")
                yield Button(t("SETTINGS_SAVE", self.settings.language), variant="success", id="save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
            return
        self.settings.update(
            language=str(self.query_one("#language", Select).value),
            theme=str(self.query_one("#theme", Select).value),
            default_sort=str(self.query_one("#sort", Select).value),
            default_port=self.query_one("#port", Input).value.strip() or None,
            notifications_enabled=str(self.query_one("#notifications", Select).value) == "on",
            history_enabled=str(self.query_one("#history", Select).value) == "on",
        )
        self.app.update_language(self.settings.language)
        self.dismiss()


class ConnectionScreen(ModalScreen[None]):
    """Show progress and recoverable failures while the radio handshakes."""

    CSS = """
    ConnectionScreen { align: center middle; background: #000000aa; }
    #connection-dialog { width: 64; height: auto; padding: 1 2; border: round #00f3ff; background: #10212b; }
    #connection-heading { width: 100%; height: 3; background: #063b46; color: #00f3ff; content-align: center middle; text-align: center; text-style: bold; }
    #connection-status { width: 100%; height: 3; margin-top: 1; color: #e8f1f5; content-align: center middle; text-align: center; }
    #connection-back { width: 100%; margin-top: 1; display: none; }
    """

    def __init__(self, port: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.port = port

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-dialog"):
            yield Label("Connessione alla periferica", id="connection-heading")
            yield Static(f"Apertura di {self.port} e sincronizzazione del NodeDB...", id="connection-status")
            yield Button("Torna all'elenco", id="connection-back")

    def show_error(self) -> None:
        self.query_one("#connection-status", Static).update(
            f"Connessione a {self.port} non riuscita."
        )
        self.query_one("#connection-back", Button).display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connection-back":
            self.app.return_to_device_selector()


class MeshDeckApp(App):
    """Full-screen Textual command console with live radio output."""

    TITLE = "MESH-DECK"
    SUB_TITLE = "Meshtastic command console"
    BINDINGS = [
        Binding("ctrl+c", "clear_input", "Clear input", show=False),
        Binding("tab", "complete", "Complete", show=False, priority=True),
        Binding("escape", "clear_suggestions", "Dismiss", show=False),
    ]
    CSS = """
    Screen { background: #081018; color: #e8f1f5; }
    Header { background: #10212b; color: #00f3ff; }
    #output { height: 1fr; margin: 0 1; border: round #1f8794; background: #0b1720; }
    #suggestions { height: auto; max-height: 5; margin: 0 1; color: #9fffd0; background: #10212b; }
    #command { margin: 0 1 1 1; border: round #00f3ff; background: #0b1720; color: #f8fafc; }
    Footer { background: #10212b; color: #9aa9b4; }
    """

    def __init__(
        self,
        repl: MeshDeckREPL,
        devices: list[DeviceConnectionInfo] | None = None,
        preferred_port: str | None = None,
        initial_port: str | None = None,
        open_explorer_on_connect: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.repl = repl
        self.devices = devices
        self.preferred_port = preferred_port
        self.initial_port = initial_port
        self.open_explorer_on_connect = open_explorer_on_connect
        self.completions: list[Completion] = []
        self.history_position = len(self.repl.settings.command_history)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield RichLog(id="output", markup=True, wrap=True, highlight=True)
            yield OptionList(id="suggestions", compact=True)
            yield Input(placeholder=self.repl._get_prompt(), id="command")
        yield Footer()

    def on_mount(self) -> None:
        console = TextualConsole(self)
        self.repl.console = console
        self.repl.dispatcher.console = console
        self.query_one(OptionList).display = False
        if self.initial_port:
            self.begin_connection(self.initial_port)
        elif self.devices is not None:
            self.push_device_selector()
        else:
            self.activate_console()

    def push_device_selector(self) -> None:
        self.push_screen(
            DeviceSelectorScreen(self.devices or [], preferred_port=self.preferred_port),
            callback=self.on_device_selected,
        )

    def on_device_selected(self, port: str | None) -> None:
        if port is None:
            self.exit()
            return
        self.begin_connection(port)

    def begin_connection(self, port: str) -> None:
        self.push_screen(ConnectionScreen(port))
        self.connect_radio(port)

    @work(thread=True, exclusive=True)
    def connect_radio(self, port: str) -> None:
        success = self.repl.client.connect(port, blocking=True)
        self.call_from_thread(self.connection_complete, success)

    def connection_complete(self, success: bool) -> None:
        if success:
            self.pop_screen()
            self.activate_console()
            return
        if isinstance(self.screen, ConnectionScreen):
            self.screen.show_error()

    def return_to_device_selector(self) -> None:
        if isinstance(self.screen, ConnectionScreen):
            self.pop_screen()
        self.push_device_selector()

    def activate_console(self) -> None:
        self.repl.dispatcher.cmd_banner([])
        self.query_one(Input).focus()
        if self.open_explorer_on_connect:
            self.open_node_explorer(self.repl.client.store, self.repl.client.get_local_node())

    def write_output(self, renderable: Any) -> None:
        if isinstance(renderable, str):
            try:
                renderable = Text.from_markup(renderable)
            except Exception:
                renderable = Text(renderable)
        self.query_one(RichLog).write(renderable)

    def clear_output(self) -> None:
        self.query_one(RichLog).clear()

    def open_node_explorer(self, node_store: Any, local_node: Any) -> None:
        from mesh_deck.ui.interactive_table import InteractiveNodesScreen
        self.push_screen(InteractiveNodesScreen(node_store, local_node=local_node))

    def open_channel_chat(self, radio_client: Any) -> None:
        from mesh_deck.ui.channel_chat import ChannelChatScreen
        self.push_screen(ChannelChatScreen(radio_client))

    def open_settings(self) -> None:
        self.push_screen(SettingsScreen(self.repl.settings))

    def update_language(self, language: str) -> None:
        self.repl.settings.language = language
        self.sub_title = t("APP_SUBTITLE", language)
        self.repl.completer.commands = command_descriptions(language)
        self.query_one(Input).placeholder = self.repl._get_prompt()

    def restart_console(self) -> None:
        """Apply saved settings and redraw the connected command console."""
        self.repl.settings = Settings.load()
        self.update_language(self.repl.settings.language)
        self.clear_output()
        self.activate_console()

    def notify_message(self, msg: MeshMessage) -> None:
        """Show a toast notification for a newly received mesh message."""
        sender = msg.sender_name or msg.sender_short_name or msg.sender_id or "?"
        body = msg.text if len(msg.text) <= 140 else f"{msg.text[:137]}..."
        if msg.is_dm:
            title = f"🔒 DM da {sender}"
            severity = "warning"
        else:
            channel_label = msg.channel_name or msg.channel
            title = f"📡 Canale {channel_label} — {sender}"
            severity = "information"
        self.notify(body, title=title, severity=severity, timeout=6)

    def on_input_changed(self, event: Input.Changed) -> None:
        self.completions = self.repl.completer.suggestions(event.value)
        suggestions = self.query_one(OptionList)
        suggestions.set_options([
            Option(f"[bold cyan]{item.value}[/] [dim]{item.description}[/]", id=str(index))
            for index, item in enumerate(self.completions[:8])
        ])
        suggestions.display = bool(self.completions)
        suggestions.highlighted = 0 if self.completions else None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "suggestions":
            if self._execute_command_completion(event.option_index):
                return
            self._apply_completion(event.option_index)
            return
        if event.option_list.id == "devices" and event.option_index < len(self.devices or []):
            if isinstance(self.screen, DeviceSelectorScreen):
                self.screen.dismiss(self.devices[event.option_index].port)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value
        if self._execute_command_completion(0):
            return
        self._submit_command(command)

    def _submit_command(self, command: str) -> None:
        """Clear the command input and schedule command execution."""
        input_widget = self.query_one(Input)
        input_widget.value = ""
        self.clear_suggestions()
        self.history_position = len(self.repl.settings.command_history)
        self.repl.settings.add_command(command)
        self._dispatch_command(command)


    @work(thread=True, exclusive=True)
    def _dispatch_command(self, command: str) -> None:
        if not self.repl.dispatcher.dispatch(command):
            self.call_from_thread(self.exit)

    def on_key(self, event: Any) -> None:
        if event.key == "enter" and isinstance(self.focused, OptionList):
            highlighted = self.focused.highlighted
            if self.focused.id == "suggestions" and highlighted is not None:
                if self._execute_command_completion(highlighted):
                    event.stop()
                    event.prevent_default()
                    return
                self._apply_completion(highlighted)
            elif self.focused.id == "devices" and highlighted is not None:
                if isinstance(self.screen, DeviceSelectorScreen):
                    self.screen.dismiss(self.devices[highlighted].port)
            else:
                return
            event.stop()
            event.prevent_default()
            return
        if event.key == "down" and self.completions and isinstance(self.focused, Input):
            self.query_one(OptionList).focus()
            event.stop()
            event.prevent_default()
            return
        if not isinstance(self.focused, Input):
            return
        if event.key not in {"up", "down"}:
            return
        history = self.repl.settings.command_history
        if not history:
            return
        if event.key == "up":
            self.history_position = max(0, self.history_position - 1)
        else:
            self.history_position = min(len(history), self.history_position + 1)
        command = self.query_one(Input)
        command.value = history[self.history_position] if self.history_position < len(history) else ""
        command.cursor_position = len(command.value)
        event.stop()
        event.prevent_default()

    def action_complete(self) -> None:
        if not self.completions:
            return
        self._apply_completion(0)

    def _apply_completion(self, index: int) -> None:
        if index >= len(self.completions):
            return
        command = self.query_one(Input)
        candidate = self.completions[index]
        replacement_start = len(command.value) + candidate.start_position
        command.value = command.value[:replacement_start] + candidate.value
        command.cursor_position = len(command.value)
        command.focus()
        self.clear_suggestions()

    def _execute_command_completion(self, index: int) -> bool:
        """Execute a selected incomplete slash-command suggestion."""
        value = self.query_one(Input).value
        if " " in value.strip() or not value.lstrip().startswith("/"):
            return False
        if index >= len(self.completions):
            return False
        candidate = self.completions[index]
        replacement_start = len(value) + candidate.start_position
        completed_value = value[:replacement_start] + candidate.value
        if completed_value == value:
            return False
        self._submit_command(completed_value)
        return True

    def action_clear_input(self) -> None:
        self.query_one(Input).value = ""
        self.clear_suggestions()

    def action_clear_suggestions(self) -> None:
        self.clear_suggestions()

    def clear_suggestions(self) -> None:
        self.completions = []
        suggestions = self.query_one(OptionList)
        suggestions.clear_options()
        suggestions.display = False


class MeshDeckREPL:
    """Compatibility facade which launches the primary Textual application."""

    def __init__(
        self,
        radio_client: RadioClient,
        console: Console | None = None,
        dispatcher: CommandDispatcher | None = None,
    ) -> None:
        self.client = radio_client
        self.console = console or Console()
        self.settings = Settings.load()
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            from mesh_deck.commands.dispatcher import CommandDispatcher
            self.dispatcher = CommandDispatcher(self.client, console=self.console)
        self.completer = MeshDeckCompleter(
            self._get_all_nodes,
            self._get_available_ports,
            commands=command_descriptions(self.settings.language),
        )
        self.client.on_message_received(self._handle_incoming_message)

    def _get_all_nodes(self) -> list:
        return self.client.store.get_all_nodes()

    def _get_available_ports(self) -> list[str]:
        from mesh_deck.core.scanner import scan_meshtastic_ports
        return [port.port for port in scan_meshtastic_ports()]

    def _handle_incoming_message(self, msg: MeshMessage) -> None:
        self.console.print(render_message(msg))
        if self.settings.notifications_enabled:
            notifier = getattr(self.console, "notify_message", None)
            if callable(notifier):
                notifier(msg)

    def _get_prompt(self) -> str:
        """Return the contextual label used by the Textual command input."""
        local = self.client.get_local_node()
        name = ""
        if local:
            name = local.short_name or local.long_name or local.id
        return t("COMMAND_PLACEHOLDER", self.settings.language, name=name or "-")

    def run(self) -> None:
        MeshDeckApp(self).run()
