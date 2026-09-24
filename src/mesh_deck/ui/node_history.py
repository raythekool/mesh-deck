"""On-demand node telemetry history rendered from local JSONL snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Select, Static

from mesh_deck.core.history import HistoryStore
from mesh_deck.i18n import t
from mesh_deck.models import NodeData

HISTORY_RANGES = {
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "all": None,
}
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _parse_observed_at(entry: dict[str, Any]) -> datetime | None:
    value = entry.get("observed_at")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _sparkline(values: list[float], width: int = 42) -> str:
    """Render numeric samples as a compact Unicode sparkline."""
    if not values:
        return "—"
    samples = values[-width:]
    low, high = min(samples), max(samples)
    if low == high:
        return SPARK_CHARS[len(SPARK_CHARS) // 2] * len(samples)
    return "".join(
        SPARK_CHARS[round((value - low) / (high - low) * (len(SPARK_CHARS) - 1))]
        for value in samples
    )


class NodeHistoryScreen(Screen[None]):
    """Show bounded, on-demand telemetry history for one node."""

    BINDINGS = [
        Binding("q", "close", "Close", show=True),
        Binding("escape", "close", "Back", show=True),
        Binding("r", "refresh_history", "Refresh", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #history-controls { height: 3; margin: 1 1 0 1; padding: 0 1; border: round $mesh-primary; background: $mesh-bg-elevated; }
    #history-range-label { width: 16; padding-top: 1; color: $mesh-primary; text-style: bold; }
    #history-range { width: 16; }
    #history-summary { height: auto; margin: 1; padding: 1; border: round $mesh-border-soft; background: $mesh-bg-panel; color: $mesh-muted; }
    #history-metrics { height: 1fr; margin: 0 1 1 1; }
    .history-metric { height: 1fr; margin-bottom: 1; padding: 1; border: round $mesh-border-soft; background: $mesh-bg-panel; }
    .history-metric-title { color: $mesh-primary; text-style: bold; }
    .history-metric-value { color: $mesh-text; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
    """

    def __init__(self, node: NodeData, history: HistoryStore, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.node = node
        self.history = history
        self.lang = lang
        self.title = t("HISTORY_TITLE", lang, name=node.display_name)
        self.sub_title = t("HISTORY_SUBTITLE", lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_history", t("BINDING_REFRESH", lang), show=True)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="history-controls"):
            yield Label(t("HISTORY_RANGE_LABEL", self.lang), id="history-range-label")
            yield Select(
                [(t("HISTORY_RANGE_6H", self.lang), "6h"), (t("HISTORY_RANGE_24H", self.lang), "24h"), (t("HISTORY_RANGE_7D", self.lang), "7d"), (t("HISTORY_RANGE_ALL", self.lang), "all")],
                value="24h",
                id="history-range",
            )
        yield Static(id="history-summary")
        with Vertical(id="history-metrics"):
            for metric in ("battery", "snr", "temperature", "channel"):
                with Vertical(classes="history-metric", id=f"history-{metric}"):
                    yield Static(id=f"history-{metric}-title", classes="history-metric-title")
                    yield Static(id=f"history-{metric}-value", classes="history-metric-value")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_history()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "history-range":
            self.refresh_history()

    def _entries(self, range_key: str) -> list[dict[str, Any]]:
        window = HISTORY_RANGES[range_key]
        entries = self.history.iter_node_history(self.node.id)
        if window is None:
            return entries
        cutoff = datetime.now() - window
        return [entry for entry in entries if (_parse_observed_at(entry) or datetime.min) >= cutoff]

    def refresh_history(self) -> None:
        self._load_history(str(self.query_one("#history-range", Select).value))

    @work(thread=True, exclusive=True)
    def _load_history(self, range_key: str) -> None:
        self.app.call_from_thread(self._render_history, self._entries(range_key))

    def _render_history(self, entries: list[dict[str, Any]]) -> None:
        self.query_one("#history-summary", Static).update(
            t("HISTORY_SUMMARY", self.lang, count=len(entries), node=self.node.display_name)
            if entries
            else t("HISTORY_EMPTY", self.lang, node=self.node.display_name)
        )
        self._render_metric(
            "battery",
            entries,
            "battery_level",
            t("HISTORY_METRIC_BATTERY", self.lang),
            "%",
        )
        self._render_metric("snr", entries, "snr", t("HISTORY_METRIC_SNR", self.lang), " dB")
        self._render_metric(
            "temperature",
            entries,
            "temperature",
            t("HISTORY_METRIC_TEMPERATURE", self.lang),
            " °C",
        )
        self._render_metric(
            "channel",
            entries,
            "channel_util",
            t("HISTORY_METRIC_CHANNEL_UTIL", self.lang),
            "%",
        )

    def _render_metric(
        self,
        metric: str,
        entries: list[dict[str, Any]],
        field: str,
        title: str,
        suffix: str,
    ) -> None:
        values = [float(value) for entry in entries if (value := entry.get(field)) is not None]
        self.query_one(f"#history-{metric}-title", Static).update(title)
        if not values:
            content = t("HISTORY_METRIC_EMPTY", self.lang)
        else:
            content = f"{_sparkline(values)}  {values[-1]:.1f}{suffix}"
        self.query_one(f"#history-{metric}-value", Static).update(content)

    def action_refresh_history(self) -> None:
        self.refresh_history()

    def action_close(self) -> None:
        self.dismiss()
