"""Primary Textual console for Mesh-Deck."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, RichLog, Select, Static
from textual.widgets.option_list import Option

from mesh_deck.core.settings import Settings
from mesh_deck.i18n import command_descriptions, t
from mesh_deck.core.events import DeviceConnectionInfo, MeshMessage, NodeData
from mesh_deck.ui.device_selector import DeviceSelectorScreen
from mesh_deck.ui.completer import Completion, MeshDeckCompleter
from mesh_deck.ui.tables import render_message, render_node_detail
from mesh_deck.ui.theme import (
    DEFAULT_THEME,
    THEME_COLORS,
    ThemedApp,
    format_role,
    format_snr,
    format_time_ago,
    set_theme,
    theme_names,
)

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

    def open_node_explorer(self, node_store: Any, local_node: Any, lang: str = "it") -> None:
        self._invoke(self.app.open_node_explorer, node_store, local_node, lang)

    def open_channel_chat(self, radio_client: Any, lang: str = "it") -> None:
        self._invoke(self.app.open_channel_chat, radio_client, lang)

    def open_settings(self) -> None:
        self._invoke(self.app.open_settings)

    def update_language(self, language: str) -> None:
        self._invoke(self.app.update_language, language)

    def apply_theme(self, theme: str) -> None:
        self._invoke(self.app.apply_theme, theme)

    def restart_console(self) -> None:
        self._invoke(self.app.restart_console)

    def notify_message(self, msg: MeshMessage) -> None:
        self._invoke(self.app.notify_message, msg)

    def request_sidebar_refresh(self) -> None:
        self._invoke(self.app.request_sidebar_refresh)

    def _invoke(self, callback: Any, *args: Any) -> None:
        if threading.get_ident() == getattr(self.app, "ui_thread_id", None):
            callback(*args)
        else:
            self.app.call_from_thread(callback, *args)


class SettingsScreen(ModalScreen[None]):
    """Edit persistent console preferences with native Textual controls."""

    CSS = """
    SettingsScreen { align: center middle; background: #000000aa; }
    #settings-dialog { width: 64; height: auto; padding: 1 2; background: $mesh-bg-elevated; border: round $mesh-primary; }
    #settings-dialog Label { margin-top: 1; color: $mesh-secondary; }
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
            yield Select(
                [(t(f"THEME_DESC_{name.upper()}", self.settings.language), name) for name in theme_names()],
                value=self.settings.theme if self.settings.theme in theme_names() else DEFAULT_THEME,
                id="theme",
            )
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
        self.app.apply_theme(self.settings.theme)
        self.dismiss()


class ConnectionScreen(ModalScreen[None]):
    """Show progress and recoverable failures while the radio handshakes."""

    CSS = """
    ConnectionScreen { align: center middle; background: #000000aa; }
    #connection-dialog { width: 64; height: auto; padding: 1 2; border: round $mesh-primary; background: $mesh-bg-elevated; }
    #connection-heading { width: 100%; height: 3; background: $mesh-bg-header; color: $mesh-primary; content-align: center middle; text-align: center; text-style: bold; }
    #connection-status { width: 100%; height: 3; margin-top: 1; color: $mesh-text; content-align: center middle; text-align: center; }
    #connection-back { width: 100%; margin-top: 1; display: none; }
    """

    def __init__(self, port: str, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.port = port
        self.lang = lang

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-dialog"):
            yield Label(t("CONNECTION_HEADING", self.lang), id="connection-heading")
            yield Static(t("CONNECTION_STATUS", self.lang, port=self.port), id="connection-status")
            yield Button(t("CONNECTION_BACK", self.lang), id="connection-back")

    def show_error(self) -> None:
        self.query_one("#connection-status", Static).update(
            t("CONNECTION_FAILED", self.lang, port=self.port)
        )
        self.query_one("#connection-back", Button).display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connection-back":
            self.app.return_to_device_selector()


SIDEBAR_MIN_WIDTH = 18
SIDEBAR_MAX_WIDTH_RATIO = 0.6
# A busy mesh can emit node updates several times a second; refreshes are
# coalesced into at most one repaint per this interval.
SIDEBAR_REFRESH_INTERVAL = 2.0
SIDEBAR_SORT_CYCLE = ["last_heard", "snr", "hops", "name"]
SIDEBAR_SORT_LABELS = {
    "last_heard": "SIDEBAR_SORT_LAST_HEARD",
    "snr": "SIDEBAR_SORT_SNR",
    "hops": "SIDEBAR_SORT_HOPS",
    "name": "SIDEBAR_SORT_NAME",
}
SIDEBAR_FILTER_CYCLE = ["all", "active", "favorites"]
SIDEBAR_FILTER_LABELS = {
    "all": "SIDEBAR_FILTER_ALL",
    "active": "SIDEBAR_FILTER_ACTIVE",
    "favorites": "SIDEBAR_FILTER_FAVORITES",
}


class SidebarResizeHandle(Static):
    """Thin draggable divider that lets the user resize the node sidebar."""

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        self.capture_mouse()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self.app.mouse_captured is not self:
            return
        self.release_mouse()
        width = int(self.screen.query_one("#sidebar").size.width)
        self.app.repl.settings.update(sidebar_width=width)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.app.mouse_captured is not self:
            return
        max_width = max(SIDEBAR_MIN_WIDTH, int(self.screen.size.width * SIDEBAR_MAX_WIDTH_RATIO))
        width = max(SIDEBAR_MIN_WIDTH, min(max_width, event.screen_x))
        self.screen.query_one("#sidebar").styles.width = width


class SidebarControlButton(Static, can_focus=True):
    """Compact clickable pill used for the sidebar sort/filter controls."""

    def on_click(self, event: events.Click) -> None:
        event.stop()
        if self.id == "sidebar-sort":
            self.app.action_cycle_sidebar_sort()
        elif self.id == "sidebar-filter":
            self.app.action_cycle_sidebar_filter()


class MeshDeckApp(ThemedApp, App):
    """Full-screen Textual command console with live radio output."""

    TITLE = "MESH-DECK"
    SUB_TITLE = "Meshtastic command console"
    BINDINGS = [
        Binding("ctrl+c", "clear_input", "Clear input", show=False),
        Binding("tab", "complete", "Complete", show=False, priority=True),
        Binding("escape", "clear_suggestions", "Dismiss", show=False),
        Binding("ctrl+b", "toggle_sidebar", "Toggle sidebar", show=True),
    ]
    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    Header { background: $mesh-bg-elevated; color: $mesh-primary; }
    #body { height: 1fr; }
    #sidebar { width: 32; min-width: 18; border: round $mesh-border-soft; background: $mesh-bg-panel; }
    #sidebar-title { width: 100%; height: 1; background: $mesh-bg-header; color: $mesh-primary; content-align: center middle; text-style: bold; }
    #sidebar-controls { height: 1; background: $mesh-bg-panel; }
    #sidebar-controls > SidebarControlButton { width: 1fr; height: 1; content-align: center middle; background: $mesh-bg-elevated; color: $mesh-secondary; text-style: bold; }
    #sidebar-controls > SidebarControlButton:hover { background: $mesh-border-soft; color: $mesh-bg; }
    #sidebar-nodes { height: 1fr; background: $mesh-bg-panel; color: $mesh-text; }
    #sidebar-resizer { width: 1; height: 1fr; background: $mesh-border-soft; }
    #sidebar-resizer:hover { background: $mesh-primary; }
    #main { height: 1fr; }
    #node-detail { height: auto; max-height: 20; margin: 0 1; border: round $mesh-purple; background: $mesh-bg-panel; display: none; }
    #output { height: 1fr; margin: 0 1; border: round $mesh-border-soft; background: $mesh-bg-panel; }
    #suggestions { height: auto; max-height: 5; margin: 0 1; color: $mesh-secondary; background: $mesh-bg-elevated; }
    #command { margin: 0 1 1 1; border: round $mesh-primary; background: $mesh-bg-panel; color: $mesh-text; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
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
        self._sidebar_refresh_pending = False
        self._sidebar_node_ids: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label(t("SIDEBAR_TITLE", self.repl.settings.language), id="sidebar-title")
                with Horizontal(id="sidebar-controls"):
                    yield SidebarControlButton(id="sidebar-sort")
                    yield SidebarControlButton(id="sidebar-filter")
                yield OptionList(id="sidebar-nodes", compact=True)
            yield SidebarResizeHandle(id="sidebar-resizer")
            with Vertical(id="main"):
                yield Static(id="node-detail")
                yield RichLog(id="output", markup=True, wrap=True, highlight=True)
                yield OptionList(id="suggestions", compact=True)
                yield Input(placeholder=self.repl._get_prompt(), id="command")
        yield Footer()

    def on_mount(self) -> None:
        # Captured before anything can post from a radio thread, so
        # TextualConsole can tell "already on the UI thread" from
        # "must marshal via call_from_thread" without private Textual state.
        self.ui_thread_id = threading.get_ident()
        console = TextualConsole(self)
        self.repl.console = console
        self.repl.dispatcher.console = console
        self.query_one("#suggestions", OptionList).display = False
        self.query_one("#sidebar").display = self.repl.settings.sidebar_enabled
        self.query_one("#sidebar").styles.width = self.repl.settings.sidebar_width
        self.update_language(self.repl.settings.language)
        if self.initial_port:
            self.begin_connection(self.initial_port)
        elif self.devices is not None:
            self.push_device_selector()
        else:
            self.activate_console()

    def push_device_selector(self) -> None:
        self.push_screen(
            DeviceSelectorScreen(self.devices or [], preferred_port=self.preferred_port, lang=self.repl.settings.language),
            callback=self.on_device_selected,
        )

    def on_device_selected(self, port: str | None) -> None:
        if port is None:
            self.exit()
            return
        self.begin_connection(port)

    def begin_connection(self, port: str) -> None:
        self.push_screen(ConnectionScreen(port, lang=self.repl.settings.language))
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
        self.refresh_sidebar()
        if self.open_explorer_on_connect:
            self.open_node_explorer(self.repl.client.store, self.repl.client.get_local_node(), self.repl.settings.language)

    def refresh_sidebar(self) -> None:
        """Populate the node sidebar from the current NodeStore snapshot."""
        self._sidebar_refresh_pending = False
        lang = self.repl.settings.language
        sort_by = self.repl.settings.default_sort
        filter_state = self.repl.settings.sidebar_filter
        self.query_one("#sidebar-sort", Static).update(f"\u2195 {t(SIDEBAR_SORT_LABELS.get(sort_by, 'SIDEBAR_SORT_LAST_HEARD'), lang)}")
        self.query_one("#sidebar-sort", Static).tooltip = t("SIDEBAR_SORT_TOOLTIP", lang)
        self.query_one("#sidebar-filter", Static).update(f"\u2691 {t(SIDEBAR_FILTER_LABELS.get(filter_state, 'SIDEBAR_FILTER_ALL'), lang)}")
        self.query_one("#sidebar-filter", Static).tooltip = t("SIDEBAR_FILTER_TOOLTIP", lang)
        local = self.repl.client.get_local_node()
        local_id = local.id if local else None
        nodes = self.repl.client.store.get_all_nodes(
            sort_by=sort_by,
            active_only=filter_state == "active",
            favorites_only=filter_state == "favorites",
        )
        sidebar = self.query_one("#sidebar-nodes", OptionList)
        sidebar.clear_options()
        self._sidebar_node_ids = [node.id for node in nodes]
        if not nodes:
            sidebar.add_option(Option(f"[dim]{t('SIDEBAR_EMPTY', lang)}[/]", disabled=True))
            return
        for node in nodes:
            label = node.short_name or node.display_name or node.id
            long_name = node.long_name or node.display_name or node.id
            marker = "★ " if node.id == local_id else ""
            sidebar.add_option(Option(
                f"{marker}[bold {THEME_COLORS['primary']}]{label}[/] {format_role(node.role)}\n"
                f"[italic {THEME_COLORS['muted']}]{long_name}[/] · {format_snr(node.snr)} · {format_time_ago(node.last_heard, lang)}"
            ))
        sidebar.highlighted = 0

    def request_sidebar_refresh(self) -> None:
        """Schedule a coalesced sidebar repaint after a radio-side node update.

        Node updates arrive from the PubSub thread and can burst; repainting
        the whole OptionList per packet would thrash the UI, so bursts collapse
        into a single repaint at most every SIDEBAR_REFRESH_INTERVAL seconds.
        """
        if not self.repl.settings.sidebar_enabled or self._sidebar_refresh_pending:
            return
        self._sidebar_refresh_pending = True
        self.set_timer(SIDEBAR_REFRESH_INTERVAL, self._flush_sidebar_refresh)

    def _flush_sidebar_refresh(self) -> None:
        if not self._sidebar_refresh_pending:
            return
        if not self.repl.settings.sidebar_enabled or not self.is_mounted:
            self._sidebar_refresh_pending = False
            return
        self.refresh_sidebar()

    def action_toggle_sidebar(self) -> None:
        enabled = not self.repl.settings.sidebar_enabled
        self.repl.settings.update(sidebar_enabled=enabled)
        self.query_one("#sidebar").display = enabled
        if enabled:
            self.refresh_sidebar()

    def action_cycle_sidebar_sort(self) -> None:
        current = self.repl.settings.default_sort
        index = SIDEBAR_SORT_CYCLE.index(current) if current in SIDEBAR_SORT_CYCLE else -1
        next_sort = SIDEBAR_SORT_CYCLE[(index + 1) % len(SIDEBAR_SORT_CYCLE)]
        self.repl.settings.update(default_sort=next_sort)
        self.refresh_sidebar()

    def action_cycle_sidebar_filter(self) -> None:
        current = self.repl.settings.sidebar_filter
        index = SIDEBAR_FILTER_CYCLE.index(current) if current in SIDEBAR_FILTER_CYCLE else -1
        next_filter = SIDEBAR_FILTER_CYCLE[(index + 1) % len(SIDEBAR_FILTER_CYCLE)]
        self.repl.settings.update(sidebar_filter=next_filter)
        self.refresh_sidebar()

    def write_output(self, renderable: Any) -> None:
        if isinstance(renderable, str):
            try:
                renderable = Text.from_markup(renderable)
            except Exception:
                renderable = Text(renderable)
        self.query_one(RichLog).write(renderable)

    def clear_output(self) -> None:
        self.query_one(RichLog).clear()

    def open_node_explorer(self, node_store: Any, local_node: Any, lang: str = "it") -> None:
        from mesh_deck.ui.interactive_table import InteractiveNodesScreen
        self.push_screen(InteractiveNodesScreen(node_store, local_node=local_node, lang=lang))

    def open_channel_chat(self, radio_client: Any, lang: str = "it") -> None:
        from mesh_deck.ui.channel_chat import ChannelChatScreen
        self.push_screen(ChannelChatScreen(radio_client, lang=lang))

    def open_settings(self) -> None:
        self.push_screen(SettingsScreen(self.repl.settings))

    def apply_theme(self, name: str | None = None) -> None:
        """Activate a palette and repaint every Rich and Textual surface."""
        set_theme(name if name is not None else self.repl.settings.theme)
        self.refresh_css()
        if self.repl.settings.sidebar_enabled:
            self.refresh_sidebar()

    def update_language(self, language: str) -> None:
        self.repl.settings.language = language
        self.sub_title = t("APP_SUBTITLE", language)
        self.repl.completer.commands = command_descriptions(language)
        self.repl.completer.lang = language
        self.query_one(Input).placeholder = self.repl._get_prompt()
        self._bindings.key_to_bindings["ctrl+b"] = [
            Binding("ctrl+b", "toggle_sidebar", t("SIDEBAR_TOGGLE", language), show=True)
        ]

    def restart_console(self) -> None:
        """Apply saved settings and redraw the connected command console."""
        self.repl.settings = Settings.load()
        self.update_language(self.repl.settings.language)
        self.apply_theme(self.repl.settings.theme)
        self.query_one("#sidebar").display = self.repl.settings.sidebar_enabled
        self.query_one("#sidebar").styles.width = self.repl.settings.sidebar_width
        self.close_node_detail()
        self.clear_output()
        self.activate_console()

    def notify_message(self, msg: MeshMessage) -> None:
        """Show a toast notification for a newly received mesh message."""
        lang = self.repl.settings.language
        sender = msg.sender_name or msg.sender_short_name or msg.sender_id or "?"
        body = msg.text if len(msg.text) <= 140 else f"{msg.text[:137]}..."
        if msg.is_dm:
            title = t("NOTIFY_DM_TITLE", lang, sender=sender)
            severity = "warning"
        else:
            channel_label = msg.channel_name or msg.channel
            title = t("NOTIFY_CHANNEL_TITLE", lang, channel=channel_label, sender=sender)
            severity = "information"
        self.notify(body, title=title, severity=severity, timeout=6)

    def on_input_changed(self, event: Input.Changed) -> None:
        self.completions = self.repl.completer.suggestions(event.value)
        suggestions = self.query_one("#suggestions", OptionList)
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
            return
        if event.option_list.id == "sidebar-nodes":
            self._open_sidebar_node(event.option_index)

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
            elif self.focused.id == "sidebar-nodes" and highlighted is not None:
                self._open_sidebar_node(highlighted)
            else:
                return
            event.stop()
            event.prevent_default()
            return
        if event.key == "down" and self.completions and isinstance(self.focused, Input):
            self.query_one("#suggestions", OptionList).focus()
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
        self.close_node_detail()

    def clear_suggestions(self) -> None:
        self.completions = []
        suggestions = self.query_one("#suggestions", OptionList)
        suggestions.clear_options()
        suggestions.display = False

    def _open_sidebar_node(self, index: int) -> None:
        node_ids = self._sidebar_node_ids
        if index >= len(node_ids):
            return
        self.show_node_detail(node_ids[index])

    def show_node_detail(self, node_id: str) -> None:
        """Render the selected node as a single persistent detail card, replacing any previous one."""
        node = self.repl.client.store.get_node(node_id)
        if node is None:
            return
        local_node = self.repl.client.get_local_node()
        distance_km = None
        bearing_deg = None
        if local_node and local_node.id != node.id:
            distance_km = self.repl.client.store.calculate_distance(local_node.id, node.id)
            bearing_deg = self.repl.client.store.calculate_bearing(local_node.id, node.id)
        panel = render_node_detail(
            node,
            distance_km=distance_km,
            lang=self.repl.settings.language,
            bearing_deg=bearing_deg,
        )
        detail = self.query_one("#node-detail", Static)
        detail.update(panel)
        detail.display = True

    def close_node_detail(self) -> None:
        self.query_one("#node-detail", Static).display = False


class MeshDeckREPL:
    """Compatibility facade which launches the primary Textual application."""

    def __init__(
        self,
        radio_client: RadioClient,
        console: Console | None = None,
        dispatcher: CommandDispatcher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.client = radio_client
        self.console = console or Console()
        # One shared Settings instance for REPL, app and dispatcher: two
        # independent Settings.load() calls would silently diverge on save.
        self.settings = settings if settings is not None else Settings.load()
        set_theme(self.settings.theme)
        self._link_was_lost = False
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            from mesh_deck.commands.dispatcher import CommandDispatcher
            self.dispatcher = CommandDispatcher(self.client, console=self.console, settings=self.settings)
        self.completer = MeshDeckCompleter(
            self._get_all_nodes,
            self._get_available_ports,
            commands=command_descriptions(self.settings.language),
            lang=self.settings.language,
        )
        self.client.on_message_received(self._handle_incoming_message)
        self.client.on_node_updated(self._handle_node_updated)
        self.client.on_connection_change(self._handle_connection_change)
        self.client.on_reconnect_attempt(self._handle_reconnect_attempt)

    def _handle_node_updated(self, _node: NodeData) -> None:
        """Ask the console to repaint the node sidebar (called from a radio thread)."""
        requester = getattr(self.console, "request_sidebar_refresh", None)
        if callable(requester):
            requester()

    def _handle_connection_change(self, connected: bool, port: str | None) -> None:
        """Report link state changes in the log (called from a radio thread)."""
        lang = self.settings.language
        if connected:
            # Only announce a restore if we actually reported a loss first,
            # otherwise the initial handshake would print a bogus notice.
            if not self._link_was_lost:
                return
            self._link_was_lost = False
            self.console.print(
                f"[{THEME_COLORS['secondary']}]{t('CONN_RESTORED', lang, port=port or '?')}[/]"
            )
        else:
            self._link_was_lost = True
            self.console.print(
                f"[{THEME_COLORS['alert']}]{t('CONN_LOST', lang, port=port or '?')}[/]"
            )
        requester = getattr(self.console, "request_sidebar_refresh", None)
        if callable(requester):
            requester()

    def _handle_reconnect_attempt(self, port: str, attempt: int) -> None:
        """Report an automatic reconnection attempt (called from a radio thread)."""
        self.console.print(
            f"[{THEME_COLORS['warning']}]"
            f"{t('CONN_RETRYING', self.settings.language, port=port, attempt=attempt)}[/]"
        )

    def _get_all_nodes(self) -> list:
        return self.client.store.get_all_nodes()

    def _get_available_ports(self) -> list[str]:
        from mesh_deck.core.scanner import scan_meshtastic_ports
        return [port.port for port in scan_meshtastic_ports()]

    def _handle_incoming_message(self, msg: MeshMessage) -> None:
        self.console.print(render_message(msg, lang=self.settings.language))
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
