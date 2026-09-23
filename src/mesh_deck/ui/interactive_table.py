"""Interactive full-screen Textual table with mouse-click column sorting.

Allows sorting by clicking on any table header (SNR, Name, Hops, Battery, Distance, etc.).
Press 'q' or 'Escape' to return seamlessly to the REPL.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label

from mesh_deck.i18n import t
from mesh_deck.ui.theme import ThemedApp, format_time_ago

if TYPE_CHECKING:
    from mesh_deck.core.events import NodeData
    from mesh_deck.core.node_store import NodeStore


def _clean_text(markup_or_str: str) -> str:
    """Strip Rich markup tags for clean Textual cell display."""
    return re.sub(r"\[/?.*?\]", "", str(markup_or_str)).strip()


class InteractiveNodesScreen(Screen):
    """Interactive table screen with mouse click column sorting."""

    BINDINGS = [
        Binding("q", "close", "Chiudi / Esci", show=True),
        Binding("escape", "close", "Torna al prompt", show=True),
        Binding("r", "refresh_nodes", "Aggiorna", show=True),
        Binding("slash", "focus_filter", "Cerca / Filtra", show=True),
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

    #table-container {
        height: 1fr;
        margin: 1;
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
    """

    def __init__(
        self,
        node_store: NodeStore,
        local_node: NodeData | None = None,
        lang: str = "it",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node
        self.lang = lang
        self.sort_column_idx = 0
        self.sort_reverse = False
        self.column_keys: list[str] = []
        self._raw_rows: list[list[Any]] = []
        self.title = t("VIEW_TITLE", self.lang)
        self.sub_title = t("VIEW_SUBTITLE", self.lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", self.lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", self.lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_nodes", t("BINDING_REFRESH", self.lang), show=True)]
        self._bindings.key_to_bindings["slash"] = [
            Binding("slash", "focus_filter", t("BINDING_FILTER", self.lang), show=True)
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="filter-bar"):
            yield Label(t("FILTER_LABEL", self.lang), id="filter-label")
            yield Input(placeholder=t("FILTER_PLACEHOLDER", self.lang), id="filter-input")
        with Vertical(id="table-container"):
            yield DataTable(id="nodes-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize table columns and populate initial node rows."""
        table = self.query_one(DataTable)
        columns = [
            ("#", "idx"),
            (t("COL_NODE_NAME", self.lang), "name"),
            (t("COL_AKA", self.lang), "aka"),
            (t("COL_ID", self.lang), "id"),
            (t("COL_HARDWARE", self.lang), "hardware"),
            (t("COL_ROLE", self.lang), "role"),
            (t("COL_SNR", self.lang), "snr"),
            (t("COL_HOPS", self.lang), "hops"),
            (t("COL_BATTERY", self.lang), "battery"),
            (t("COL_DISTANCE", self.lang), "distance"),
            (t("COL_LAST_HEARD", self.lang), "last_heard"),
        ]

        self.column_keys = []
        for title, key in columns:
            table.add_column(title, key=key)
            self.column_keys.append(key)

        self.refresh_table()

    def refresh_table(self, filter_text: str = "") -> None:
        """Populate or update table rows."""
        table = self.query_one(DataTable)
        table.clear()

        nodes = self.store.get_all_nodes(sort_by="last_heard")
        filter_lower = filter_text.strip().lower()

        self._raw_rows = []
        for i, node in enumerate(nodes, start=1):
            name_display = node.display_name
            is_local = self.local_node and node.id == self.local_node.id
            if is_local:
                name_display = f"★ {name_display} ({t('LOCAL_SUFFIX', self.lang)})"

            aka = node.aka
            node_id = node.id
            hw = node.hardware
            role = node.role

            # SNR value
            snr_val = node.snr
            snr_str = f"{snr_val:+.1f} dB" if snr_val is not None else "-- dB"

            # Hops
            hops_val = node.hops_away
            if hops_val is not None:
                hops_str = f"{t('HOPS_DIRECT', self.lang)} (0)" if hops_val == 0 else f"{hops_val} hops"
            else:
                hops_str = "--"

            # Battery
            if node.battery_level is not None:
                if node.battery_level > 100:
                    batt_str = "⚡ USB"
                else:
                    volt = f" ({node.voltage:.2f}V)" if node.voltage else ""
                    batt_str = f"{node.battery_level}%{volt}"
            elif node.voltage is not None:
                batt_str = f"{node.voltage:.2f}V"
            else:
                batt_str = "--"

            # Distance
            dist_km = None
            if self.local_node and node.id != self.local_node.id:
                dist_km = self.store.calculate_distance(self.local_node.id, node.id)
            if dist_km is not None:
                dist_str = f"{int(dist_km * 1000)} m" if dist_km < 1.0 else f"{dist_km:.1f} km"
            else:
                dist_str = "--"

            # Last heard
            last_heard_str = _clean_text(format_time_ago(node.last_heard, self.lang))

            # Filter check
            if filter_lower:
                search_haystack = f"{name_display} {aka} {node_id} {hw} {role}".lower()
                if filter_lower not in search_haystack:
                    continue

            row_data = [
                i,
                name_display,
                aka,
                node_id,
                hw,
                role,
                snr_str,
                hops_str,
                batt_str,
                dist_str,
                last_heard_str,
            ]
            self._raw_rows.append(row_data)
            table.add_row(*row_data)

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

        def _sort_key(row: list[Any]) -> tuple[int, float, str]:
            # Uniform (missing, number, text) shape: a column mixing numbers and
            # "--" placeholders must never compare float against str.
            parsed = _parse_cell(row[col_idx])
            if parsed is None:
                return (1, 0.0, "")
            if isinstance(parsed, float):
                return (0, parsed, "")
            return (0, 0.0, parsed)

        self._raw_rows.sort(key=_sort_key, reverse=reverse)

        # Clear and repopulate
        table.clear()
        for row in self._raw_rows:
            table.add_row(*row)

        arrow = "▼" if reverse else "▲"
        col_name = table.columns[_column_key(table, col_idx)].label
        clean_name = re.sub(r"[▲▼]", "", str(col_name)).strip()
        self.sub_title = t("VIEW_SORTED_BY", self.lang, column=clean_name, arrow=arrow)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live search filter as user types."""
        self.refresh_table(filter_text=event.value)

    def action_refresh_nodes(self) -> None:
        """Action for 'r' key."""
        inp = self.query_one(Input)
        self.refresh_table(filter_text=inp.value)

    def action_focus_filter(self) -> None:
        """Action for '/' key."""
        self.query_one(Input).focus()

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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node
        self.lang = lang

    def on_mount(self) -> None:
        self.push_screen(
            InteractiveNodesScreen(self.store, local_node=self.local_node, lang=self.lang),
            callback=lambda _: self.exit(),
        )


def launch_interactive_nodes(node_store: NodeStore, local_node: NodeData | None = None, lang: str = "it") -> None:
    """Run the interactive table viewer as a standalone application."""
    InteractiveNodesApp(node_store=node_store, local_node=local_node, lang=lang).run()
