"""Tactical status header / banner for Mesh-Deck.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from typing import Any
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from mesh_deck.models import NodeData
from mesh_deck.ui.theme import format_battery, format_role


def render_banner(
    local_node: NodeData | None,
    port: str,
    channel_util: float | None = None,
    channels: list[dict[str, Any]] | None = None,
) -> Panel:
    """Render a tactical Rich panel displaying active node, radio status, and quick commands.

    Args:
        local_node: NodeData object for the local Meshtastic device, or None if connecting.
        port: Serial port string (e.g. '/dev/ttyACM0').
        channel_util: Channel utilization percentage override.
        channels: Optional list of channel info dictionaries.

    Returns:
        Rich Panel styled with neon accents and rounded corners.
    """
    # Grid for the main status metrics (2 columns)
    grid = Table.grid(expand=True)
    grid.add_column(ratio=6, justify="left")
    grid.add_column(ratio=5, justify="left")

    if local_node is not None:
        name_display = f"[bold #00ff66]{local_node.long_name}[/bold #00ff66] [dim]({local_node.id})[/dim]"
        aka_display = f"[bold #00f3ff]{local_node.short_name}[/bold #00f3ff]"
        hw_display = f"[white]{local_node.hardware}[/white] {format_role(local_node.role)}"
        batt_display = format_battery(local_node.battery_level, local_node.voltage)
        region = local_node.region or "EU_868"
        preset = local_node.modem_preset or "LONG_FAST"

        # Determine effective channel utilization
        eff_ch_util = (
            channel_util
            if channel_util is not None
            else local_node.channel_utilization
        )
    else:
        name_display = "[bold #ffb800]IN CONNESSIONE / RICERCA...[/bold #ffb800]"
        aka_display = "[dim]--[/dim]"
        hw_display = "[dim]Sconosciuto[/dim]"
        batt_display = "[dim]--[/dim]"
        region = "EU_868"
        preset = "LONG_FAST"
        eff_ch_util = channel_util

    # Format channel utilization
    if eff_ch_util is not None:
        if eff_ch_util < 25.0:
            util_color = "#00ff66"
        elif eff_ch_util < 50.0:
            util_color = "#00f3ff"
        elif eff_ch_util < 75.0:
            util_color = "#ffb800"
        else:
            util_color = "#ff3366"
        util_display = f"[bold {util_color}]{eff_ch_util:.1f}%[/bold {util_color}]"
    else:
        util_display = "[dim]--[/dim]"

    # Left Column: Node identity & power
    left_content = (
        f"[dim #64748b]◈ NODO LOCALE:[/dim #64748b] {name_display}\n"
        f"  [dim #64748b]Alias / AKA:[/dim #64748b] {aka_display} [dim #64748b]| HW:[/dim #64748b] {hw_display}\n"
        f"  [dim #64748b]Batteria:[/dim #64748b]    {batt_display}"
    )

    # Right Column: RF & Radio connection
    right_content = (
        f"[dim #64748b]⚡ RADIO PORT:[/dim #64748b] [bold #00f3ff]{port}[/bold #00f3ff]\n"
        f"  [dim #64748b]Regione:[/dim #64748b]    [white]{region}[/white] [dim #64748b]• Preset:[/dim #64748b] [white]{preset}[/white]\n"
        f"  [dim #64748b]Ch. Util:[/dim #64748b]   {util_display}"
    )

    grid.add_row(left_content, right_content)

    elements: list[Any] = [grid]

    # Optional channel list row
    if channels:
        elements.append(Rule(style="#334155"))
        chan_parts: list[str] = []
        for ch in channels:
            idx = ch.get("index", 0)
            name = ch.get("name") or ("Primary" if idx == 0 else f"Ch_{idx}")
            modem = ch.get("modem")
            modem_suffix = f" [dim]({modem})[/dim]" if modem else ""
            chan_parts.append(f"[bold #00f3ff]#{name}[/bold #00f3ff][dim][{idx}][/dim]{modem_suffix}")
        elements.append(Text.from_markup(f"[dim #64748b]◈ CANALI ATTIVI:[/dim #64748b] {'  [dim]•[/dim]  '.join(chan_parts)}"))

    # Divider & quick commands
    elements.append(Rule(style="#334155"))
    cmd_text = (
        "[dim #64748b]❯ COMANDI:[/dim #64748b] "
        "[bold #00f3ff]/help[/bold #00f3ff] [dim #64748b]•[/dim #64748b] "
        "[bold #00f3ff]/nodes[/bold #00f3ff] [dim #64748b]•[/dim #64748b] "
        "[bold #00f3ff]/dm[/bold #00f3ff] [dim #64748b]•[/dim #64748b] "
        "[bold #00f3ff]/switch[/bold #00f3ff] [dim #64748b]•[/dim #64748b] "
        "[bold #00f3ff]/quit[/bold #00f3ff]"
    )
    elements.append(Text.from_markup(cmd_text))

    return Panel(
        Group(*elements),
        title="[bold #00f3ff]📡 MESH-DECK // TACTICAL CONSOLE[/bold #00f3ff]",
        title_align="left",
        subtitle="[dim #64748b]Hermes Meshtastic Interface[/dim #64748b]",
        subtitle_align="right",
        border_style="#00f3ff",
        box=box.ROUNDED,
        padding=(0, 1),
    )
