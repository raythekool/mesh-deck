"""Main entrypoint for Mesh-Deck CLI/TUI."""

from __future__ import annotations

import argparse
import sys
from rich.console import Console

from mesh_deck.core.radio_client import RadioClient
from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL
from mesh_deck.ui.tables import render_nodes_table
from mesh_deck.ui.theme import THEME_COLORS

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mesh-deck",
        description="📡 Mesh-Deck: Hermes-style interactive TUI/CLI for Meshtastic devices",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        help="Specific serial port to connect to (e.g. /dev/ttyACM0)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List detected Meshtastic serial ports and exit",
    )
    parser.add_argument(
        "-n",
        "--nodes",
        action="store_true",
        help="Print the nodes table and exit (non-interactive)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch directly into full-screen interactive table with mouse sorting",
    )
    return parser.parse_args()


def main() -> None:
    from mesh_deck.core.settings import Settings

    settings = Settings.load()
    args = parse_args()

    # If --list requested, scan and print
    if args.list:
        ports = scan_meshtastic_ports()
        if not ports:
            console.print(f"[{THEME_COLORS['warning']}]Nessun dispositivo Meshtastic rilevato sulle porte USB.[/]")
            sys.exit(0)
        console.print(f"[{THEME_COLORS['primary']} bold]📡 Dispositivi Meshtastic rilevati:[/] {len(ports)}")
        for p in ports:
            console.print(f"  • [bold cyan]{p.port}[/] - [white]{p.hw_name}[/] [dim]({p.description})[/]")
        sys.exit(0)

    # If --nodes requested, print table and exit
    if args.nodes:
        port = args.port or settings.default_port
        if not port:
            ports = scan_meshtastic_ports()
            if not ports:
                console.print(f"[{THEME_COLORS['alert']}]Nessun dispositivo Meshtastic rilevato.[/]")
                sys.exit(1)
            port = ports[0].port

        client = RadioClient()
        if not client.connect(port, blocking=True):
            console.print(f"[{THEME_COLORS['alert']}]Impossibile connettersi al dispositivo su {port}.[/]")
            sys.exit(1)
        nodes = client.store.get_all_nodes(sort_by=settings.default_sort)
        local = client.get_local_node()
        table = render_nodes_table(nodes, local_node_id=local.id if local else None)
        console.print(table)
        client.disconnect()
        sys.exit(0)

    devices = None
    if not args.port:
        devices = scan_meshtastic_ports()
        if not devices:
            console.print(
                f"[{THEME_COLORS['alert']}]Nessun dispositivo Meshtastic rilevato.[/] "
                f"Verifica il cavo USB o specifica manualmente la porta con [bold]--port /dev/...[/bold]"
            )
            sys.exit(1)

    client = RadioClient()
    repl = MeshDeckREPL(client, console=console)
    try:
        MeshDeckApp(
            repl,
            devices=devices,
            preferred_port=settings.default_port,
            initial_port=args.port,
            open_explorer_on_connect=args.tui or settings.ui_mode == "tui",
        ).run()
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
