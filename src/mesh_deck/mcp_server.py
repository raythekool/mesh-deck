"""Local Model Context Protocol server for Mesh-Deck."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mesh_deck.agent import AgentService, AgentServiceError


def create_server(
    service: AgentService,
    *,
    default_port: str | None = None,
    default_timeout: int = 30,
) -> MCPServer:
    """Create an MCP server backed by one persistent, serialized radio service."""
    server = MCPServer(
        "mesh-deck",
        instructions=(
            "Inspect and communicate with a locally attached Meshtastic radio. "
            "Message tools only transmit when confirm=true."
        ),
    )

    def call(method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        operation = getattr(service, method)
        try:
            return operation(*args, **kwargs)
        except AgentServiceError as exc:
            raise ToolError(json.dumps(exc.to_dict(), ensure_ascii=False)) from exc

    @server.tool()
    def scan_devices() -> dict[str, Any]:
        """List locally detected Meshtastic serial devices."""
        return call("scan_devices")

    @server.tool()
    def get_radio_info(port: str | None = None) -> dict[str, Any]:
        """Get connection, local node, radio, and channel summary information."""
        return call(
            "get_radio_info",
            port or default_port,
            default_timeout,
        )

    @server.tool()
    def list_nodes(
        sort_by: str = "last_heard",
        active_only: bool = False,
        port: str | None = None,
    ) -> dict[str, Any]:
        """List mesh nodes with telemetry using a stable structured response."""
        return call(
            "list_nodes",
            port=port or default_port,
            timeout=default_timeout,
            sort_by=sort_by,
            active_only=active_only,
        )

    @server.tool()
    def get_node(query: str, port: str | None = None) -> dict[str, Any]:
        """Find one node by ID, decimal number, short name, or long name."""
        return call(
            "get_node",
            query,
            port=port or default_port,
            timeout=default_timeout,
        )

    @server.tool()
    def list_channels(port: str | None = None) -> dict[str, Any]:
        """List channel metadata and encryption status without exposing keys."""
        return call(
            "list_channels",
            port=port or default_port,
            timeout=default_timeout,
        )

    @server.tool()
    def send_broadcast(
        text: str,
        channel_index: int = 0,
        confirm: bool = False,
        port: str | None = None,
    ) -> dict[str, Any]:
        """Preview a broadcast, or transmit it only when confirm is true."""
        return call(
            "send_broadcast",
            text,
            channel_index=channel_index,
            confirm=confirm,
            port=port or default_port,
            timeout=default_timeout,
        )

    @server.tool()
    def send_direct_message(
        target: str,
        text: str,
        confirm: bool = False,
        port: str | None = None,
    ) -> dict[str, Any]:
        """Preview a direct message, or transmit it only when confirm is true."""
        return call(
            "send_direct_message",
            target,
            text,
            confirm=confirm,
            port=port or default_port,
            timeout=default_timeout,
        )

    return server


def run_server(port: str | None = None, timeout: int = 30) -> None:
    """Run the Mesh-Deck MCP server over stdio until the client disconnects."""
    service = AgentService()
    server = create_server(service, default_port=port, default_timeout=timeout)
    try:
        server.run(transport="stdio")
    finally:
        service.close()
