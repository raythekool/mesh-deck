"""Application services shared by machine-readable CLI and MCP adapters."""

from __future__ import annotations

from collections.abc import Callable
import threading
from typing import Any

from mesh_deck.core.events import DeviceConnectionInfo, NodeData
from mesh_deck.core.history import HistoryStore
from mesh_deck.core.radio_client import RadioClient
from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.core.settings import Settings


class AgentServiceError(Exception):
    """An actionable error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AgentService:
    """Hardware-facing operations with JSON-safe results and explicit failures."""

    def __init__(
        self,
        client: RadioClient | None = None,
        settings: Settings | None = None,
        scanner: Callable[[], list[DeviceConnectionInfo]] = scan_meshtastic_ports,
        history: HistoryStore | None = None,
    ) -> None:
        self.settings = settings or Settings.load()
        if client is not None:
            self.client = client
        else:
            use_history = history if history is not None else (
                HistoryStore() if self.settings.history_enabled else None
            )
            self.client = RadioClient(history=use_history)
        self._scanner = scanner
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            self.client.disconnect()

    def __enter__(self) -> AgentService:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def scan_devices(self) -> dict[str, Any]:
        with self._lock:
            devices = [device.to_dict() for device in self._scanner()]
        return {"devices": devices, "count": len(devices)}

    def ensure_connected(self, port: str | None = None, timeout: int = 30) -> str:
        with self._lock:
            if timeout <= 0:
                raise AgentServiceError(
                    "invalid_input",
                    "Connection timeout must be greater than zero.",
                    exit_code=2,
                    details={"timeout": timeout},
                )

            target_port = port or self.settings.default_port
            if not target_port:
                devices = self._scanner()
                if not devices:
                    raise AgentServiceError(
                        "device_not_found",
                        "No Meshtastic serial device was detected.",
                        exit_code=4,
                    )
                target_port = devices[0].port

            if self.client.is_connected and self.client.port == target_port:
                return target_port

            try:
                connected = self.client.connect(target_port, blocking=True, timeout=timeout)
            except Exception as exc:
                raise AgentServiceError(
                    "connection_failed",
                    f"Could not connect to Meshtastic device on {target_port}.",
                    exit_code=5,
                    details={"port": target_port, "reason": str(exc)},
                ) from exc

            if not connected:
                raise AgentServiceError(
                    "connection_failed",
                    f"Could not connect to Meshtastic device on {target_port}.",
                    exit_code=5,
                    details={"port": target_port},
                )
            return target_port

    def get_radio_info(self, port: str | None = None, timeout: int = 30) -> dict[str, Any]:
        with self._lock:
            connected_port = self.ensure_connected(port, timeout)
            raw_info = self.client.get_my_info() or {}
            local = self.client.get_local_node()
            return {
                "connection": {
                    "connected": self.client.is_connected,
                    "port": connected_port,
                },
                "local_node": local.to_dict() if local else None,
                "radio": self._safe_radio_info(raw_info),
                "channel_count": len(self.client.get_channels()),
            }

    def list_nodes(
        self,
        *,
        port: str | None = None,
        timeout: int = 30,
        sort_by: str = "last_heard",
        active_only: bool = False,
    ) -> dict[str, Any]:
        if sort_by not in {"last_heard", "snr", "hops", "name"}:
            raise AgentServiceError(
                "invalid_input",
                f"Unsupported node sort: {sort_by}.",
                exit_code=2,
                details={"allowed": ["last_heard", "snr", "hops", "name"]},
            )
        with self._lock:
            self.ensure_connected(port, timeout)
            nodes = self.client.store.get_all_nodes(
                sort_by=sort_by,
                active_only=active_only,
            )
            return {
                "nodes": [node.to_dict() for node in nodes],
                "count": len(nodes),
                "sort": sort_by,
                "active_only": active_only,
            }

    def get_node(
        self,
        query: str,
        *,
        port: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            raise AgentServiceError(
                "invalid_input",
                "A node ID, number, alias, or name is required.",
                exit_code=2,
            )
        with self._lock:
            self.ensure_connected(port, timeout)
            node = self.client.store.get_node(normalized_query)
            if node is None:
                raise AgentServiceError(
                    "node_not_found",
                    f"No node matched {normalized_query!r}.",
                    exit_code=3,
                    details={"query": normalized_query},
                )

            data = node.to_dict()
            local = self.client.get_local_node()
            if local and local.id != node.id:
                data["distance_km"] = self.client.store.calculate_distance(local.id, node.id)
            return {"node": data}

    def list_channels(
        self,
        *,
        port: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        with self._lock:
            self.ensure_connected(port, timeout)
            channels = [self._safe_channel(channel) for channel in self.client.get_channels()]
            return {"channels": channels, "count": len(channels)}

    def send_broadcast(
        self,
        text: str,
        *,
        channel_index: int = 0,
        confirm: bool = False,
        port: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        message = self._validate_message(text)
        if channel_index < 0:
            raise AgentServiceError(
                "invalid_input",
                "Channel index must be zero or greater.",
                exit_code=2,
                details={"channel_index": channel_index},
            )
        preview = {
            "operation": "broadcast",
            "text": message,
            "channel_index": channel_index,
        }
        if not confirm:
            return {"sent": False, "preview": True, **preview}

        with self._lock:
            self.ensure_connected(port, timeout)
            try:
                self.client.send_broadcast(message, channel_index=channel_index)
            except Exception as exc:
                raise AgentServiceError(
                    "send_failed",
                    "The broadcast message could not be sent.",
                    exit_code=6,
                    details={"reason": str(exc)},
                ) from exc
        return {"sent": True, "preview": False, **preview}

    def send_direct_message(
        self,
        target: str,
        text: str,
        *,
        confirm: bool = False,
        port: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        normalized_target = target.strip()
        if not normalized_target:
            raise AgentServiceError(
                "invalid_input",
                "A direct-message target is required.",
                exit_code=2,
            )
        message = self._validate_message(text)
        with self._lock:
            self.ensure_connected(port, timeout)
            node = self.client.store.get_node(normalized_target)
            if node is None:
                raise AgentServiceError(
                    "node_not_found",
                    f"No node matched {normalized_target!r}.",
                    exit_code=3,
                    details={"query": normalized_target},
                )

            preview = {
                "operation": "direct_message",
                "target": self._node_identity(node),
                "text": message,
            }
            if not confirm:
                return {"sent": False, "preview": True, **preview}

            try:
                self.client.send_dm(node.id, message)
            except Exception as exc:
                raise AgentServiceError(
                    "send_failed",
                    f"The direct message to {node.id} could not be sent.",
                    exit_code=6,
                    details={"target": node.id, "reason": str(exc)},
                ) from exc
            return {"sent": True, "preview": False, **preview}

    @staticmethod
    def _validate_message(text: str) -> str:
        message = text.strip()
        if not message:
            raise AgentServiceError(
                "invalid_input",
                "Message text must not be empty.",
                exit_code=2,
            )
        return message

    @staticmethod
    def _node_identity(node: NodeData) -> dict[str, Any]:
        return {
            "id": node.id,
            "num": node.num,
            "long_name": node.long_name,
            "short_name": node.short_name,
        }

    @staticmethod
    def _safe_radio_info(info: dict[str, Any]) -> dict[str, Any]:
        aliases = {
            "my_node_num": ("my_node_num", "myNodeNum"),
            "firmware_version": ("firmware_version", "firmwareVersion"),
            "region": ("region",),
            "modem_preset": ("modem_preset", "modemPreset"),
        }
        safe: dict[str, Any] = {}
        for output_key, input_keys in aliases.items():
            for input_key in input_keys:
                if input_key in info:
                    safe[output_key] = info[input_key]
                    break
        return safe

    @staticmethod
    def _safe_channel(channel: dict[str, Any]) -> dict[str, Any]:
        raw = channel.get("raw")
        raw_dict = raw if isinstance(raw, dict) else {}
        settings = raw_dict.get("settings")
        settings_dict = settings if isinstance(settings, dict) else {}
        psk = settings_dict.get("psk")
        return {
            "index": channel.get("index"),
            "name": channel.get("name") or settings_dict.get("name") or "",
            "role": channel.get("role"),
            "uplink_enabled": channel.get(
                "uplink_enabled",
                raw_dict.get("uplinkEnabled", False),
            ),
            "downlink_enabled": channel.get(
                "downlink_enabled",
                raw_dict.get("downlinkEnabled", False),
            ),
            "has_psk": channel.get("has_psk", bool(psk)),
        }
