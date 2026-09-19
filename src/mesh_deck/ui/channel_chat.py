"""Mouse-usable, full-screen chat viewer for mesh channels and direct messages.

Shows one scrollable message log per channel (plus an aggregated "Direct
Messages" entry), pre-populated from local history when available, and kept
live via RadioClient's message callback. Click a channel in the sidebar to
switch chats; type in the bottom input to send a broadcast on the selected
channel.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option

from mesh_deck.core.events import MeshMessage
from mesh_deck.ui.tables import render_message
from mesh_deck.ui.theme import THEME_COLORS

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient

DM_KEY = "dm"


def _message_from_history_entry(entry: dict[str, Any]) -> MeshMessage:
    """Reconstruct a MeshMessage from a HistoryStore JSONL record."""
    payload = dict(entry)
    payload.pop("direction", None)
    payload.pop("recorded_at", None)
    timestamp = payload.get("timestamp")
    if isinstance(timestamp, str):
        try:
            payload["timestamp"] = datetime.fromisoformat(timestamp)
        except ValueError:
            payload["timestamp"] = None
    return MeshMessage(**payload)


class ChannelChatScreen(Screen):
    """Interactive chat viewer: click a channel to see its message history live."""

    TITLE = "💬 MESH-DECK // CHAT CANALI"
    SUB_TITLE = "Fai click su un canale per aprirlo • Invia dal campo in basso • 'q'/'Esc' per uscire"

    BINDINGS = [
        Binding("q", "close", "Chiudi", show=True),
        Binding("escape", "close", "Torna al prompt", show=True),
        Binding("r", "refresh_channels", "Aggiorna canali", show=True),
    ]

    CSS = """
    Screen { background: #0a0e17; color: #f8fafc; }
    #chat-body { height: 1fr; margin: 1; }
    #channel-list { width: 30; border: round #1f8794; background: #10212b; }
    #chat-panel { border: round #00f3ff; background: #0b1720; }
    #chat-log { height: 1fr; padding: 0 1; }
    #chat-input { margin: 0 1 1 1; border: round #00f3ff; }
    #chat-hint { color: #64748b; padding: 0 1; height: 1; }
    """

    def __init__(self, radio_client: RadioClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = radio_client
        self._entries: list[tuple[int | str, str]] = []
        self._selected_key: int | str = 0
        self._buffers: dict[int | str, list[MeshMessage]] = {}
        self._unread: dict[int | str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="chat-body"):
            yield OptionList(id="channel-list")
            with Vertical(id="chat-panel"):
                yield RichLog(id="chat-log", markup=True, wrap=True, highlight=True)
                yield Static("", id="chat-hint")
                yield Input(placeholder="Scrivi un messaggio e premi invio...", id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        self.client.on_message_received(self._handle_radio_message)
        self._preload_history()
        self._refresh_channel_list()
        self._render_selected()

    def on_unmount(self) -> None:
        self.client.off_message_received(self._handle_radio_message)

    # -- data -----------------------------------------------------------

    def _channel_entries(self) -> list[tuple[int | str, str]]:
        entries: list[tuple[int | str, str]] = []
        for ch in self.client.get_channels():
            idx = ch.get("index", 0)
            name = ch.get("name") or ("Primary" if idx == 0 else f"Canale {idx}")
            entries.append((idx, str(name)))
        if not entries:
            entries.append((0, "Primary"))
        entries.append((DM_KEY, "Messaggi Diretti"))
        return entries

    def _preload_history(self) -> None:
        history = getattr(self.client, "history", None)
        if history is None:
            return
        for entry in history.iter_messages(limit=500):
            try:
                msg = _message_from_history_entry(entry)
            except Exception:
                continue
            key = DM_KEY if msg.is_dm else msg.channel
            self._buffers.setdefault(key, []).append(msg)

    def _refresh_channel_list(self) -> None:
        self._entries = self._channel_entries()
        option_list = self.query_one("#channel-list", OptionList)
        option_list.clear_options()
        for key, name in self._entries:
            unread = self._unread.get(key, 0)
            badge = f" [bold {THEME_COLORS['alert']}]({unread})[/]" if unread else ""
            option_list.add_option(Option(f"{name}{badge}"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "channel-list":
            return
        idx = event.option_index
        if idx >= len(self._entries):
            return
        key, _name = self._entries[idx]
        self._selected_key = key
        self._unread[key] = 0
        self._refresh_channel_list()
        self._render_selected()

    def _render_selected(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        for msg in self._buffers.get(self._selected_key, []):
            log.write(render_message(msg))
        hint = self.query_one("#chat-hint", Static)
        input_box = self.query_one("#chat-input", Input)
        if self._selected_key == DM_KEY:
            hint.update("I DM si inviano con /dm <id|aka> <testo> dal prompt principale.")
            input_box.disabled = True
        else:
            hint.update("")
            input_box.disabled = False

    def _handle_radio_message(self, msg: MeshMessage) -> None:
        """Callback registered on RadioClient; invoked from the pubsub background thread."""
        self.app.call_from_thread(self._handle_message, msg)

    def _handle_message(self, msg: MeshMessage) -> None:
        key = DM_KEY if msg.is_dm else msg.channel
        self._buffers.setdefault(key, []).append(msg)
        if key == self._selected_key:
            self.query_one("#chat-log", RichLog).write(render_message(msg))
        else:
            self._unread[key] = self._unread.get(key, 0) + 1
            self._refresh_channel_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        text = event.value.strip()
        if not text or self._selected_key == DM_KEY:
            return
        event.input.value = ""
        try:
            self.client.send_broadcast(text, channel_index=int(self._selected_key))
        except Exception as exc:
            self.app.notify(str(exc), title="Invio fallito", severity="error")

    def action_close(self) -> None:
        self.dismiss()

    def action_refresh_channels(self) -> None:
        self._refresh_channel_list()


class ChannelChatApp(App):
    """Standalone wrapper for launching the reusable channel chat screen."""

    def __init__(self, radio_client: RadioClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = radio_client

    def on_mount(self) -> None:
        self.push_screen(
            ChannelChatScreen(self.client),
            callback=lambda _: self.exit(),
        )


def launch_channel_chat(radio_client: RadioClient) -> None:
    """Run the channel chat viewer as a standalone application."""
    ChannelChatApp(radio_client).run()
