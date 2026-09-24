"""Interactive full-screen Textual table with mouse-click column sorting.

Allows sorting by clicking on any table header (SNR, Name, Hops, Battery, Distance, etc.).
Press 'q' or 'Escape' to return seamlessly to the REPL.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

from mesh_deck.i18n import t
from mesh_deck.ui.node_presentation import present_node
from mesh_deck.ui.tables import render_node_detail
from mesh_deck.ui.theme import ThemedApp

if TYPE_CHECKING:
    from mesh_deck.core.events import NodeData
    from mesh_deck.core.history import HistoryStore
    from mesh_deck.core.node_store import NodeStore


def _clean_text(markup_or_str: str) -> str:
    """Strip Rich markup tags for clean Textual cell display."""
    return re.sub(r"\[/?.*?\]", "", str(markup_or_str)).strip()


FULL_COLUMNS = (
    ("#", "idx"),
    ("COL_NODE_NAME", "name"),
    ("COL_AKA", "aka"),
    ("COL_ID", "id"),
    ("COL_HARDWARE", "hardware"),
    ("COL_ROLE", "role"),
    ("COL_SNR", "snr"),
    ("COL_HOPS", "hops"),
    ("COL_BATTERY", "battery"),
    ("COL_DISTANCE", "distance"),
    ("COL_LAST_HEARD", "last_heard"),
)
COMPACT_COLUMNS = (
    ("COL_NODE_NAME", "name"),
    ("COL_ROLE", "role"),
    ("COL_SNR", "snr"),
    ("COL_HOPS", "hops"),
    ("COL_BATTERY", "battery"),
    ("COL_LAST_HEARD", "last_heard"),
)
EXPLORER_COMPACT_BREAKPOINT = 120
EXPLORER_VIEW_MODES = ("auto", "full", "compact")


class NodeDetailScreen(Screen[None]):
    """Compact-screen node dossier, reusing the shared Rich detail renderer."""

    BINDINGS = [
        Binding("escape", "close", "Back", show=True),
        Binding("q", "close", "Close", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #compact-node-detail { height: 1fr; margin: 1; }
    """

    def __init__(
        self,
        node: NodeData,
        node_store: NodeStore,
        local_node: NodeData | None,
        lang: str,
        history: HistoryStore | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.node = node
        self.store = node_store
        self.local_node = local_node
        self.lang = lang
        self.history = history
        self.title = t("VIEW_NODE_DETAIL_TITLE", lang, name=node.display_name)
        self._bindings.key_to_bindings["escape"] = [
            Binding("escape", "close", t("BINDING_BACK", lang), show=True)
        ]
        self._bindings.key_to_bindings["q"] = [
            Binding("q", "close", t("BINDING_CLOSE", lang), show=True)
        ]
        self._bindings.key_to_bindings["h"] = [
            Binding("h", "open_history", t("BINDING_HISTORY", lang), show=history is not None)
        ]

    def compose(self) -> ComposeResult:
        distance_km = None
        bearing_deg = None
        if self.local_node and self.local_node.id != self.node.id:
            distance_km = self.store.calculate_distance(self.local_node.id, self.node.id)
            bearing_deg = self.store.calculate_bearing(self.local_node.id, self.node.id)
        yield Static(
            render_node_detail(
                self.node,
                distance_km=distance_km,
                bearing_deg=bearing_deg,
                lang=self.lang,
            ),
            id="compact-node-detail",
        )
        yield Footer()

    def action_close(self) -> None:
        self.dismiss()

    def action_open_history(self) -> None:
        if self.history is None:
            self.notify(t("HISTORY_DISABLED", self.lang), severity="warning")
            return
        from mesh_deck.ui.node_history import NodeHistoryScreen

        self.app.push_screen(NodeHistoryScreen(self.node, self.history, lang=self.lang))


class InteractiveNodesScreen(Screen):
    """Interactive table screen with mouse click column sorting."""

    BINDINGS = [
        Binding("q", "close", "Chiudi / Esci", show=True),
        Binding("escape", "close", "Torna al prompt", show=True),
        Binding("r", "refresh_nodes", "Aggiorna", show=True),
        Binding("slash", "focus_filter", "Cerca / Filtra", show=True),
        Binding("v", "cycle_view_mode", "View", show=True),
        Binding("h", "open_history", "History", show=True),
    ]

    CSS = """
    Screen {
        background: $mesh-bg;
        color: $mesh-text;
    }

    #filter-bar {
        height: 3;
        margin: 1 1 0 1;
        background: $mesh-bg-elevated;
        border: round $mesh-primary;
        padding: 0 1;
    }

    #filter-label {
        width: 12;
        color: $mesh-primary;
        text-style: bold;
        padding-top: 1;
    }

    #filter-input {
        width: 1fr;
        background: $mesh-bg-panel;
        color: $mesh-secondary;
        border: none;
    }

    #view-mode {
        width: 17;
        color: $mesh-secondary;
        text-align: right;
        padding-top: 1;
    }

    #explorer-body {
        height: 1fr;
        margin: 1;
    }

    #table-container {
        height: 1fr;
        width: 3fr;
    }

    DataTable {
        background: $mesh-bg;
        border: round $mesh-primary;
        color: $mesh-text;
    }

    DataTable > .datatable--header {
        background: $mesh-bg-elevated;
        color: $mesh-primary;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $mesh-border-soft;
        color: $mesh-text;
        text-style: bold;
    }

    Footer {
        background: $mesh-bg-panel;
        color: $mesh-muted;
    }

    Input:focus, DataTable:focus {
        border: double $mesh-primary;
    }

    #detail-container {
        display: none;
        width: 2fr;
        margin-left: 1;
        padding: 1;
        border: round $mesh-purple;
        background: $mesh-bg-panel;
    }

    #detail-heading {
        height: auto;
        color: $mesh-primary;
        text-style: bold;
    }

    #node-detail {
        height: 1fr;
    }

    #detail-hint {
        height: auto;
        color: $mesh-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        node_store: NodeStore,
        local_node: NodeData | None = None,
        lang: str = "it",
        view_mode: str = "full",
        history: HistoryStore | None = None,
        on_view_mode_change: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node
        self.lang = lang
        self.sort_column_idx = 0
        self.sort_reverse = False
        self.view_mode = view_mode if view_mode in EXPLORER_VIEW_MODES else "auto"
        self._on_view_mode_change = on_view_mode_change
        self.history = history
        self._effective_compact: bool | None = None
        self._selected_node_id: str | None = None
        self.column_keys: list[str] = []
        self._raw_rows: list[list[Any]] = []
        self._row_node_ids: list[str] = []
        self.title = t("VIEW_TITLE", self.lang)
        self.sub_title = t("VIEW_SUBTITLE", self.lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", self.lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", self.lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_nodes", t("BINDING_REFRESH", self.lang), show=True)]
        self._bindings.key_to_bindings["slash"] = [
            Binding("slash", "focus_filter", t("BINDING_FILTER", self.lang), show=True)
        ]
        self._bindings.key_to_bindings["v"] = [
            Binding("v", "cycle_view_mode", t("BINDING_VIEW_MODE", self.lang), show=True)
        ]
        self._bindings.key_to_bindings["h"] = [
            Binding("h", "open_history", t("BINDING_HISTORY", self.lang), show=history is not None)
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="filter-bar"):
            yield Label(t("FILTER_LABEL", self.lang), id="filter-label")
            yield Input(placeholder=t("FILTER_PLACEHOLDER", self.lang), id="filter-input")
            yield Static(id="view-mode")
        with Horizontal(id="explorer-body"):
            with Vertical(id="table-container"):
                yield DataTable(id="nodes-table", cursor_type="row")
            with Vertical(id="detail-container"):
                yield Static(id="detail-heading")
                yield Static(id="node-detail")
                yield Static(id="detail-hint")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize table columns and populate initial node rows."""
        self._configure_layout(force=True)

    def on_resize(self) -> None:
        self._configure_layout()

    @property
    def is_compact(self) -> bool:
        if self.view_mode == "compact":
            return True
        if self.view_mode == "full":
            return False
        return self.size.width < EXPLORER_COMPACT_BREAKPOINT

    def _configure_layout(self, *, force: bool = False) -> None:
        compact = self.is_compact
        if not force and compact == self._effective_compact:
            return

        self._effective_compact = compact
        detail = self.query_one("#detail-container", Vertical)
        detail.display = not compact
        self._configure_columns(compact)
        self._update_view_mode_label()
        self.refresh_table()
        if self._selected_node_id and not compact:
            self._render_detail(self._selected_node_id)

    def _configure_columns(self, compact: bool) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        self.column_keys = []
        for title_key, key in (COMPACT_COLUMNS if compact else FULL_COLUMNS):
            title = title_key if title_key == "#" else t(title_key, self.lang)
            table.add_column(title, key=key)
            self.column_keys.append(key)

    def _update_view_mode_label(self) -> None:
        mode_key = {
            "auto": "VIEW_MODE_AUTO",
            "full": "VIEW_MODE_FULL",
            "compact": "VIEW_MODE_COMPACT",
        }[self.view_mode]
        effective_key = "VIEW_MODE_COMPACT" if self.is_compact else "VIEW_MODE_FULL"
        self.query_one("#view-mode", Static).update(
            t("VIEW_MODE_LABEL", self.lang, mode=t(mode_key, self.lang), effective=t(effective_key, self.lang))
        )

    def refresh_table(self, filter_text: str = "") -> None:
        """Populate or update table rows."""
        table = self.query_one(DataTable)
        table.clear()

        nodes = self.store.get_all_nodes(sort_by="last_heard")
        filter_lower = filter_text.strip().lower()

        self._raw_rows = []
        self._row_node_ids = []
        for i, node in enumerate(nodes, start=1):
            name_display = node.display_name
            is_local = self.local_node and node.id == self.local_node.id
            if is_local:
                name_display = f"★ {name_display} ({t('LOCAL_SUFFIX', self.lang)})"

            dist_km = None
            if self.local_node and node.id != self.local_node.id:
                dist_km = self.store.calculate_distance(self.local_node.id, node.id)
            display = present_node(node, lang=self.lang, distance_km=dist_km)

            # Filter check
            if filter_lower:
                search_haystack = f"{name_display} {display.aka} {display.node_id} {display.hardware} {display.role}".lower()
                if filter_lower not in search_haystack:
                    continue

            full_values = {
                "idx": i,
                "name": name_display,
                "aka": display.aka,
                "id": display.node_id,
                "hardware": display.hardware,
                "role": display.role,
                "snr": display.snr_text,
                "hops": display.hops_text,
                "battery": display.battery_text,
                "distance": display.distance_text,
                "last_heard": display.last_heard_text,
            }
            row_data = [full_values[key] for key in self.column_keys]
            self._raw_rows.append(row_data)
            self._row_node_ids.append(node.id)
            table.add_row(*row_data, key=node.id)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle mouse click on any column header to sort the table."""
        col_idx = event.column_index
        if self.sort_column_idx == col_idx:
            # Toggle direction
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column_idx = col_idx
            self.sort_reverse = False

        self._sort_and_repopulate(col_idx, self.sort_reverse)

    def _sort_and_repopulate(self, col_idx: int, reverse: bool) -> None:
        """Sort rows by column index and repopulate table."""
        table = self.query_one(DataTable)

        def _parse_cell(val: Any) -> float | str | None:
            """Return a comparable value, or None when the cell has no data."""
            if isinstance(val, (int, float)):
                return float(val)
            val_str = str(val).strip()
            if not val_str or val_str == "--":
                return None

            # SNR, e.g. "+8.5 dB"
            snr = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*dB", val_str)
            if snr:
                return float(snr.group(1))

            # Hops, e.g. "Diretto (0)" / "Direct (0)" or "3 hops"
            if val_str.endswith("(0)"):
                return 0.0
            hops = re.fullmatch(r"(\d+)\s*hops?", val_str)
            if hops:
                return float(hops.group(1))

            # Distance, e.g. "1.4 km" or "820 m" (normalized to meters)
            dist = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(km|m)", val_str)
            if dist:
                return float(dist.group(1)) * (1000.0 if dist.group(2) == "km" else 1.0)

            return val_str.lower()

        def _sort_key(item: tuple[str, list[Any]]) -> tuple[int, float, str]:
            # Uniform (missing, number, text) shape: a column mixing numbers and
            # "--" placeholders must never compare float against str.
            parsed = _parse_cell(item[1][col_idx])
            if parsed is None:
                return (1, 0.0, "")
            if isinstance(parsed, float):
                return (0, parsed, "")
            return (0, 0.0, parsed)

        ordered_rows = list(zip(self._row_node_ids, self._raw_rows, strict=True))
        ordered_rows.sort(key=_sort_key, reverse=reverse)
        self._row_node_ids = [node_id for node_id, _row in ordered_rows]
        self._raw_rows = [row for _node_id, row in ordered_rows]

        # Clear and repopulate
        table.clear()
        for node_id, row in zip(self._row_node_ids, self._raw_rows, strict=True):
            table.add_row(*row, key=node_id)

        arrow = "▼" if reverse else "▲"
        col_name = table.columns[_column_key(table, col_idx)].label
        clean_name = re.sub(r"[▲▼]", "", str(col_name)).strip()
        self.sub_title = t("VIEW_SORTED_BY", self.lang, column=clean_name, arrow=arrow)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live search filter as user types."""
        self.refresh_table(filter_text=event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_node(str(event.row_key.value))

    def action_refresh_nodes(self) -> None:
        """Action for 'r' key."""
        inp = self.query_one(Input)
        self.refresh_table(filter_text=inp.value)

    def action_focus_filter(self) -> None:
        """Action for '/' key."""
        self.query_one(Input).focus()

    def action_cycle_view_mode(self) -> None:
        index = EXPLORER_VIEW_MODES.index(self.view_mode)
        self.view_mode = EXPLORER_VIEW_MODES[(index + 1) % len(EXPLORER_VIEW_MODES)]
        if self._on_view_mode_change is not None:
            self._on_view_mode_change(self.view_mode)
        self._configure_layout(force=True)

    def _open_node(self, node_id: str) -> None:
        node = self.store.get_node(node_id)
        if node is None:
            return
        self._selected_node_id = node_id
        if self.is_compact:
            self.app.push_screen(
                NodeDetailScreen(node, self.store, self.local_node, self.lang, self.history)
            )
            return
        self._render_detail(node_id)

    def action_open_history(self) -> None:
        if self._selected_node_id is None:
            return
        node = self.store.get_node(self._selected_node_id)
        if node is None:
            return
        if self.history is None:
            self.notify(t("HISTORY_DISABLED", self.lang), severity="warning")
            return
        from mesh_deck.ui.node_history import NodeHistoryScreen

        self.app.push_screen(NodeHistoryScreen(node, self.history, lang=self.lang))

    def _render_detail(self, node_id: str) -> None:
        node = self.store.get_node(node_id)
        if node is None:
            return
        distance_km = None
        bearing_deg = None
        if self.local_node and self.local_node.id != node.id:
            distance_km = self.store.calculate_distance(self.local_node.id, node.id)
            bearing_deg = self.store.calculate_bearing(self.local_node.id, node.id)
        self.query_one("#detail-heading", Static).update(
            t("VIEW_NODE_DETAIL_TITLE", self.lang, name=node.display_name)
        )
        self.query_one("#node-detail", Static).update(
            render_node_detail(
                node,
                distance_km=distance_km,
                bearing_deg=bearing_deg,
                lang=self.lang,
            )
        )
        self.query_one("#detail-hint", Static).update(t("VIEW_DETAIL_HINT", self.lang))

    def update_language(self, lang: str) -> None:
        """Refresh all mounted explorer strings without losing selection or mode."""
        self.lang = lang
        self.title = t("VIEW_TITLE", lang)
        self.sub_title = t("VIEW_SUBTITLE", lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_nodes", t("BINDING_REFRESH", lang), show=True)]
        self._bindings.key_to_bindings["slash"] = [Binding("slash", "focus_filter", t("BINDING_FILTER", lang), show=True)]
        self._bindings.key_to_bindings["v"] = [Binding("v", "cycle_view_mode", t("BINDING_VIEW_MODE", lang), show=True)]
        self._bindings.key_to_bindings["h"] = [
            Binding("h", "open_history", t("BINDING_HISTORY", lang), show=self.history is not None)
        ]
        self.query_one("#filter-label", Label).update(t("FILTER_LABEL", lang))
        self.query_one("#filter-input", Input).placeholder = t("FILTER_PLACEHOLDER", lang)
        self._configure_layout(force=True)

    def action_close(self) -> None:
        """Return to the containing application."""
        self.dismiss()


def _column_key(table: DataTable, col_idx: int) -> Any:
    """Return the column key at a positional index, or the index as fallback."""
    keys = list(table.columns.keys())
    return keys[col_idx] if 0 <= col_idx < len(keys) else col_idx


class InteractiveNodesApp(ThemedApp, App):
    """Standalone wrapper for launching the reusable node explorer screen."""

    def __init__(
        self,
        node_store: NodeStore,
        local_node: NodeData | None = None,
        lang: str = "it",
        view_mode: str = "full",
        history: HistoryStore | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node
        self.lang = lang
        self.view_mode = view_mode
        self.history = history

    def on_mount(self) -> None:
        self.push_screen(
            InteractiveNodesScreen(
                self.store,
                local_node=self.local_node,
                lang=self.lang,
                view_mode=self.view_mode,
                history=self.history,
            ),
            callback=lambda _: self.exit(),
        )


def launch_interactive_nodes(
    node_store: NodeStore,
    local_node: NodeData | None = None,
    lang: str = "it",
    view_mode: str = "full",
    history: HistoryStore | None = None,
) -> None:
    """Run the interactive table viewer as a standalone application."""
    InteractiveNodesApp(
        node_store=node_store,
        local_node=local_node,
        lang=lang,
        view_mode=view_mode,
        history=history,
    ).run()
