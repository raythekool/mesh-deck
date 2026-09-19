"""Local, on-disk history of observed nodes and exchanged mesh messages.

Persistence is opt-in: RadioClient does not create a HistoryStore on its own,
so tests and library usage keep no file-system side effects unless a
HistoryStore is explicitly attached. The real CLI/TUI/MCP entrypoints wire
one in by default (see ``mesh_deck.__main__`` and ``mesh_deck.mcp_server``),
respecting the user's ``history_enabled`` setting.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from mesh_deck.core.events import MeshMessage, NodeData

logger = logging.getLogger(__name__)

HISTORY_DIR = Path.home() / ".config" / "mesh-deck" / "history"
NODES_HISTORY_FILE = "nodes.jsonl"
MESSAGES_HISTORY_FILE = "messages.jsonl"

# Fields used to detect a materially changed node snapshot, so a new history
# line is only appended when something worth recording actually changed
# (rather than on every noisy telemetry tick).
_NODE_SNAPSHOT_FIELDS = (
    "long_name",
    "short_name",
    "hw_model",
    "role",
    "battery_level",
    "latitude",
    "longitude",
    "altitude",
    "snr",
    "hops_away",
)


class HistoryStore:
    """Append-only JSONL history of node sightings and channel/DM messages.

    Files are written under ``base_dir`` (default ``~/.config/mesh-deck/history/``):
      - ``nodes.jsonl``: one line per meaningfully-changed node observation.
      - ``messages.jsonl``: one line per sent/received message, tagged by channel.
    """

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else HISTORY_DIR
        self._lock = threading.RLock()
        self._last_node_snapshot: dict[str, tuple[Any, ...]] = {}

    @property
    def nodes_file(self) -> Path:
        return self.base_dir / NODES_HISTORY_FILE

    @property
    def messages_file(self) -> Path:
        return self.base_dir / MESSAGES_HISTORY_FILE

    def record_node(self, node: NodeData) -> bool:
        """Append a node snapshot if it materially changed since last recorded.

        Returns:
            True if a new line was appended, False if skipped as a duplicate.
        """
        fingerprint = tuple(getattr(node, field_name, None) for field_name in _NODE_SNAPSHOT_FIELDS)
        with self._lock:
            if self._last_node_snapshot.get(node.id) == fingerprint:
                return False
            self._last_node_snapshot[node.id] = fingerprint
            entry = node.to_dict()
            entry["observed_at"] = datetime.now().isoformat()
            self._append(self.nodes_file, entry)
            return True

    def record_message(self, msg: MeshMessage, *, direction: str) -> None:
        """Append a sent ('out') or received ('in') message entry."""
        entry = msg.to_dict()
        entry["direction"] = direction
        entry["recorded_at"] = datetime.now().isoformat()
        self._append(self.messages_file, entry)

    def iter_node_history(self, node_id: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Return recorded node snapshots, optionally filtered by node ID."""
        entries = self._read_all(self.nodes_file)
        if node_id:
            entries = [e for e in entries if e.get("id") == node_id]
        return entries[-limit:] if limit else entries

    def iter_messages(
        self,
        channel: int | str | None = None,
        *,
        include_dm: bool = True,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return recorded messages, optionally filtered by channel and/or DM status."""
        entries = self._read_all(self.messages_file)
        if channel is not None:
            entries = [e for e in entries if e.get("channel") == channel]
        if not include_dm:
            entries = [e for e in entries if not e.get("is_dm")]
        return entries[-limit:] if limit else entries

    def _append(self, path: Path, entry: dict[str, Any]) -> None:
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            except OSError as exc:
                # History is best-effort; never let disk issues break live radio comms.
                logger.warning("Could not write history to %s: %s", path, exc)

    def _read_all(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.warning("Could not read history from %s: %s", path, exc)
            return []
        return entries
