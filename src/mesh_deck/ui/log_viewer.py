"""Interactive viewer for bounded Mesh-Deck application and device logs."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Select, Static

from mesh_deck.core.log_buffer import LogBuffer, LogEntry
from mesh_deck.core.settings import CONFIG_DIR
from mesh_deck.i18n import t

LOG_EXPORT_DIR = CONFIG_DIR / "exports"
LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class LogViewerScreen(Screen[None]):
    """Searchable, bounded diagnostic log viewer that never writes to stdout."""

    BINDINGS = [
        Binding("q", "close", "Close", show=True),
        Binding("escape", "close", "Back", show=True),
        Binding("r", "refresh_entries", "Refresh", show=True),
        Binding("p", "toggle_pause", "Pause", show=True),
        Binding("c", "copy_selected", "Copy", show=True),
        Binding("e", "export_entries", "Export", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #log-controls { height: 3; margin: 1 1 0 1; padding: 0 1; border: round $mesh-primary; background: $mesh-bg-elevated; }
    #log-source { width: 18; }
    #log-level { width: 18; margin-left: 1; }
    #log-query { width: 1fr; margin-left: 1; background: $mesh-bg-panel; color: $mesh-text; border: none; }
    #log-status { height: 1; margin: 0 1; color: $mesh-muted; }
    #log-table { height: 1fr; margin: 0 1 1 1; border: round $mesh-border-soft; background: $mesh-bg-panel; }
    DataTable > .datatable--header { background: $mesh-bg-elevated; color: $mesh-primary; text-style: bold; }
    DataTable > .datatable--cursor { background: $mesh-border-soft; color: $mesh-text; text-style: bold; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
    """

    def __init__(self, buffer: LogBuffer, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.buffer = buffer
        self.lang = lang
        self.paused = False
        self._pending_entries = 0
        self._refresh_pending = False
        self._visible_entries: dict[str, LogEntry] = {}
        self.title = t("LOGS_TITLE", lang)
        self.sub_title = t("LOGS_SUBTITLE", lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_entries", t("BINDING_REFRESH", lang), show=True)]
        self._bindings.key_to_bindings["p"] = [Binding("p", "toggle_pause", t("BINDING_LOG_PAUSE", lang), show=True)]
        self._bindings.key_to_bindings["c"] = [Binding("c", "copy_selected", t("BINDING_LOG_COPY", lang), show=True)]
        self._bindings.key_to_bindings["e"] = [Binding("e", "export_entries", t("BINDING_LOG_EXPORT", lang), show=True)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="log-controls"):
            yield Label(t("LOGS_SOURCE_LABEL", self.lang))
            yield Select(
                [(t("LOGS_SOURCE_ALL", self.lang), "all"), (t("LOGS_SOURCE_APP", self.lang), "app"), (t("LOGS_SOURCE_DEVICE", self.lang), "device")],
                value="all",
                id="log-source",
            )
            yield Label(t("LOGS_LEVEL_LABEL", self.lang))
            yield Select(
                [(t("LOGS_LEVEL_DEBUG", self.lang), "debug"), (t("LOGS_LEVEL_INFO", self.lang), "info"), (t("LOGS_LEVEL_WARNING", self.lang), "warning"), (t("LOGS_LEVEL_ERROR", self.lang), "error")],
                value="warning",
                id="log-level",
            )
            yield Input(placeholder=t("LOGS_QUERY_PLACEHOLDER", self.lang), id="log-query")
        yield Static(id="log-status")
        yield DataTable(id="log-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.add_columns(
            (t("LOGS_COL_TIME", self.lang), "time"),
            (t("LOGS_COL_SOURCE", self.lang), "source"),
            (t("LOGS_COL_LEVEL", self.lang), "level"),
            (t("LOGS_COL_MESSAGE", self.lang), "message"),
        )
        self.buffer.add_listener(self._on_entry)
        self.refresh_entries()

    def on_unmount(self) -> None:
        self.buffer.remove_listener(self._on_entry)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("log-source", "log-level"):
            self.refresh_entries()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "log-query":
            self.refresh_entries()

    def _on_entry(self, _entry: LogEntry) -> None:
        """Coalesce background log arrivals onto the Textual UI event loop."""
        if threading.get_ident() == getattr(self.app, "ui_thread_id", None):
            self.request_refresh()
            return
        try:
            self.app.call_from_thread(self.request_refresh)
        except RuntimeError:
            pass

    def request_refresh(self) -> None:
        if self.paused:
            self._pending_entries += 1
            self._render_status()
            return
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self.set_timer(0.15, self._flush_refresh)

    def _flush_refresh(self) -> None:
        self._refresh_pending = False
        self.refresh_entries()

    def _filters(self) -> tuple[str, int, str]:
        source = str(self.query_one("#log-source", Select).value)
        level = str(self.query_one("#log-level", Select).value)
        query = self.query_one("#log-query", Input).value
        return source, LEVELS[level], query

    def refresh_entries(self) -> None:
        source, minimum_level, query = self._filters()
        entries = self.buffer.entries(source=source, minimum_level=minimum_level, query=query)
        table = self.query_one("#log-table", DataTable)
        table.clear()
        self._visible_entries = {}
        for entry in entries:
            key = str(entry.sequence)
            message = entry.message.replace("\n", " ").strip()
            table.add_row(
                entry.timestamp.strftime("%H:%M:%S"),
                entry.source.upper() if entry.port is None else f"DEVICE {entry.port}",
                entry.level_name,
                message,
                key=key,
            )
            self._visible_entries[key] = entry
        self._pending_entries = 0
        self._render_status(len(entries))

    def _render_status(self, count: int | None = None) -> None:
        if count is None:
            count = len(self._visible_entries)
        if self.paused:
            status = t("LOGS_STATUS_PAUSED", self.lang, count=count, pending=self._pending_entries)
        else:
            status = t("LOGS_STATUS_LIVE", self.lang, count=count)
        self.query_one("#log-status", Static).update(status)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self._visible_entries.get(str(event.row_key.value))
        if entry is not None:
            self.app.copy_to_clipboard(entry.to_line())
            self.notify(t("LOGS_COPIED", self.lang), severity="information")

    def action_refresh_entries(self) -> None:
        self.refresh_entries()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            self._render_status()
        else:
            self.refresh_entries()

    def action_copy_selected(self) -> None:
        table = self.query_one("#log-table", DataTable)
        if table.cursor_row is None:
            self.notify(t("LOGS_NOTHING_SELECTED", self.lang), severity="warning")
            return
        rows = list(table.rows.keys())
        if table.cursor_row >= len(rows):
            return
        entry = self._visible_entries.get(str(rows[table.cursor_row].value))
        if entry is None:
            return
        self.app.copy_to_clipboard(entry.to_line())
        self.notify(t("LOGS_COPIED", self.lang), severity="information")

    def action_export_entries(self) -> None:
        try:
            LOG_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            export_path = LOG_EXPORT_DIR / f"mesh-deck-{datetime.now():%Y%m%d-%H%M%S}.log"
            export_path.write_text(
                "\n".join(entry.to_line() for entry in self._visible_entries.values()) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self.notify(t("LOGS_EXPORT_FAILED", self.lang, error=exc), severity="error")
            return
        self.notify(t("LOGS_EXPORTED", self.lang, path=export_path), severity="information")

    def action_close(self) -> None:
        self.dismiss()
