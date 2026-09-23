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
    THEME_COLORS,
    THEMES,
    css_variables,
    format_battery,
    format_bearing,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
    set_theme,
    theme_names,
)

__all__ = [
    "THEME_COLORS",
    "THEMES",
    "css_variables",
    "set_theme",
    "theme_names",
    "SLASH_COMMANDS",
    "format_snr",
    "format_battery",
    "format_bearing",
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
