"""Rich tables and detail panels for Meshtastic nodes and messages.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from typing import Union
from rich import box
from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from mesh_deck.models import MeshMessage, NodeData
from mesh_deck.ui.theme import (
    format_battery,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
)


def render_nodes_table(
    nodes: list[NodeData],
    local_node_id: str | None = None,
) -> Table:
    """Render a tactical Rich table listing all discovered nodes in the mesh.

    Args:
        nodes: List of NodeData objects.
        local_node_id: Node ID (e.g. '!45a466e4') of the local device for highlighting.

    Returns:
        Rich Table configured with rounded borders and cyberpunk color scheme.
    """
    table = Table(
        title=f"[bold #00f3ff]📡 NODI NELLA MESH[/bold #00f3ff] [dim]({len(nodes)} rilevati)[/dim]",
        title_justify="left",
        box=box.ROUNDED,
        header_style="bold #00f3ff",
        border_style="#334155",
        collapse_padding=True,
        pad_edge=False,
        show_lines=False,
    )

    table.add_column("#", justify="right", style="dim", min_width=2, no_wrap=True)
    table.add_column("Nome Nodo", justify="left", min_width=12, no_wrap=True, overflow="ellipsis")
    table.add_column("AKA", justify="center", min_width=5, no_wrap=True)
    table.add_column("ID", justify="center", style="dim", min_width=9, no_wrap=True)
    table.add_column("Hardware", justify="left", min_width=10, overflow="ellipsis", no_wrap=True)
    table.add_column("Ruolo", justify="center", min_width=7, no_wrap=True)
    table.add_column("SNR", justify="right", min_width=8, no_wrap=True)
    table.add_column("Hops", justify="center", min_width=11, no_wrap=True)
    table.add_column("Batteria", justify="center", min_width=11, no_wrap=True)
    table.add_column("Distanza", justify="right", min_width=8, no_wrap=True)
    table.add_column("Ultimo Contatto", justify="right", min_width=8, no_wrap=True)

    for idx, node in enumerate(nodes, start=1):
        is_local = False
        if local_node_id:
            clean_local = local_node_id.strip()
            is_local = (
                node.id == clean_local
                or (node.num is not None and str(node.num) == clean_local)
                or (node.short_name.lower() == clean_local.lower())
            )

        long_name_safe = escape(str(node.long_name or "Unknown"))
        short_name_safe = escape(str(node.short_name or "????"))
        node_id_safe = escape(str(node.id or "!unknown"))
        hw_safe = escape(str(node.hardware or "UNSET"))

        if is_local:
            node_name = f"[bold #00ff66]★ [/bold #00ff66][bold #00f3ff]{long_name_safe}[/bold #00f3ff] [dim](LOCALE)[/dim]"
            aka = f"[bold #00ff66]{short_name_safe}[/bold #00ff66]"
            node_id_str = f"[bold #00f3ff]{node_id_safe}[/bold #00f3ff]"
            row_style = "bold"
        else:
            node_name = f"[bold #f8fafc]{long_name_safe}[/bold #f8fafc]"
            aka = f"[#00f3ff]{short_name_safe}[/#00f3ff]"
            node_id_str = f"[dim]{node_id_safe}[/dim]"
            row_style = None

        hw_display = f"[white]{hw_safe}[/white]"
        role_badge = format_role(node.role)
        snr_display = format_snr(node.snr)
        hops_display = format_hops(node.hops_away)
        batt_display = format_battery(node.battery_level, node.voltage)
        dist_display = format_distance(node.distance_km)
        seen_display = format_time_ago(node.last_heard)

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
) -> Panel:
    """Render an in-depth analytical dossier panel for a single node.

    Includes identity, radio telemetry, GPS location with OpenStreetMap link,
    and environmental sensor readings.

    Args:
        node: NodeData object.
        distance_km: Optional distance in kilometers relative to current position.

    Returns:
        Rich Panel containing organized analytical telemetry grids.
    """
    effective_dist = distance_km if distance_km is not None else node.distance_km

    long_name_safe = escape(str(node.long_name or "Unknown"))
    short_name_safe = escape(str(node.short_name or "????"))
    node_id_safe = escape(str(node.id or "!unknown"))
    hw_safe = escape(str(node.hardware or "UNSET"))

    # Section 1: Identity & Role
    id_grid = Table.grid(expand=True)
    id_grid.add_column(ratio=6)
    id_grid.add_column(ratio=6)

    licensed_str = "[bold #00ff66]Sì (Amateur Radio)[/bold #00ff66]" if node.is_licensed else "[dim]No / ISM[/dim]"
    id_grid.add_row(
        f"[dim #64748b]Nome Completo:[/dim #64748b]   [bold #00ff66]{long_name_safe}[/bold #00ff66]\n"
        f"[dim #64748b]Alias (AKA):[/dim #64748b]      [bold #00f3ff]{short_name_safe}[/bold #00f3ff]\n"
        f"[dim #64748b]Node ID:[/dim #64748b]          [white]{node_id_safe}[/white] [dim](Dec: {node.num or '--'})[/dim]",
        f"[dim #64748b]Modello HW:[/dim #64748b]       [white]{hw_safe}[/white]\n"
        f"[dim #64748b]Ruolo Dispositivo:[/dim #64748b] {format_role(node.role)}\n"
        f"[dim #64748b]Licenza Radio:[/dim #64748b]    {licensed_str}",
    )

    # Section 2: Radio Metrics & Propagation
    last_heard_full = (
        node.last_heard.strftime("%Y-%m-%d %H:%M:%S")
        if node.last_heard
        else "N/A"
    )
    last_heard_display = f"{format_time_ago(node.last_heard)} [dim]({last_heard_full})[/dim]"

    ch_util_str = f"{node.channel_utilization:.1f}%" if node.channel_utilization is not None else "[dim]--[/dim]"
    air_util_str = f"{node.air_util_tx:.2f}%" if node.air_util_tx is not None else "[dim]--[/dim]"

    radio_grid = Table.grid(expand=True)
    radio_grid.add_column(ratio=6)
    radio_grid.add_column(ratio=6)

    radio_grid.add_row(
        f"[dim #64748b]Segnale (SNR):[/dim #64748b]    {format_snr(node.snr)}\n"
        f"[dim #64748b]Hops Away:[/dim #64748b]        {format_hops(node.hops_away)}\n"
        f"[dim #64748b]Ultimo Contatto:[/dim #64748b]  {last_heard_display}",
        f"[dim #64748b]Ch. Utilization:[/dim #64748b]  [white]{ch_util_str}[/white]\n"
        f"[dim #64748b]Air Util TX:[/dim #64748b]      [white]{air_util_str}[/white]\n"
        f"[dim #64748b]Preset Modem:[/dim #64748b]     [white]{node.modem_preset or 'LONG_FAST'}[/white]",
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
        f"[dim #64748b]Batteria:[/dim #64748b]         {batt_str}\n"
        f"[dim #64748b]Tensione Cella:[/dim #64748b]   [white]{volt_str}[/white]",
        f"[dim #64748b]Temperatura:[/dim #64748b]      [white]{temp_str}[/white]\n"
        f"[dim #64748b]Umidità Relativa:[/dim #64748b] [white]{hum_str}[/white] [dim #64748b]| Pressione:[/dim #64748b] [white]{press_str}[/white]",
    )

    # Section 4: Geographic Position & OpenStreetMap
    geo_grid = Table.grid(expand=True)
    geo_grid.add_column(ratio=6)
    geo_grid.add_column(ratio=6)

    if node.has_coords:
        coords_val = f"[bold #00f3ff]{node.latitude:.5f}, {node.longitude:.5f}[/bold #00f3ff]"
        alt_val = f"{node.altitude:.0f} m s.l.m." if node.altitude is not None else "[dim]--[/dim]"
        osm_link = (
            f"[link={node.osm_url}][bold #00ff66]Apri mappa ↗[/bold #00ff66][/link] "
            f"[dim #64748b]({node.osm_url})[/dim #64748b]"
        )
    else:
        coords_val = "[dim]Non disponibili / GPS assente[/dim]"
        alt_val = "[dim]--[/dim]"
        osm_link = "[dim]Nessuna coordinata per il rendering mappa[/dim]"

    dist_str = format_distance(effective_dist)

    geo_grid.add_row(
        f"[dim #64748b]Coordinate GPS:[/dim #64748b]   {coords_val}\n"
        f"[dim #64748b]Altitudine:[/dim #64748b]       [white]{alt_val}[/white]\n"
        f"[dim #64748b]Distanza Stima:[/dim #64748b]   [bold #ffb800]{dist_str}[/bold #ffb800]",
        f"[dim #64748b]OpenStreetMap:[/dim #64748b]\n{osm_link}",
    )

    # Section 5: Security / Public Key (if available)
    pubkey_str = (
        f"[dim #64748b]{escape(str(node.public_key))}[/dim #64748b]"
        if node.public_key
        else "[dim]Non trasmessa o crittografia standard[/dim]"
    )

    elements = [
        Text.from_markup("[bold #00f3ff]◈ IDENTITÀ & HARDWARE[/bold #00f3ff]"),
        id_grid,
        Rule(style="#334155"),
        Text.from_markup("[bold #00f3ff]⚡ TELEMETRIA RADIO & PROPAGAZIONE[/bold #00f3ff]"),
        radio_grid,
        Rule(style="#334155"),
        Text.from_markup("[bold #00f3ff]🔋 ENERGIA & SENSORI AMBIENTALI[/bold #00f3ff]"),
        power_grid,
        Rule(style="#334155"),
        Text.from_markup("[bold #00f3ff]📍 POSIZIONE GEOGRAFICA[/bold #00f3ff]"),
        geo_grid,
        Rule(style="#334155"),
        Text.from_markup(f"[dim #64748b]Chiave Pubblica PKI:[/dim #64748b] {pubkey_str}"),
    ]

    return Panel(
        Group(*elements),
        title=f"[bold #00f3ff]◈ SCHEDA ANALITICA // {short_name_safe} ({node_id_safe})[/bold #00f3ff]",
        title_align="left",
        subtitle="[dim #64748b]Meshtastic Node Dossier[/dim #64748b]",
        subtitle_align="right",
        border_style="#00f3ff",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def render_message(
    msg: MeshMessage,
    as_panel: bool | None = None,
) -> Union[Text, Panel]:
    """Format an incoming or transmitted mesh message.

    Direct messages (DM) are styled inside a tactical alert Panel by default,
    while broadcast messages render as sleek, single-line terminal logs.

    Args:
        msg: MeshMessage object.
        as_panel: If True, forces Panel output. If None, defaults to True for DMs.

    Returns:
        Rich Text or Panel object.
    """
    timestamp_str = msg.timestamp.strftime("[%H:%M:%S]") if msg.timestamp else "[--:--:--]"
    sender_raw = msg.sender_name or msg.sender_short_name or msg.sender_id or "Sconosciuto"
    sender_display = escape(str(sender_raw))
    sender_id_safe = escape(str(msg.sender_id or "!unknown"))
    snr_display = f" [{format_snr(msg.snr)}]" if msg.snr is not None else ""
    text_safe = escape(str(msg.text or ""))

    should_render_panel = msg.is_direct if as_panel is None else as_panel

    if should_render_panel:
        recipient_raw = msg.recipient_name or msg.recipient_id or "^all"
        recipient_display = escape(str(recipient_raw))
        content = (
            f"[dim #64748b]{timestamp_str}[/dim #64748b] "
            f"[bold #00ff66]{sender_display}[/bold #00ff66] [dim]({sender_id_safe})[/dim]{snr_display} "
            f"[bold #ff007f]➔[/bold #ff007f] [bold #00f3ff]{recipient_display}[/bold #00f3ff]\n\n"
            f"[bold #f8fafc]{text_safe}[/bold #f8fafc]"
        )
        return Panel(
            Text.from_markup(content),
            title="[bold #ff007f]🔒 MESSAGGIO DIRETTO PRIVATO // DM[/bold #ff007f]",
            title_align="left",
            border_style="#ff007f",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    else:
        # Broadcast / channel chatter
        if msg.channel_name:
            chan_tag = f"[bold #00f3ff]#{escape(str(msg.channel_name))}[/bold #00f3ff]"
        elif msg.channel == 0:
            chan_tag = "[bold #00f3ff]#Primary[/bold #00f3ff]"
        else:
            chan_tag = f"[bold #00f3ff]#Ch_{escape(str(msg.channel))}[/bold #00f3ff]"

        formatted = (
            f"[dim #64748b]{timestamp_str}[/dim #64748b] "
            f"{chan_tag} "
            f"[bold #00ff66]{sender_display}[/bold #00ff66]{snr_display} "
            f"[dim #64748b]❯[/dim #64748b] "
            f"[#f8fafc]{text_safe}[/#f8fafc]"
        )
        return Text.from_markup(formatted)
