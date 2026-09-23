"""Tactical status header / banner for Mesh-Deck.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from typing import Any
from rich import box
from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from mesh_deck.i18n import t
from mesh_deck.models import NodeData
from mesh_deck.ui.theme import THEME_COLORS as c, format_battery, format_role


def render_banner(
    local_node: NodeData | None,
    port: str,
    channel_util: float | None = None,
    channels: list[dict[str, Any]] | None = None,
    lang: str = "it",
) -> Panel:
    """Render a tactical Rich panel displaying active node, radio status, and quick commands.

    Args:
        local_node: NodeData object for the local Meshtastic device, or None if connecting.
        port: Serial port string (e.g. '/dev/ttyACM0').
        channel_util: Channel utilization percentage override.
        channels: Optional list of channel info dictionaries.
        lang: Language code ("it" or "en") for label translation.

    Returns:
        Rich Panel styled with neon accents and rounded corners.
    """
    # Grid for the main status metrics (2 columns)
    grid = Table.grid(expand=True)
    grid.add_column(ratio=6, justify="left")
    grid.add_column(ratio=5, justify="left")

    port_safe = escape(str(port or "N/A"))

    if local_node is not None:
        long_safe = escape(str(local_node.long_name or t("BANNER_UNKNOWN", lang)))
        short_safe = escape(str(local_node.short_name or "????"))
        id_safe = escape(str(local_node.id or "!unknown"))
        hw_safe = escape(str(local_node.hardware or "UNSET"))
        name_display = f"[bold {c['secondary']}]{long_safe}[/bold {c['secondary']}] [dim]({id_safe})[/dim]"
        aka_display = f"[bold {c['primary']}]{short_safe}[/bold {c['primary']}]"
        hw_display = f"[white]{hw_safe}[/white] {format_role(local_node.role)}"
        batt_display = format_battery(local_node.battery_level, local_node.voltage)
        region = escape(str(local_node.region or "EU_868"))
        preset = escape(str(local_node.modem_preset or "LONG_FAST"))

        # Determine effective channel utilization
        eff_ch_util = (
            channel_util
            if channel_util is not None
            else local_node.channel_utilization
        )
    else:
        name_display = f"[bold {c['accent']}]{t('BANNER_CONNECTING', lang)}[/bold {c['accent']}]"
        aka_display = "[dim]--[/dim]"
        hw_display = f"[dim]{t('BANNER_UNKNOWN', lang)}[/dim]"
        batt_display = "[dim]--[/dim]"
        region = "EU_868"
        preset = "LONG_FAST"
        eff_ch_util = channel_util

    # Format channel utilization
    if eff_ch_util is not None:
        if eff_ch_util < 25.0:
            util_color = c["secondary"]
        elif eff_ch_util < 50.0:
            util_color = c["primary"]
        elif eff_ch_util < 75.0:
            util_color = c["accent"]
        else:
            util_color = c["alert"]
        util_display = f"[bold {util_color}]{eff_ch_util:.1f}%[/bold {util_color}]"
    else:
        util_display = "[dim]--[/dim]"

    # Left Column: Node identity & power
    left_content = (
        f"[dim {c['muted']}]◈ {t('LOCAL_NODE', lang)}:[/dim {c['muted']}] {name_display}\n"
        f"  [dim {c['muted']}]{t('BANNER_ALIAS', lang)}:[/dim {c['muted']}] {aka_display} [dim {c['muted']}]| {t('BANNER_HW_LABEL', lang)}:[/dim {c['muted']}] {hw_display}\n"
        f"  [dim {c['muted']}]{t('BATTERY', lang)}:[/dim {c['muted']}]    {batt_display}"
    )

    # Right Column: RF & Radio connection
    right_content = (
        f"[dim {c['muted']}]⚡ {t('RADIO_PORT', lang)}:[/dim {c['muted']}] [bold {c['primary']}]{port_safe}[/bold {c['primary']}]\n"
        f"  [dim {c['muted']}]{t('REGION', lang)}:[/dim {c['muted']}]    [white]{region}[/white] [dim {c['muted']}]• {t('PRESET', lang)}:[/dim {c['muted']}] [white]{preset}[/white]\n"
        f"  [dim {c['muted']}]{t('CH_UTIL', lang)}:[/dim {c['muted']}]   {util_display}"
    )

    grid.add_row(left_content, right_content)

    elements: list[Any] = [grid]

    # Optional channel list row
    if channels:
        elements.append(Rule(style=c["border_dim"]))
        chan_parts: list[str] = []
        for ch in channels:
            idx = ch.get("index", 0)
            name = ch.get("name") or ("Primary" if idx == 0 else f"Ch_{idx}")
            modem = ch.get("modem")
            modem_suffix = f" [dim]({escape(str(modem))})[/dim]" if modem else ""
            chan_parts.append(f"[bold {c['primary']}]#{escape(str(name))}[/bold {c['primary']}][dim][{idx}][/dim]{modem_suffix}")
        elements.append(Text.from_markup(f"[dim {c['muted']}]◈ {t('ACTIVE_CHANNELS', lang)}:[/dim {c['muted']}] {'  [dim]•[/dim]  '.join(chan_parts)}"))

    # Divider & quick commands
    elements.append(Rule(style=c["border_dim"]))
    cmd_names = ["/help", "/nodes", "/view", "/dm", "/switch", "/settings", "/quit"]
    cmd_sep = f" [dim {c['muted']}]•[/dim {c['muted']}] "
    cmd_list = cmd_sep.join(f"[bold {c['primary']}]{name}[/bold {c['primary']}]" for name in cmd_names)
    cmd_prefix = t("COMMANDS_SHORTCUTS", lang).split(":", 1)[0]
    cmd_text = f"[dim {c['muted']}]❯ {cmd_prefix}:[/dim {c['muted']}] {cmd_list}"
    elements.append(Text.from_markup(cmd_text))

    return Panel(
        Group(*elements),
        title=f"[bold {c['primary']}]{t('BANNER_TITLE', lang)}[/bold {c['primary']}]",
        title_align="left",
        subtitle=f"[dim {c['muted']}]{t('BANNER_SUBTITLE', lang)}[/dim {c['muted']}]",
        subtitle_align="right",
        border_style=c["primary"],
        box=box.ROUNDED,
        padding=(0, 1),
    )
