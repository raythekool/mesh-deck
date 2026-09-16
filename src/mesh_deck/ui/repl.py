"""Primary Textual console for Mesh-Deck."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual import work
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, RichLog, Select
from textual.widgets.option_list import Option

from mesh_deck.core.settings import Settings
from mesh_deck.i18n import command_descriptions, t
from mesh_deck.core.events import MeshMessage
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

    def open_settings(self) -> None:
        self._invoke(self.app.open_settings)

    def update_language(self, language: str) -> None:
        self._invoke(self.app.update_language, language)

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
        )
        self.app.update_language(self.settings.language)
        self.dismiss()


class MeshDeckApp(App):
    """Full-screen Textual command console with live radio output."""

    TITLE = "MESH-DECK"
    SUB_TITLE = "Meshtastic command console"
    BINDINGS = [
        Binding("ctrl+c", "clear_input", "Clear input", show=False),
        Binding("tab", "complete", "Complete", show=False),
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

    def __init__(self, repl: MeshDeckREPL, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.repl = repl
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
        self.repl.dispatcher.cmd_banner([])
        self.query_one(OptionList).display = False
        self.query_one(Input).focus()

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

    def open_settings(self) -> None:
        self.push_screen(SettingsScreen(self.repl.settings))

    def update_language(self, language: str) -> None:
        self.repl.settings.language = language
        self.sub_title = t("APP_SUBTITLE", language)
        self.repl.completer.commands = command_descriptions(language)
        self.query_one(Input).placeholder = self.repl._get_prompt()

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
        self._apply_completion(event.index)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value
        event.input.value = ""
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
            if highlighted is not None:
                self._apply_completion(highlighted)
            event.stop()
            event.prevent_default()
            return
        if event.key == "down" and self.completions:
            self.query_one(OptionList).focus()
            event.stop()
            event.prevent_default()
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

    def _get_prompt(self) -> str:
        """Return the contextual label used by the Textual command input."""
        local = self.client.get_local_node()
        name = ""
        if local:
            name = local.short_name or local.long_name or local.id
        return t("COMMAND_PLACEHOLDER", self.settings.language, name=name or "-")

    def run(self) -> None:
        MeshDeckApp(self).run()
