"""Domain models for Mesh-Deck nodes, messages, and telemetry.

Re-exports core domain models from mesh_deck.core.events for convenience and clean architecture.
"""

from __future__ import annotations

from mesh_deck.core.events import (
    DeviceConnectionInfo,
    MeshMessage,
    NodeData,
)

__all__ = [
    "NodeData",
    "MeshMessage",
    "DeviceConnectionInfo",
]
