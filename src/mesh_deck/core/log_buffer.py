"""Bounded, thread-safe application and radio-device diagnostic log buffer."""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LogEntry:
    """One diagnostic line retained for the interactive log viewer."""

    sequence: int
    timestamp: datetime
    source: str  # "app" | "device"
    level: int
    message: str
    logger_name: str = ""
    port: str | None = None

    @property
    def level_name(self) -> str:
        return logging.getLevelName(self.level)

    def to_line(self) -> str:
        """Stable text representation used by clipboard and export."""
        origin = self.port or self.logger_name or self.source
        return f"{self.timestamp.isoformat(timespec='seconds')} [{self.source}:{origin}] {self.level_name}: {self.message}"


class LogBuffer(logging.Handler):
    """A bounded logging handler with a second stream for Meshtastic device lines."""

    def __init__(self, max_entries: int = 2_000) -> None:
        super().__init__(level=logging.DEBUG)
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._listeners: list[Callable[[LogEntry], None]] = []
        self._lock = threading.RLock()
        self._sequence = 0
        self._attached_logger: logging.Logger | None = None
        self._previous_level: int | None = None
        self._previous_propagate: bool | None = None

    def attach(self, logger: logging.Logger | None = None) -> None:
        """Capture Mesh-Deck application logs while the Textual app is mounted."""
        with self._lock:
            if self._attached_logger is not None:
                return
            target = logger or logging.getLogger("mesh_deck")
            self._previous_level = target.level
            self._previous_propagate = target.propagate
            target.setLevel(logging.DEBUG)
            # The viewer owns these records while mounted. Do not duplicate
            # debug diagnostics to root handlers or MCP stdout.
            target.propagate = False
            target.addHandler(self)
            self._attached_logger = target

    def detach(self) -> None:
        """Stop capturing application logs, retaining entries already collected."""
        with self._lock:
            if self._attached_logger is None:
                return
            self._attached_logger.removeHandler(self)
            if self._previous_level is not None:
                self._attached_logger.setLevel(self._previous_level)
            if self._previous_propagate is not None:
                self._attached_logger.propagate = self._previous_propagate
            self._attached_logger = None
            self._previous_level = None
            self._previous_propagate = None

    def emit(self, record: logging.LogRecord) -> None:
        """Record a Python application log line without feeding logging recursively."""
        try:
            message = record.getMessage()
        except Exception:
            message = "<unformattable log record>"
        self._append(
            source="app",
            level=record.levelno,
            message=message,
            logger_name=record.name,
        )

    def record_device(self, line: str, port: str | None = None) -> None:
        """Record a line forwarded by the connected Meshtastic device."""
        self._append(
            source="device",
            level=logging.INFO,
            message=line.rstrip(),
            port=port,
        )

    def entries(
        self,
        *,
        source: str = "all",
        minimum_level: int = logging.WARNING,
        query: str = "",
    ) -> list[LogEntry]:
        """Return a snapshot filtered by source, minimum level, and free text."""
        normalized_query = query.casefold().strip()
        with self._lock:
            values = list(self._entries)
        return [
            entry
            for entry in values
            if (source == "all" or entry.source == source)
            and entry.level >= minimum_level
            and (not normalized_query or normalized_query in entry.to_line().casefold())
        ]

    def add_listener(self, callback: Callable[[LogEntry], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[LogEntry], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _append(
        self,
        *,
        source: str,
        level: int,
        message: str,
        logger_name: str = "",
        port: str | None = None,
    ) -> None:
        if not message:
            return
        with self._lock:
            self._sequence += 1
            entry = LogEntry(
                sequence=self._sequence,
                timestamp=datetime.now(),
                source=source,
                level=level,
                message=message,
                logger_name=logger_name,
                port=port,
            )
            self._entries.append(entry)
            listeners = list(self._listeners)
        for callback in listeners:
            callback(entry)
