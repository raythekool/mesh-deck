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
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

if TYPE_CHECKING:
    from mesh_deck.core.events import NodeData
    from mesh_deck.core.node_store import NodeStore


def _clean_text(markup_or_str: str) -> str:
    """Strip Rich markup tags for clean Textual cell display."""
    return re.sub(r"\[/?.*?\]", "", str(markup_or_str)).strip()


class InteractiveNodesScreen(Screen):
    """Interactive table screen with mouse click column sorting."""

    TITLE = "📡 MESH-DECK // INTERACTIVE NODE EXPLORER"
    SUB_TITLE = "Fai click su una colonna per ordinare • Premi 'q' o 'Esc' per tornare al prompt"

    BINDINGS = [
        Binding("q", "close", "Chiudi / Esci", show=True),
        Binding("escape", "close", "Torna al prompt", show=True),
        Binding("r", "refresh_nodes", "Aggiorna", show=True),
        Binding("slash", "focus_filter", "Cerca / Filtra", show=True),
    ]

    CSS = """
    Screen {
        background: #0a0e17;
        color: #f8fafc;
    }

    #filter-bar {
        height: 3;
        margin: 1 1 0 1;
        background: #111827;
        border: round #00f3ff;
        padding: 0 1;
    }

    #filter-label {
        width: 12;
        color: #00f3ff;
        text-style: bold;
        padding-top: 1;
    }

    #filter-input {
        width: 1fr;
        background: #0f172a;
        color: #00ff66;
        border: none;
    }

    #table-container {
        height: 1fr;
        margin: 1;
    }

    DataTable {
        background: #0a0e17;
        border: round #38bdf8;
        color: #f8fafc;
    }

    DataTable > .datatable--header {
        background: #1e293b;
        color: #00f3ff;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #0369a1;
        color: #ffffff;
        text-style: bold;
    }

    Footer {
        background: #0f172a;
        color: #94a3b8;
    }
    """

    def __init__(
        self,
        node_store: NodeStore,
        local_node: NodeData | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node
        self.sort_column_idx = 0
        self.sort_reverse = False
        self.column_keys: list[str] = []
        self._raw_rows: list[list[Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="filter-bar"):
            yield Label("🔍 Filtra:", id="filter-label")
            yield Input(placeholder="Cerca per nome, AKA, hardware o ID...", id="filter-input")
        with Vertical(id="table-container"):
            yield DataTable(id="nodes-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize table columns and populate initial node rows."""
        table = self.query_one(DataTable)
        columns = [
            ("#", "idx"),
            ("Nome Nodo", "name"),
            ("AKA", "aka"),
            ("ID", "id"),
            ("Hardware", "hardware"),
            ("Ruolo", "role"),
            ("SNR", "snr"),
            ("Hops", "hops"),
            ("Batteria", "battery"),
            ("Distanza", "distance"),
            ("Ultimo Contatto", "last_heard"),
        ]

        self.column_keys = []
        for title, key in columns:
            col_key = table.add_column(title, key=key)
            self.column_keys.append(str(col_key))

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
                name_display = f"★ {name_display} (LOCALE)"

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
                hops_str = "Diretto (0)" if hops_val == 0 else f"{hops_val} hops"
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
            from mesh_deck.ui.theme import format_time_ago
            last_heard_str = _clean_text(format_time_ago(node.last_heard))

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

        def _sort_key(row: list[Any]) -> Any:
            val = row[col_idx]
            if isinstance(val, (int, float)):
                return val
            val_str = str(val).strip()

            # Attempt numeric conversion for SNR
            if "dB" in val_str:
                clean = val_str.replace("dB", "").strip()
                try:
                    return float(clean)
                except ValueError:
                    return float("-inf")

            # Attempt numeric conversion for Hops
            if "Diretto" in val_str:
                return 0
            if "hops" in val_str:
                clean = val_str.replace("hops", "").strip()
                try:
                    return int(clean)
                except ValueError:
                    return 999

            # Attempt numeric conversion for Distance
            if val_str.endswith("km"):
                clean = val_str.replace("km", "").strip()
                try:
                    return float(clean) * 1000
                except ValueError:
                    return float("inf")
            if val_str.endswith("m"):
                clean = val_str.replace("m", "").strip()
                try:
                    return float(clean)
                except ValueError:
                    return float("inf")

            if val_str == "--":
                return ""

            return val_str.lower()

        self._raw_rows.sort(key=_sort_key, reverse=reverse)

        # Clear and repopulate
        table.clear()
        for row in self._raw_rows:
            table.add_row(*row)

        arrow = "▼" if reverse else "▲"
        col_name = table.columns[event_col_key_or_idx(table, col_idx)].label
        clean_name = re.sub(r"[▲▼]", "", str(col_name)).strip()
        self.sub_title = f"Ordinato per: {clean_name} {arrow} • Click su un header per cambiare ordinamento"

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


def event_col_key_or_idx(table: DataTable, col_idx: int) -> Any:
    """Helper to get column key by index."""
    keys = list(table.columns.keys())
    return keys[col_idx] if 0 <= col_idx < len(keys) else col_idx


class InteractiveNodesApp(App):
    """Standalone wrapper for launching the reusable node explorer screen."""

    def __init__(
        self,
        node_store: NodeStore,
        local_node: NodeData | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.store = node_store
        self.local_node = local_node

    def on_mount(self) -> None:
        self.push_screen(
            InteractiveNodesScreen(self.store, local_node=self.local_node),
            callback=lambda _: self.exit(),
        )


def launch_interactive_nodes(node_store: NodeStore, local_node: NodeData | None = None) -> None:
    """Run the interactive table viewer as a standalone application."""
    InteractiveNodesApp(node_store=node_store, local_node=local_node).run()
