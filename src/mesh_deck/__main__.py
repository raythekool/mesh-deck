"""Main entrypoint for Mesh-Deck CLI/TUI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from rich.console import Console

from mesh_deck.cli import add_agent_subcommands, resolve_connection_args, run_agent_command
from mesh_deck.core.radio_client import RadioClient
from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.i18n import t
from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL
from mesh_deck.ui.tables import render_nodes_table
from mesh_deck.ui.theme import THEME_COLORS, set_theme

console = Console()
warning_console = Console(stderr=True)


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 capable.

    On Windows the standard streams default to the legacy ANSI code page, so
    any non-ASCII output — the emoji in the argparse description, accented
    Italian strings — raises UnicodeEncodeError before argparse can even print
    its help. Rich re-encodes its own output, but argparse writes directly.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # already detached or not a text stream
            pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
        help="Deprecated: use `mesh-deck scan`",
    )
    parser.add_argument(
        "-n",
        "--nodes",
        action="store_true",
        help="Deprecated: use `mesh-deck nodes`",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch directly into full-screen interactive table with mouse sorting",
    )
    add_agent_subcommands(parser)
    return parser.parse_args(argv)


def _build_history(settings: Any) -> Any:
    """Return a HistoryStore for the real CLI/TUI entrypoints, honoring user settings."""
    if not settings.history_enabled:
        return None
    from mesh_deck.core.history import HistoryStore

    return HistoryStore()


def _warn_deprecated_option(option: str, replacement: str, language: str) -> None:
    """Emit a human warning on stderr without corrupting machine-readable stdout."""
    warning_console.print(
        f"[{THEME_COLORS['warning']}]"
        f"{t('CLI_DEPRECATED_OPTION', language, option=option, replacement=replacement)}[/]"
    )


def main(argv: Sequence[str] | None = None) -> int:
    from mesh_deck.core.settings import Settings

    _force_utf8_stdio()
    settings = Settings.load()
    set_theme(settings.theme)
    args = parse_args(argv)

    if args.command == "mcp":
        from mesh_deck.mcp_server import run_server

        port, timeout = resolve_connection_args(args)
        run_server(port=port, timeout=timeout)
        return 0

    if args.command:
        return run_agent_command(args)

    # If --list requested, scan and print
    if args.list:
        _warn_deprecated_option("--list", "scan", settings.language)
        ports = scan_meshtastic_ports()
        if not ports:
            console.print(f"[{THEME_COLORS['warning']}]{t('CLI_NO_DEVICES_USB', settings.language)}[/]")
            return 0
        console.print(f"[{THEME_COLORS['primary']} bold]{t('CLI_DEVICES_FOUND', settings.language)}[/] {len(ports)}")
        for p in ports:
            console.print(f"  • [bold cyan]{p.port}[/] - [white]{p.hw_name}[/] [dim]({p.description})[/]")
        return 0

    # If --nodes requested, print table and exit
    if args.nodes:
        _warn_deprecated_option("--nodes", "nodes", settings.language)
        port = args.port or settings.default_port
        if not port:
            ports = scan_meshtastic_ports()
            if not ports:
                console.print(f"[{THEME_COLORS['alert']}]{t('CLI_NO_DEVICES', settings.language)}[/]")
                return 1
            port = ports[0].port

        client = RadioClient(history=_build_history(settings))
        if not client.connect(port, blocking=True):
            console.print(f"[{THEME_COLORS['alert']}]{t('CLI_CONNECT_FAILED', settings.language, port=port)}[/]")
            return 1
        nodes = client.store.get_all_nodes(sort_by=settings.default_sort)
        local = client.get_local_node()
        table = render_nodes_table(nodes, local_node_id=local.id if local else None, lang=settings.language)
        console.print(table)
        client.disconnect()
        return 0

    devices = None
    if not args.port:
        devices = scan_meshtastic_ports()
        if not devices:
            console.print(
                f"[{THEME_COLORS['alert']}]{t('CLI_NO_DEVICES', settings.language)}[/] "
                f"{t('CLI_NO_DEVICES_HINT', settings.language)}"
            )
            return 1

    client = RadioClient(history=_build_history(settings))
    repl = MeshDeckREPL(client, console=console, settings=settings)
    try:
        MeshDeckApp(
            repl,
            devices=devices,
            preferred_port=settings.default_port,
            initial_port=args.port,
            open_explorer_on_connect=args.tui,
        ).run()
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
