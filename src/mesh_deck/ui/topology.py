"""Data-first NeighborInfo topology explorer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

from mesh_deck.core.events import NeighborReport
from mesh_deck.i18n import t
from mesh_deck.ui.node_presentation import plain_markup
from mesh_deck.ui.theme import format_snr, format_time_ago

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient


class TopologyScreen(Screen[None]):
    """Explore NeighborInfo edge data with filters and explicit data quality."""

    BINDINGS = [
        Binding("q", "close", "Close", show=True),
        Binding("escape", "close", "Back", show=True),
        Binding("r", "refresh_topology", "Refresh", show=True),
        Binding("slash", "focus_filter", "Filter", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #topology-filter { height: 3; margin: 1 1 0 1; padding: 0 1; border: round $mesh-primary; background: $mesh-bg-elevated; }
    #topology-filter-label { width: 12; padding-top: 1; color: $mesh-primary; text-style: bold; }
    #topology-filter-input { width: 1fr; background: $mesh-bg-panel; color: $mesh-text; border: none; }
    #topology-body { height: 1fr; margin: 1; }
    #topology-table { width: 3fr; height: 1fr; border: round $mesh-border-soft; background: $mesh-bg-panel; }
    #topology-quality { width: 2fr; height: 1fr; margin-left: 1; padding: 1; border: round $mesh-primary; background: $mesh-bg-panel; }
    #topology-quality-title { color: $mesh-primary; text-style: bold; }
    #topology-quality-content { height: auto; color: $mesh-text; }
    DataTable > .datatable--header { background: $mesh-bg-elevated; color: $mesh-primary; text-style: bold; }
    DataTable > .datatable--cursor { background: $mesh-border-soft; color: $mesh-text; text-style: bold; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
    """

    def __init__(self, client: RadioClient, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = client
        self.lang = lang
        self._edges: dict[str, tuple[str, str]] = {}
        self.title = t("TOPOLOGY_TITLE", lang)
        self.sub_title = t("TOPOLOGY_SUBTITLE", lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_topology", t("BINDING_REFRESH", lang), show=True)]
        self._bindings.key_to_bindings["slash"] = [Binding("slash", "focus_filter", t("BINDING_FILTER", lang), show=True)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="topology-filter"):
            yield Label(t("FILTER_LABEL", self.lang), id="topology-filter-label")
            yield Input(placeholder=t("TOPOLOGY_FILTER_PLACEHOLDER", self.lang), id="topology-filter-input")
        with Horizontal(id="topology-body"):
            yield DataTable(id="topology-table", cursor_type="row")
            with Vertical(id="topology-quality"):
                yield Static(t("TOPOLOGY_QUALITY_TITLE", self.lang), id="topology-quality-title")
                yield Static(id="topology-quality-content")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#topology-table", DataTable)
        table.add_columns(
            (t("TOPOLOGY_COL_REPORTER", self.lang), "reporter"),
            (t("TOPOLOGY_COL_NEIGHBOR", self.lang), "neighbor"),
            (t("COL_SNR", self.lang), "snr"),
            (t("COL_LAST_HEARD", self.lang), "age"),
        )
        self.refresh_topology()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "topology-filter-input":
            self.refresh_topology()

    def _node_label(self, node_id: str) -> str:
        node = self.client.store.get_node(node_id)
        return node.display_name if node is not None else node_id

    def refresh_topology(self) -> None:
        reports = self.client.get_neighbor_reports()
        query = self.query_one("#topology-filter-input", Input).value.casefold().strip()
        table = self.query_one("#topology-table", DataTable)
        table.clear()
        self._edges = {}

        for report in reports:
            self._add_report_edges(table, report, query)

        self._render_quality(reports)

    def _add_report_edges(self, table: DataTable, report: NeighborReport, query: str) -> None:
        reporter_label = self._node_label(report.node_id)
        for link in report.neighbors:
            neighbor_label = self._node_label(link.node_id)
            haystack = f"{reporter_label} {report.node_id} {neighbor_label} {link.node_id}".casefold()
            if query and query not in haystack:
                continue
            key = f"{report.node_id}:{link.node_id}"
            table.add_row(
                reporter_label,
                neighbor_label,
                plain_markup(format_snr(link.snr)),
                plain_markup(format_time_ago(link.last_rx_time, self.lang)),
                key=key,
            )
            self._edges[key] = (report.node_id, link.node_id)

    def _render_quality(self, reports: list[NeighborReport]) -> None:
        newest = max((report.received_at for report in reports), default=None)
        lines = [
            t("TOPOLOGY_QUALITY_REPORTS", self.lang, count=len(reports)),
            t(
                "TOPOLOGY_QUALITY_NEWEST",
                self.lang,
                age=plain_markup(format_time_ago(newest, self.lang)) if newest else t("TIME_AGO_NEVER", self.lang),
            ),
        ]
        if reports:
            lines.append(t("TOPOLOGY_QUALITY_HINT", self.lang))
        else:
            lines.append(t("TOPOLOGY_EMPTY_HINT", self.lang))
        self.query_one("#topology-quality-content", Static).update("\n\n".join(lines))

    def action_refresh_topology(self) -> None:
        self.refresh_topology()

    def action_focus_filter(self) -> None:
        self.query_one("#topology-filter-input", Input).focus()

    def action_close(self) -> None:
        self.dismiss()
