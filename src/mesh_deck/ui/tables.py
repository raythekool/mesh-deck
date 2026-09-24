"""Rich tables and detail panels for Meshtastic nodes and messages.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from rich import box
from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from mesh_deck.i18n import t
from mesh_deck.models import MeshMessage, NodeData
from mesh_deck.ui.node_presentation import present_node
from mesh_deck.ui.theme import (
    THEME_COLORS as c,
    format_battery,
    format_bearing,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
)


def render_nodes_table(
    nodes: list[NodeData],
    local_node_id: str | None = None,
    lang: str = "it",
) -> Table:
    """Render a tactical Rich table listing all discovered nodes in the mesh.

    Args:
        nodes: List of NodeData objects.
        local_node_id: Node ID (e.g. '!45a466e4') of the local device for highlighting.

    Returns:
        Rich Table configured with rounded borders and cyberpunk color scheme.
    """
    table = Table(
        title=f"[bold {c['primary']}]{t('NODES_TABLE_TITLE', lang, count=len(nodes))}[/bold {c['primary']}]",
        title_justify="left",
        box=box.ROUNDED,
        header_style=f"bold {c['primary']}",
        border_style=c["border_dim"],
        collapse_padding=True,
        pad_edge=False,
        show_lines=False,
    )

    table.add_column("#", justify="right", style="dim", min_width=2, no_wrap=True)
    table.add_column(t("COL_NAME", lang), justify="left", min_width=12, no_wrap=True, overflow="ellipsis")
    table.add_column(t("COL_AKA", lang), justify="center", min_width=5, no_wrap=True)
    table.add_column(t("COL_ID", lang), justify="center", style="dim", min_width=9, no_wrap=True)
    table.add_column(t("COL_HARDWARE", lang), justify="left", min_width=10, overflow="ellipsis", no_wrap=True)
    table.add_column(t("COL_ROLE", lang), justify="center", min_width=7, no_wrap=True)
    table.add_column(t("COL_SNR", lang), justify="right", min_width=8, no_wrap=True)
    table.add_column(t("COL_HOPS", lang), justify="center", min_width=11, no_wrap=True)
    table.add_column(t("COL_BATTERY", lang), justify="center", min_width=11, no_wrap=True)
    table.add_column(t("COL_DISTANCE", lang), justify="right", min_width=8, no_wrap=True)
    table.add_column(t("COL_LAST_HEARD", lang), justify="right", min_width=8, no_wrap=True)

    for idx, node in enumerate(nodes, start=1):
        is_local = False
        if local_node_id:
            clean_local = local_node_id.strip()
            is_local = (
                node.id == clean_local
                or (node.num is not None and str(node.num) == clean_local)
                or (node.short_name.lower() == clean_local.lower())
            )

        display = present_node(node, lang=lang)
        long_name_safe = escape(str(node.long_name or t("NODE_UNKNOWN_NAME", lang)))
        short_name_safe = escape(str(node.short_name or "????"))
        node_id_safe = escape(str(node.id or "!unknown"))
        hw_safe = escape(display.hardware)

        if is_local:
            node_name = f"[bold {c['secondary']}]★ [/bold {c['secondary']}][bold {c['primary']}]{long_name_safe}[/bold {c['primary']}] [dim]({t('LOCAL_BADGE', lang)})[/dim]"
            aka = f"[bold {c['secondary']}]{short_name_safe}[/bold {c['secondary']}]"
            node_id_str = f"[bold {c['primary']}]{node_id_safe}[/bold {c['primary']}]"
            row_style = "bold"
        else:
            node_name = f"[bold {c['text']}]{long_name_safe}[/bold {c['text']}]"
            aka = f"[{c['primary']}]{short_name_safe}[/{c['primary']}]"
            node_id_str = f"[dim]{node_id_safe}[/dim]"
            row_style = None

        hw_display = f"[white]{hw_safe}[/white]"
        role_badge = display.role_markup
        snr_display = display.snr_markup
        hops_display = display.hops_markup
        batt_display = display.battery_markup
        dist_display = display.distance_markup
        seen_display = display.last_heard_markup

        table.add_row(
            str(idx),
            node_name,
            aka,
            node_id_str,
            hw_display,
            role_badge,
            snr_display,
            hops_display,
            batt_display,
            dist_display,
            seen_display,
            style=row_style,
        )

    return table


def render_node_detail(
    node: NodeData,
    distance_km: float | None = None,
    lang: str = "it",
    bearing_deg: float | None = None,
) -> Panel:
    """Render an in-depth analytical dossier panel for a single node.

    Includes identity, radio telemetry, GPS location with OpenStreetMap link,
    and environmental sensor readings.

    Args:
        node: NodeData object.
        distance_km: Optional distance in kilometers relative to current position.
        lang: Language code ("it" or "en") for label translation.

    Returns:
        Rich Panel containing organized analytical telemetry grids.
    """
    effective_dist = distance_km if distance_km is not None else node.distance_km

    long_name_safe = escape(str(node.long_name or t("NODE_UNKNOWN_NAME", lang)))
    short_name_safe = escape(str(node.short_name or "????"))
    node_id_safe = escape(str(node.id or "!unknown"))
    hw_safe = escape(str(node.hardware or "UNSET"))

    # Section 1: Identity & Role
    id_grid = Table.grid(expand=True)
    id_grid.add_column(ratio=6)
    id_grid.add_column(ratio=6)

    licensed_str = (
        f"[bold {c['secondary']}]{t('LICENSED_YES', lang)}[/bold {c['secondary']}]"
        if node.is_licensed
        else f"[dim]{t('LICENSED_NO', lang)}[/dim]"
    )
    id_grid.add_row(
        f"[dim {c['muted']}]{t('LABEL_FULL_NAME', lang)}:[/dim {c['muted']}]   [bold {c['secondary']}]{long_name_safe}[/bold {c['secondary']}]\n"
        f"[dim {c['muted']}]{t('LABEL_AKA', lang)}:[/dim {c['muted']}]      [bold {c['primary']}]{short_name_safe}[/bold {c['primary']}]\n"
        f"[dim {c['muted']}]{t('LABEL_NODE_ID', lang)}:[/dim {c['muted']}]          [white]{node_id_safe}[/white] "
        f"[dim]{t('LABEL_DEC', lang, num=node.num or '--')}[/dim]",
        f"[dim {c['muted']}]{t('LABEL_HW_MODEL', lang)}:[/dim {c['muted']}]       [white]{hw_safe}[/white]\n"
        f"[dim {c['muted']}]{t('LABEL_DEVICE_ROLE', lang)}:[/dim {c['muted']}] {format_role(node.role)}\n"
        f"[dim {c['muted']}]{t('LABEL_RADIO_LICENSE', lang)}:[/dim {c['muted']}]    {licensed_str}",
    )

    # Section 2: Radio Metrics & Propagation
    last_heard_full = (
        node.last_heard.strftime("%Y-%m-%d %H:%M:%S")
        if node.last_heard
        else "N/A"
    )
    last_heard_display = f"{format_time_ago(node.last_heard, lang)} [dim]({last_heard_full})[/dim]"

    ch_util_str = f"{node.channel_utilization:.1f}%" if node.channel_utilization is not None else "[dim]--[/dim]"
    air_util_str = f"{node.air_util_tx:.2f}%" if node.air_util_tx is not None else "[dim]--[/dim]"

    radio_grid = Table.grid(expand=True)
    radio_grid.add_column(ratio=6)
    radio_grid.add_column(ratio=6)

    radio_grid.add_row(
        f"[dim {c['muted']}]{t('LABEL_SNR', lang)}:[/dim {c['muted']}]    {format_snr(node.snr)}\n"
        f"[dim {c['muted']}]{t('LABEL_HOPS_AWAY', lang)}:[/dim {c['muted']}]        {format_hops(node.hops_away, lang)}\n"
        f"[dim {c['muted']}]{t('LABEL_LAST_HEARD', lang)}:[/dim {c['muted']}]  {last_heard_display}",
        f"[dim {c['muted']}]{t('LABEL_CH_UTIL', lang)}:[/dim {c['muted']}]  [white]{ch_util_str}[/white]\n"
        f"[dim {c['muted']}]{t('LABEL_AIR_UTIL', lang)}:[/dim {c['muted']}]      [white]{air_util_str}[/white]\n"
        f"[dim {c['muted']}]{t('LABEL_MODEM_PRESET', lang)}:[/dim {c['muted']}]     [white]{node.modem_preset or 'LONG_FAST'}[/white]",
    )

    # Section 3: Power & Environmental Telemetry
    batt_str = format_battery(node.battery_level, node.voltage)
    volt_str = f"{node.voltage:.2f} V" if node.voltage is not None else "[dim]--[/dim]"
    temp_str = f"{node.temperature:.1f} °C" if node.temperature is not None else "[dim]--[/dim]"
    hum_str = f"{node.relative_humidity:.1f}%" if node.relative_humidity is not None else "[dim]--[/dim]"
    press_str = f"{node.barometric_pressure:.1f} hPa" if node.barometric_pressure is not None else "[dim]--[/dim]"

    power_grid = Table.grid(expand=True)
    power_grid.add_column(ratio=6)
    power_grid.add_column(ratio=6)

    power_grid.add_row(
        f"[dim {c['muted']}]{t('LABEL_BATTERY_FULL', lang)}:[/dim {c['muted']}]         {batt_str}\n"
        f"[dim {c['muted']}]{t('LABEL_CELL_VOLTAGE', lang)}:[/dim {c['muted']}]   [white]{volt_str}[/white]",
        f"[dim {c['muted']}]{t('LABEL_TEMPERATURE', lang)}:[/dim {c['muted']}]      [white]{temp_str}[/white]\n"
        f"[dim {c['muted']}]{t('LABEL_HUMIDITY', lang)}:[/dim {c['muted']}] [white]{hum_str}[/white] "
        f"[dim {c['muted']}]| {t('LABEL_PRESSURE', lang)}:[/dim {c['muted']}] [white]{press_str}[/white]",
    )

    # Section 4: Geographic Position & OpenStreetMap
    geo_grid = Table.grid(expand=True)
    geo_grid.add_column(ratio=6)
    geo_grid.add_column(ratio=6)

    if node.has_coords:
        coords_val = f"[bold {c['primary']}]{node.latitude:.5f}, {node.longitude:.5f}[/bold {c['primary']}]"
        alt_val = f"{node.altitude:.0f} {t('ALTITUDE_SUFFIX', lang)}" if node.altitude is not None else "[dim]--[/dim]"
        osm_link = (
            f"[link={node.osm_url}][bold {c['secondary']}]{t('OSM_LINK_TEXT', lang)}[/bold {c['secondary']}][/link] "
            f"[dim {c['muted']}]({node.osm_url})[/dim {c['muted']}]"
        )
    else:
        coords_val = f"[dim]{t('NO_COORDS', lang)}[/dim]"
        alt_val = "[dim]--[/dim]"
        osm_link = f"[dim]{t('NO_COORDS_MAP', lang)}[/dim]"

    dist_str = format_distance(effective_dist)

    geo_grid.add_row(
        f"[dim {c['muted']}]{t('LABEL_GPS_COORDS', lang)}:[/dim {c['muted']}]   {coords_val}\n"
        f"[dim {c['muted']}]{t('LABEL_ALTITUDE', lang)}:[/dim {c['muted']}]       [white]{alt_val}[/white]\n"
        f"[dim {c['muted']}]{t('LABEL_DISTANCE_EST', lang)}:[/dim {c['muted']}]   [bold {c['accent']}]{dist_str}[/bold {c['accent']}]\n"
        f"[dim {c['muted']}]{t('LABEL_BEARING', lang)}:[/dim {c['muted']}]       [bold {c['accent']}]{format_bearing(bearing_deg)}[/bold {c['accent']}]",
        f"[dim {c['muted']}]{t('LABEL_OSM', lang)}:[/dim {c['muted']}]\n{osm_link}",
    )

    # Section 5: Security / Public Key (if available)
    pubkey_str = (
        f"[dim {c['muted']}]{escape(str(node.public_key))}[/dim {c['muted']}]"
        if node.public_key
        else f"[dim]{t('PUBKEY_NONE', lang)}[/dim]"
    )

    elements = [
        Text.from_markup(f"[bold {c['primary']}]{t('SECTION_IDENTITY', lang)}[/bold {c['primary']}]"),
        id_grid,
        Rule(style=c["border_dim"]),
        Text.from_markup(f"[bold {c['primary']}]{t('SECTION_RADIO', lang)}[/bold {c['primary']}]"),
        radio_grid,
        Rule(style=c["border_dim"]),
        Text.from_markup(f"[bold {c['primary']}]{t('SECTION_POWER', lang)}[/bold {c['primary']}]"),
        power_grid,
        Rule(style=c["border_dim"]),
        Text.from_markup(f"[bold {c['primary']}]{t('SECTION_GEO', lang)}[/bold {c['primary']}]"),
        geo_grid,
        Rule(style=c["border_dim"]),
        Text.from_markup(f"[dim {c['muted']}]{t('LABEL_PUBKEY', lang)}:[/dim {c['muted']}] {pubkey_str}"),
    ]

    return Panel(
        Group(*elements),
        title=f"[bold {c['primary']}]{t('NODE_DETAIL_TITLE', lang, name=short_name_safe, id=node_id_safe)}[/bold {c['primary']}]",
        title_align="left",
        subtitle=f"[dim {c['muted']}]{t('NODE_DETAIL_SUBTITLE', lang)}[/dim {c['muted']}]",
        subtitle_align="right",
        border_style=c["primary"],
        box=box.ROUNDED,
        padding=(1, 2),
    )


def render_message(
    msg: MeshMessage,
    as_panel: bool | None = None,
    lang: str = "it",
) -> Text | Panel:
    """Format an incoming or transmitted mesh message.

    Direct messages (DM) are styled inside a tactical alert Panel by default,
    while broadcast messages render as sleek, single-line terminal logs.

    Args:
        msg: MeshMessage object.
        as_panel: If True, forces Panel output. If None, defaults to True for DMs.
        lang: Language code ("it" or "en") for label translation.

    Returns:
        Rich Text or Panel object.
    """
    timestamp_str = msg.timestamp.strftime("[%H:%M:%S]") if msg.timestamp else "[--:--:--]"
    sender_raw = msg.sender_name or msg.sender_short_name or msg.sender_id or t("MSG_SENDER_UNKNOWN", lang)
    sender_display = escape(str(sender_raw))
    sender_id_safe = escape(str(msg.sender_id or "!unknown"))
    snr_display = f" [{format_snr(msg.snr)}]" if msg.snr is not None else ""
    text_safe = escape(str(msg.text or ""))

    should_render_panel = msg.is_direct if as_panel is None else as_panel

    if should_render_panel:
        recipient_raw = msg.recipient_name or msg.recipient_id or "^all"
        recipient_display = escape(str(recipient_raw))
        content = (
            f"[dim {c['muted']}]{timestamp_str}[/dim {c['muted']}] "
            f"[bold {c['secondary']}]{sender_display}[/bold {c['secondary']}] [dim]({sender_id_safe})[/dim]{snr_display} "
            f"[bold {c['magenta']}]➔[/bold {c['magenta']}] [bold {c['primary']}]{recipient_display}[/bold {c['primary']}]\n\n"
            f"[bold {c['text']}]{text_safe}[/bold {c['text']}]"
        )
        return Panel(
            Text.from_markup(content),
            title=f"[bold {c['magenta']}]{t('MSG_DM_TITLE', lang)}[/bold {c['magenta']}]",
            title_align="left",
            border_style=c["magenta"],
            box=box.ROUNDED,
            padding=(0, 1),
        )
    else:
        # Broadcast / channel chatter
        if msg.channel_name:
            chan_tag = f"[bold {c['primary']}]#{escape(str(msg.channel_name))}[/bold {c['primary']}]"
        elif msg.channel == 0:
            chan_tag = f"[bold {c['primary']}]#Primary[/bold {c['primary']}]"
        else:
            chan_tag = f"[bold {c['primary']}]#Ch_{escape(str(msg.channel))}[/bold {c['primary']}]"

        formatted = (
            f"[dim {c['muted']}]{timestamp_str}[/dim {c['muted']}] "
            f"{chan_tag} "
            f"[bold {c['secondary']}]{sender_display}[/bold {c['secondary']}]{snr_display} "
            f"[dim {c['muted']}]❯[/dim {c['muted']}] "
            f"[{c['text']}]{text_safe}[/{c['text']}]"
        )
        return Text.from_markup(formatted)
