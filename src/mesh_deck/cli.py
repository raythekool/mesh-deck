"""Command-line adapter for human and agent-oriented Mesh-Deck usage."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from rich.console import Console
from rich.table import Table

from mesh_deck.agent import AgentService, AgentServiceError

EXIT_OK = 0
EXIT_USAGE = 2


def add_agent_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="List detected Meshtastic devices")
    _add_output_argument(scan)

    for name, help_text in (
        ("info", "Show connected radio information"),
        ("channels", "List configured radio channels without secret keys"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        _add_connection_arguments(command)
        _add_output_argument(command)

    nodes = subparsers.add_parser("nodes", help="List nodes in the mesh")
    _add_connection_arguments(nodes)
    _add_output_argument(nodes)
    nodes.add_argument(
        "--sort",
        choices=("last_heard", "snr", "hops", "name"),
        default="last_heard",
    )
    nodes.add_argument("--active", action="store_true", help="Only include recently active nodes")

    node = subparsers.add_parser("node", help="Show one node by ID, number, alias, or name")
    node.add_argument("query")
    _add_connection_arguments(node)
    _add_output_argument(node)

    neighbors = subparsers.add_parser("neighbors", help="Show NeighborInfo tables heard from the mesh")
    neighbors.add_argument("query", nargs="?", help="Limit to the table broadcast by one node")
    _add_connection_arguments(neighbors)
    _add_output_argument(neighbors)

    trace = subparsers.add_parser("trace", help="Trace the hop path towards a node")
    trace.add_argument("target")
    trace.add_argument("--hop-limit", type=int, default=7)
    _add_connection_arguments(trace)
    _add_output_argument(trace)

    send = subparsers.add_parser("send", help="Preview or send a broadcast message")
    send.add_argument("text")
    send.add_argument("--channel", type=int, default=0)
    send.add_argument("--confirm", action="store_true", help="Actually transmit the message")
    _add_connection_arguments(send)
    _add_output_argument(send)

    dm = subparsers.add_parser("dm", help="Preview or send a direct message")
    dm.add_argument("target")
    dm.add_argument("text")
    dm.add_argument("--confirm", action="store_true", help="Actually transmit the message")
    _add_connection_arguments(dm)
    _add_output_argument(dm)

    mcp = subparsers.add_parser("mcp", help="Run the local MCP server over stdio")
    _add_connection_arguments(mcp)

def resolve_connection_args(args: argparse.Namespace) -> tuple[str | None, int]:
    """Merge subcommand `--port`/`--timeout` with the legacy top-level `--port`.

    argparse subparsers silently overwrite a parent parser's attribute with
    their own default when both define the same `dest` (e.g. `mesh-deck
    --port /dev/ttyACM0 nodes` would otherwise lose the port). Subcommand
    connection arguments are stored under distinct `agent_*` attributes so a
    port supplied before OR after the subcommand is always honored.
    """
    port = getattr(args, "agent_port", None) or getattr(args, "port", None)
    timeout = getattr(args, "agent_timeout", None) or 30
    return port, timeout


def run_agent_command(
    args: argparse.Namespace,
    *,
    service: AgentService | None = None,
    stdout: Console | None = None,
    stderr: Console | None = None,
) -> int:
    owned_service = service is None
    active_service = service or AgentService()
    out = stdout or Console()
    err = stderr or Console(stderr=True)
    command = args.command
    port, timeout = resolve_connection_args(args)

    try:
        if command == "scan":
            data = active_service.scan_devices()
        elif command == "info":
            data = active_service.get_radio_info(port, timeout)
        elif command == "nodes":
            data = active_service.list_nodes(
                port=port,
                timeout=timeout,
                sort_by=args.sort,
                active_only=args.active,
            )
        elif command == "node":
            data = active_service.get_node(args.query, port=port, timeout=timeout)
        elif command == "channels":
            data = active_service.list_channels(port=port, timeout=timeout)
        elif command == "neighbors":
            data = active_service.list_neighbors(args.query, port=port, timeout=timeout)
        elif command == "trace":
            data = active_service.trace_route(
                args.target,
                hop_limit=args.hop_limit,
                port=port,
                timeout=timeout,
            )
        elif command == "send":
            data = active_service.send_broadcast(
                args.text,
                channel_index=args.channel,
                confirm=args.confirm,
                port=port,
                timeout=timeout,
            )
        elif command == "dm":
            data = active_service.send_direct_message(
                args.target,
                args.text,
                confirm=args.confirm,
                port=port,
                timeout=timeout,
            )
        else:
            raise AgentServiceError(
                "invalid_input",
                f"Unsupported command: {command}.",
                exit_code=EXIT_USAGE,
            )

        if args.output == "json":
            _write_json(out, {"ok": True, "command": command, "data": data})
        else:
            _render_human(command, data, out)
        return EXIT_OK
    except AgentServiceError as exc:
        envelope = {"ok": False, "command": command, "error": exc.to_dict()}
        if getattr(args, "output", "human") == "json":
            _write_json(out, envelope)
        else:
            err.print(f"[bold red]{exc.code}:[/] {exc.message}")
            if exc.details:
                err.print_json(json.dumps(exc.details))
        return exc.exit_code
    except Exception as exc:
        envelope = {
            "ok": False,
            "command": command,
            "error": {
                "code": "internal_error",
                "message": "Mesh-Deck could not complete the command.",
                "details": {"reason": str(exc)},
            },
        }
        if getattr(args, "output", "human") == "json":
            _write_json(out, envelope)
        else:
            err.print(f"[bold red]internal_error:[/] {envelope['error']['message']}")
            err.print_json(json.dumps(envelope["error"]["details"]))
        return 1
    finally:
        if owned_service:
            active_service.close()


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--port",
        dest="agent_port",
        help="Meshtastic serial port; defaults to settings or auto-detect",
    )
    parser.add_argument(
        "--timeout",
        dest="agent_timeout",
        type=int,
        default=30,
        help="Connection timeout in seconds",
    )


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        choices=("human", "json"),
        default="human",
        help="Output format",
    )


def _write_json(console: Console, payload: dict[str, Any]) -> None:
    console.file.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    console.file.flush()


def _render_human(command: str, data: dict[str, Any], console: Console) -> None:
    if command == "scan":
        rows = data["devices"]
        _render_rows(console, "Meshtastic devices", rows)
    elif command == "nodes":
        _render_rows(console, f"Mesh nodes ({data['count']})", data["nodes"])
    elif command == "channels":
        _render_rows(console, f"Radio channels ({data['count']})", data["channels"])
    elif command == "node":
        _render_mapping(console, "Node details", data["node"])
    elif command == "neighbors":
        if not data["reports"]:
            console.print("[dim]No neighbor tables received yet[/]")
        for report in data["reports"]:
            _render_rows(console, f"Neighbors of {report['node_id']}", report["neighbors"])
    elif command == "trace":
        if not data["completed"]:
            console.print(f"[dim]No traceroute reply from {data['target']['id']}[/]")
        else:
            _render_mapping(console, f"Traceroute to {data['target']['id']}", data["route"])
    elif command == "info":
        _render_mapping(console, "Radio information", data)
    elif command in {"send", "dm"}:
        status = "SENT" if data["sent"] else "PREVIEW - not sent"
        _render_mapping(console, status, data)
    else:
        console.print_json(json.dumps(data))


def _render_rows(console: Console, title: str, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        console.print(f"[dim]{title}: no results[/]")
        return
    columns = list(rows[0].keys())
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(row.get(column, "")) for column in columns))
    console.print(table)


def _render_mapping(console: Console, title: str, data: dict[str, Any]) -> None:
    table = Table(title=title, show_header=False)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            rendered = str(value)
        table.add_row(key, rendered)
    console.print(table)
