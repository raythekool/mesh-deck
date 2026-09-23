"""Settings and configuration management for Mesh-Deck."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "mesh-deck"
CONFIG_FILE = CONFIG_DIR / "settings.json"
MAX_COMMAND_HISTORY = 100


@dataclass
class Settings:
    """User preferences and settings configuration."""

    language: str = "it"  # "it" | "en"
    theme: str = "cyberpunk"  # "cyberpunk" | "high_contrast" | "amber" | "matrix"
    default_port: str | None = None
    default_sort: str = "last_heard"  # "last_heard" | "snr" | "hops" | "name"
    ui_mode: str = "repl"  # "repl" | "tui"
    command_history: list[str] = field(default_factory=list)
    notifications_enabled: bool = True
    history_enabled: bool = True
    sidebar_enabled: bool = True

    @classmethod
    def load(cls) -> Settings:
        """Load settings from disk or return default instance."""
        if not CONFIG_FILE.exists():
            return cls()

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return cls(
                    language=data.get("language", "it"),
                    theme=data.get("theme", "cyberpunk"),
                    default_port=data.get("default_port"),
                    default_sort=data.get("default_sort", "last_heard"),
                    ui_mode=data.get("ui_mode", "repl"),
                    command_history=cls._valid_history(data.get("command_history")),
                    notifications_enabled=bool(data.get("notifications_enabled", True)),
                    history_enabled=bool(data.get("history_enabled", True)),
                    sidebar_enabled=bool(data.get("sidebar_enabled", True)),
                )
        except Exception:
            pass

        return cls()

    def save(self) -> bool:
        """Persist settings to ~/.config/mesh-deck/settings.json."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def update(self, **kwargs: Any) -> bool:
        """Update fields and persist changes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self.save()

    @staticmethod
    def _valid_history(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item.strip()][-MAX_COMMAND_HISTORY:]

    def add_command(self, command: str) -> bool:
        """Record a command, avoiding adjacent duplicates."""
        normalized = command.strip()
        if not normalized:
            return True
        if self.command_history and self.command_history[-1] == normalized:
            return True
        self.command_history.append(normalized)
        self.command_history = self.command_history[-MAX_COMMAND_HISTORY:]
        return self.save()
