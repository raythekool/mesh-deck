"""UI package for Mesh-Deck TUI / CLI."""

from mesh_deck.models import DeviceConnectionInfo, MeshMessage, NodeData
from mesh_deck.ui.banner import render_banner
from mesh_deck.ui.completer import SLASH_COMMANDS, MeshDeckCompleter
from mesh_deck.ui.device_selector import DeviceSelectorApp, select_device
from mesh_deck.ui.interactive_table import InteractiveNodesApp, InteractiveNodesScreen, launch_interactive_nodes
from mesh_deck.ui.repl import MeshDeckREPL
from mesh_deck.ui.tables import (
    render_message,
    render_node_detail,
    render_nodes_table,
)
from mesh_deck.ui.theme import (
    CYBERPUNK_THEME,
    THEME_COLORS,
    THEMES,
    format_battery,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
)

__all__ = [
    "CYBERPUNK_THEME",
    "THEME_COLORS",
    "THEMES",
    "SLASH_COMMANDS",
    "format_snr",
    "format_battery",
    "format_role",
    "format_time_ago",
    "format_hops",
    "format_distance",
    "render_banner",
    "render_nodes_table",
    "render_node_detail",
    "render_message",
    "MeshDeckCompleter",
    "DeviceSelectorApp",
    "select_device",
    "MeshDeckREPL",
    "InteractiveNodesApp",
    "InteractiveNodesScreen",
    "launch_interactive_nodes",
    "NodeData",
    "MeshMessage",
    "DeviceConnectionInfo",
]
