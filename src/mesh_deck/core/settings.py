"""Settings and configuration management for Mesh-Deck."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "mesh-deck"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    """User preferences and settings configuration."""

    language: str = "it"  # "it" | "en"
    theme: str = "cyberpunk"  # "cyberpunk" | "high_contrast" | "amber" | "matrix"
    default_port: str | None = None
    default_sort: str = "last_heard"  # "last_heard" | "snr" | "hops" | "name"
    ui_mode: str = "repl"  # "repl" | "tui"

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
