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
from mesh_deck.i18n import t
from mesh_deck.ui.tables import render_message
from mesh_deck.ui.theme import THEME_COLORS, ThemedApp

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient

DM_KEY = "dm:"


class ChannelChatScreen(Screen):
    """Interactive chat viewer: click a channel to see its message history live."""

    BINDINGS = [
        Binding("q", "close", "Chiudi", show=True),
        Binding("escape", "close", "Torna al prompt", show=True),
        Binding("r", "refresh_channels", "Aggiorna canali", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #chat-body { height: 1fr; margin: 1; }
    #channel-list { width: 30; border: round $mesh-border-soft; background: $mesh-bg-elevated; }
    #chat-panel { border: round $mesh-primary; background: $mesh-bg-panel; }
    #chat-log { height: 1fr; padding: 0 1; }
    #chat-input { margin: 0 1 1 1; border: round $mesh-primary; }
    #chat-hint { color: $mesh-muted; padding: 0 1; height: 1; }
    """

    def __init__(self, radio_client: RadioClient, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = radio_client
        self.lang = lang
        self._entries: list[tuple[int | str | None, str]] = []
        self._selected_key: int | str = 0
        self._buffers: dict[int | str, list[MeshMessage]] = {}
        self._unread: dict[int | str, int] = {}
        self._dm_names: dict[str, str] = {}
        self.title = t("CHAT_TITLE", self.lang)
        self.sub_title = t("CHAT_SUBTITLE", self.lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", self.lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", self.lang), show=True)]
        self._bindings.key_to_bindings["r"] = [
            Binding("r", "refresh_channels", t("BINDING_UPDATE_CHANNELS", self.lang), show=True)
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="chat-body"):
            yield OptionList(id="channel-list")
            with Vertical(id="chat-panel"):
                yield RichLog(id="chat-log", markup=True, wrap=True, highlight=True)
                yield Static("", id="chat-hint")
                yield Input(placeholder=t("CHAT_INPUT_PLACEHOLDER", self.lang), id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        self.client.on_message_received(self._handle_radio_message)
        self._preload_history()
        self._refresh_channel_list()
        self._render_selected()

    def on_unmount(self) -> None:
        self.client.off_message_received(self._handle_radio_message)

    # -- data -----------------------------------------------------------

    def _channel_entries(self) -> list[tuple[int | str | None, str]]:
        entries: list[tuple[int | str | None, str]] = []
        for ch in self.client.get_channels():
            idx = ch.get("index", 0)
            name = ch.get("name") or ("Primary" if idx == 0 else t("CHAT_CHANNEL_FALLBACK", self.lang, index=idx))
            entries.append((idx, str(name)))
        if not entries:
            entries.append((0, "Primary"))
        dm_keys = [key for key in self._buffers if self._is_dm_key(key)]
        if dm_keys:
            entries.append((None, t("CHAT_DM_SECTION", self.lang)))
            dm_keys.sort(
                key=lambda key: self._buffers[key][-1].timestamp if self._buffers[key] else datetime.min,
                reverse=True,
            )
            for key in dm_keys:
                entries.append((key, self._dm_names.get(key, self._dm_peer_id_from_key(key))))
        return entries

    @staticmethod
    def _is_dm_key(key: int | str) -> bool:
        return isinstance(key, str) and key.startswith(DM_KEY)

    @staticmethod
    def _dm_peer_id_from_key(key: int | str) -> str:
        return str(key).removeprefix(DM_KEY)

    def _dm_key_for(self, msg: MeshMessage) -> str:
        local = self.client.get_local_node()
        local_id = getattr(local, "id", None)
        peer_id = msg.receiver_id if local_id and msg.sender_id == local_id else msg.sender_id
        return f"{DM_KEY}{peer_id}"

    def _record_dm_name(self, key: str, msg: MeshMessage) -> None:
        peer_id = self._dm_peer_id_from_key(key)
        local = self.client.get_local_node()
        local_id = getattr(local, "id", None)
        name = msg.recipient_name if local_id and msg.sender_id == local_id else msg.sender_name
        if not name:
            node = self.client.store.get_node(peer_id)
            name = node.display_name if node else peer_id
        self._dm_names[key] = name

    def _preload_history(self) -> None:
        history = getattr(self.client, "history", None)
        if history is None:
            return
        for entry in history.iter_messages(limit=500):
            try:
                msg = MeshMessage.from_dict(entry)
            except Exception:
                continue
            key = self._dm_key_for(msg) if msg.is_dm else msg.channel
            if msg.is_dm:
                self._record_dm_name(key, msg)
            self._buffers.setdefault(key, []).append(msg)

    def _refresh_channel_list(self) -> None:
        self._entries = self._channel_entries()
        option_list = self.query_one("#channel-list", OptionList)
        option_list.clear_options()
        for key, name in self._entries:
            if key is None:
                option_list.add_option(Option(f"[dim]{name}[/]", disabled=True))
                continue
            unread = self._unread.get(key, 0)
            badge = f" [bold {THEME_COLORS['alert']}]({unread})[/]" if unread else ""
            prefix = "🔒 " if self._is_dm_key(key) else "# "
            option_list.add_option(Option(f"{prefix}{name}{badge}"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "channel-list":
            return
        idx = event.option_index
        if idx >= len(self._entries):
            return
        key, _name = self._entries[idx]
        if key is None:
            return
        self._selected_key = key
        self._unread[key] = 0
        self._refresh_channel_list()
        self._render_selected()

    def _render_selected(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        for msg in self._buffers.get(self._selected_key, []):
            log.write(render_message(msg, lang=self.lang))
        hint = self.query_one("#chat-hint", Static)
        input_box = self.query_one("#chat-input", Input)
        if self._is_dm_key(self._selected_key):
            peer_id = self._dm_peer_id_from_key(self._selected_key)
            name = self._dm_names.get(self._selected_key, peer_id)
            hint.update(t("CHAT_DM_HINT", self.lang, name=name, peer_id=peer_id))
            input_box.placeholder = t("CHAT_DM_REPLY_PLACEHOLDER", self.lang, name=name)
            input_box.disabled = False
            self.sub_title = t("CHAT_DM_SUBTITLE", self.lang, name=name)
        else:
            hint.update("")
            input_box.placeholder = t("CHAT_INPUT_PLACEHOLDER", self.lang)
            input_box.disabled = False
            self.sub_title = t("CHAT_SUBTITLE", self.lang)

    def _handle_radio_message(self, msg: MeshMessage) -> None:
        """Callback registered on RadioClient; invoked from the pubsub background thread."""
        self.app.call_from_thread(self._handle_message, msg)

    def _handle_message(self, msg: MeshMessage) -> None:
        key = self._dm_key_for(msg) if msg.is_dm else msg.channel
        if msg.is_dm:
            self._record_dm_name(key, msg)
        self._buffers.setdefault(key, []).append(msg)
        if key == self._selected_key:
            self.query_one("#chat-log", RichLog).write(render_message(msg, lang=self.lang))
        else:
            self._unread[key] = self._unread.get(key, 0) + 1
            self._refresh_channel_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        try:
            if self._is_dm_key(self._selected_key):
                peer_id = self._dm_peer_id_from_key(self._selected_key)
                peer_name = self._dm_names.get(self._selected_key, peer_id)
                self.client.send_dm(peer_id, text)
                local = self.client.get_local_node()
                self._handle_message(
                    MeshMessage(
                        sender_id=getattr(local, "id", "^local"),
                        sender_name=getattr(local, "display_name", "Local"),
                        receiver_id=peer_id,
                        recipient_name=peer_name,
                        text=text,
                        is_dm=True,
                    )
                )
            else:
                self.client.send_broadcast(text, channel_index=int(self._selected_key))
        except Exception as exc:
            self.app.notify(str(exc), title=t("CHAT_SEND_FAILED_TITLE", self.lang), severity="error")

    def action_close(self) -> None:
        self.dismiss()

    def action_refresh_channels(self) -> None:
        self._refresh_channel_list()


class ChannelChatApp(ThemedApp, App):
    """Standalone wrapper for launching the reusable channel chat screen."""

    def __init__(self, radio_client: RadioClient, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = radio_client
        self.lang = lang

    def on_mount(self) -> None:
        self.push_screen(
            ChannelChatScreen(self.client, lang=self.lang),
            callback=lambda _: self.exit(),
        )


def launch_channel_chat(radio_client: RadioClient, lang: str = "it") -> None:
    """Run the channel chat viewer as a standalone application."""
    ChannelChatApp(radio_client, lang=lang).run()
