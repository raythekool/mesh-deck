"""RadioClient encapsulating meshtastic SerialInterface and pubsub event routing."""

from __future__ import annotations

import inspect
import logging
import threading
from datetime import datetime
from typing import Any, Callable

from google.protobuf.json_format import MessageToDict
from meshtastic import channel_pb2
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

from mesh_deck.core.events import MeshMessage, NodeData
from mesh_deck.core.node_store import NodeStore

logger = logging.getLogger(__name__)


class RadioClient:
    """High-level client for Meshtastic serial connection, event dispatching, and state tracking."""

    def __init__(self, node_store: NodeStore | None = None) -> None:
        self._node_store = node_store if node_store is not None else NodeStore()
        self._interface: SerialInterface | None = None
        self._port: str | None = None
        self._is_connected: bool = False
        self._lock = threading.RLock()
        self._connect_thread: threading.Thread | None = None

        # Registered user callbacks
        self._message_callbacks: list[Callable[[MeshMessage], Any]] = []
        self._node_updated_callbacks: list[Callable[[NodeData], Any]] = []
        self._telemetry_callbacks: list[Callable[..., Any]] = []
        self._connection_callbacks: list[Callable[[bool, str | None], Any]] = []

        # Pubsub subscription flags
        self._subscribed = False

    @property
    def node_store(self) -> NodeStore:
        """Underlying NodeStore instance."""
        return self._node_store

    @property
    def store(self) -> NodeStore:
        """Alias for node_store."""
        return self._node_store

    @property
    def port(self) -> str | None:
        """Path to currently connected serial port."""
        with self._lock:
            return self._port

    @property
    def is_connected(self) -> bool:
        """Whether client is currently connected to a Meshtastic device."""
        with self._lock:
            if not self._is_connected or self._interface is None:
                return False
            # If interface exposes isConnected threading.Event, check it
            if hasattr(self._interface, "isConnected"):
                event = getattr(self._interface, "isConnected")
                if hasattr(event, "is_set"):
                    return event.is_set()
            return True

    @property
    def interface(self) -> SerialInterface | None:
        """Underlying SerialInterface instance, or None if disconnected."""
        with self._lock:
            return self._interface

    def on_message_received(self, callback: Callable[[MeshMessage], Any]) -> None:
        """Register a callback for incoming text and direct messages."""
        with self._lock:
            if callback not in self._message_callbacks:
                self._message_callbacks.append(callback)

    def on_node_updated(self, callback: Callable[[NodeData], Any]) -> None:
        """Register a callback for node updates or newly discovered nodes."""
        with self._lock:
            if callback not in self._node_updated_callbacks:
                self._node_updated_callbacks.append(callback)

    def on_telemetry_received(self, callback: Callable[..., Any]) -> None:
        """Register a callback for telemetry packets (deviceMetrics, environmentMetrics)."""
        with self._lock:
            if callback not in self._telemetry_callbacks:
                self._telemetry_callbacks.append(callback)

    def on_connection_change(self, callback: Callable[[bool, str | None], Any]) -> None:
        """Register a callback for connection state changes (connected: bool, port: str|None)."""
        with self._lock:
            if callback not in self._connection_callbacks:
                self._connection_callbacks.append(callback)

    def connect(self, port: str, blocking: bool = False, timeout: int = 30) -> bool:
        """Connect to a Meshtastic device on the specified serial port.

        Args:
            port: Serial port path (e.g. '/dev/ttyACM0').
            blocking: If False, performs connection in background thread.
            timeout: Timeout in seconds for initial node db handshake.

        Returns:
            True if connected (or connection initiated when non-blocking), False on error.
        """
        self._ensure_pubsub_subscribed()

        if blocking:
            try:
                self._do_connect(port, timeout)
                return self.is_connected
            except Exception as exc:
                logger.error("Failed to connect to %s: %s", port, exc)
                return False
        else:
            with self._lock:
                # If a previous connection thread is running, let it finish or replace
                self._connect_thread = threading.Thread(
                    target=self._do_connect,
                    args=(port, timeout),
                    name=f"RadioClient-Connect-{port}",
                    daemon=True,
                )
                self._connect_thread.start()
            return True

    def _do_connect(self, port: str, timeout: int) -> None:
        """Internal worker executing serial interface connection and handshake."""
        with self._lock:
            if self._is_connected and self._port == port:
                logger.info("Already connected to %s", port)
                return
            if self._interface is not None:
                self._close_interface()

        logger.info("Opening Meshtastic SerialInterface on %s (timeout=%ds)...", port, timeout)
        try:
            # SerialInterface automatically starts reading and downloads node DB
            iface = SerialInterface(devPath=port, connectNow=True, timeout=timeout)

            with self._lock:
                self._interface = iface
                self._port = port
                self._is_connected = True

                # Determine local node number / ID
                if iface.myInfo and iface.myInfo.my_node_num:
                    local_num = iface.myInfo.my_node_num
                    self._node_store.set_local_node_id(local_num)

                # Populate NodeStore from initial nodes cache
                raw_nodes = getattr(iface, "nodes", {}) or {}
                for n_dict in raw_nodes.values():
                    if isinstance(n_dict, dict):
                        self._node_store.update_from_node_dict(n_dict)

                raw_nodes_by_num = getattr(iface, "nodesByNum", {}) or {}
                for n_dict in raw_nodes_by_num.values():
                    if isinstance(n_dict, dict):
                        self._node_store.update_from_node_dict(n_dict)

            logger.info("Connected successfully to %s. Nodes known: %d", port, len(self._node_store))
            self._notify_connection_change(True, port)

        except Exception as exc:
            logger.error("Failed to connect to %s: %s", port, exc)
            with self._lock:
                self._is_connected = False
                self._port = None
                self._interface = None
            self._notify_connection_change(False, port)
            raise

    def disconnect(self) -> None:
        """Disconnect from the current serial port cleanly."""
        old_port = None
        with self._lock:
            if not self._is_connected and self._interface is None:
                return
            old_port = self._port
            self._close_interface()

        logger.info("Disconnected from %s", old_port)
        self._notify_connection_change(False, old_port)

    def _close_interface(self) -> None:
        """Helper to cleanly close SerialInterface."""
        self._is_connected = False
        iface = self._interface
        self._interface = None
        self._port = None

        if iface is not None:
            try:
                iface.close()
            except Exception as exc:
                logger.debug("Exception while closing interface: %s", exc)

    def _ensure_pubsub_subscribed(self) -> None:
        """Subscribe internal handlers to Meshtastic pypubsub topics."""
        with self._lock:
            if self._subscribed:
                return
            pub.subscribe(self._on_pubsub_text, "meshtastic.receive.text")
            pub.subscribe(self._on_pubsub_telemetry, "meshtastic.receive.telemetry")
            pub.subscribe(self._on_pubsub_position, "meshtastic.receive.position")
            pub.subscribe(self._on_pubsub_node_updated, "meshtastic.node.updated")
            pub.subscribe(self._on_pubsub_connection_lost, "meshtastic.connection.lost")
            self._subscribed = True

    def _on_pubsub_text(self, packet: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle incoming text message packet from pubsub."""
        # Avoid crosstalk from other interfaces
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            # 1. Update sender node in store
            self._node_store.update_from_packet(packet)

            # 2. Extract sender
            from_num = packet.get("from", 0)
            from_id = packet.get("fromId")
            if not from_id and from_num:
                from_id = f"!{from_num:08x}"
            from_id = from_id or "!unknown"

            sender_node = self._node_store.get_node(from_id)
            sender_name = sender_node.display_name if sender_node else from_id
            sender_short = sender_node.short_name if sender_node else (from_id[-4:] if len(from_id) >= 4 else from_id)

            # 3. Extract receiver
            to_num = packet.get("to", 0)
            to_id = packet.get("toId")
            is_dm = bool(to_num != 0xFFFFFFFF and to_id != "^all")

            if not to_id:
                if is_dm and to_num:
                    to_id = f"!{to_num:08x}"
                else:
                    to_id = "^all"

            recipient_node = self._node_store.get_node(to_id) if is_dm else None
            recipient_name = recipient_node.display_name if recipient_node else ("Direct" if is_dm else "Broadcast")

            # 4. Extract text payload
            decoded = packet.get("decoded") or {}
            text_str = decoded.get("text", "")
            if not text_str and "payload" in decoded:
                payload = decoded["payload"]
                if isinstance(payload, (bytes, bytearray)):
                    text_str = payload.decode("utf-8", errors="replace")

            # 5. Signal and hops
            snr = packet.get("rxSnr")
            hop_start = packet.get("hopStart")
            hop_limit = packet.get("hopLimit")
            hops = None
            if hop_start is not None and hop_limit is not None and hop_start >= hop_limit:
                hops = hop_start - hop_limit
            elif sender_node and sender_node.hops_away is not None:
                hops = sender_node.hops_away

            rx_time = packet.get("rxTime")
            if isinstance(rx_time, (int, float)) and rx_time > 0:
                ts = datetime.fromtimestamp(rx_time)
            else:
                ts = datetime.now()

            channel_idx = packet.get("channel", 0)

            msg = MeshMessage(
                sender_id=from_id,
                sender_name=sender_name,
                sender_short_name=sender_short,
                receiver_id=to_id,
                recipient_name=recipient_name,
                text=text_str,
                channel=channel_idx,
                snr=snr,
                hops=hops,
                timestamp=ts,
                is_dm=is_dm,
            )

            # 6. Dispatch to message callbacks
            for cb in list(self._message_callbacks):
                try:
                    cb(msg)
                except Exception as cb_exc:
                    logger.exception("Error in message callback: %s", cb_exc)

        except Exception as exc:
            logger.exception("Error processing received text message: %s", exc)

    def _on_pubsub_telemetry(self, packet: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle incoming telemetry packet from pubsub."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            updated_node = self._node_store.update_from_telemetry_packet(packet)

            for cb in list(self._telemetry_callbacks):
                try:
                    # Support both cb(packet) and cb(packet, node) signatures
                    sig = inspect.signature(cb)
                    if len(sig.parameters) >= 2:
                        cb(packet, updated_node)
                    else:
                        cb(packet)
                except Exception as cb_exc:
                    logger.exception("Error in telemetry callback: %s", cb_exc)

            if updated_node is not None:
                self._notify_node_updated(updated_node)

        except Exception as exc:
            logger.exception("Error processing received telemetry: %s", exc)

    def _on_pubsub_position(self, packet: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle incoming position packet from pubsub."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            updated_node = self._node_store.update_from_position_packet(packet)
            if updated_node is not None:
                self._notify_node_updated(updated_node)
        except Exception as exc:
            logger.exception("Error processing received position: %s", exc)

    def _on_pubsub_node_updated(self, node: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle node updated event from pubsub."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            updated_node = self._node_store.update_from_node_dict(node)
            self._notify_node_updated(updated_node)
        except Exception as exc:
            logger.exception("Error processing node updated event: %s", exc)

    def _on_pubsub_connection_lost(self, interface=None, **kwargs) -> None:
        """Handle connection lost event from pubsub."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        logger.warning("Pubsub signaled connection lost on %s", self._port)
        lost_port = self._port
        with self._lock:
            self._is_connected = False
        self._notify_connection_change(False, lost_port)

    def _notify_node_updated(self, node: NodeData) -> None:
        """Dispatch node updated event to all registered listeners."""
        for cb in list(self._node_updated_callbacks):
            try:
                cb(node)
            except Exception as cb_exc:
                logger.exception("Error in node_updated callback: %s", cb_exc)

    def _notify_connection_change(self, connected: bool, port: str | None) -> None:
        """Dispatch connection change event to all registered listeners."""
        for cb in list(self._connection_callbacks):
            try:
                cb(connected, port)
            except Exception as cb_exc:
                logger.exception("Error in connection callback: %s", cb_exc)

    def send_broadcast(self, text: str, channel_index: int = 0) -> Any:
        """Send a broadcast text message over the specified channel.

        Args:
            text: Message body to transmit.
            channel_index: Target channel index (default: 0, Primary).

        Returns:
            The sent packet object.
        """
        with self._lock:
            if not self._is_connected or self._interface is None:
                raise ConnectionError("RadioClient is not connected to any radio.")
            iface = self._interface

        return iface.sendText(text=text, destinationId="^all", channelIndex=channel_index)

    def send_dm(self, target_id: str | int, text: str) -> Any:
        """Send a direct private message to a specific node with ACK request.

        Args:
            target_id: Destination node ID (e.g. '!45a466e4') or integer node number.
            text: Message body to transmit.

        Returns:
            The sent packet object.
        """
        with self._lock:
            if not self._is_connected or self._interface is None:
                raise ConnectionError("RadioClient is not connected to any radio.")
            iface = self._interface

        return iface.sendText(text=text, destinationId=target_id, wantAck=True)

    def get_local_node(self) -> NodeData | None:
        """Return the NodeData object corresponding to the connected local radio."""
        with self._lock:
            local = self._node_store.get_local_node()
            if local:
                return local

            if self._interface and self._interface.myInfo and self._interface.myInfo.my_node_num:
                local_num = self._interface.myInfo.my_node_num
                self._node_store.set_local_node_id(local_num)
                return self._node_store.get_local_node()

            return None

    def get_my_info(self) -> dict[str, Any]:
        """Return hardware metadata and node info for the local device."""
        with self._lock:
            if not self._interface or not self._interface.myInfo:
                return {
                    "is_connected": False,
                    "port": self._port,
                }

            try:
                info_dict = MessageToDict(self._interface.myInfo)
            except Exception:
                info_dict = {"my_node_num": getattr(self._interface.myInfo, "my_node_num", 0)}

            info_dict["port"] = self._port
            info_dict["is_connected"] = self.is_connected
            return info_dict

    def get_channels(self) -> list[dict[str, Any]]:
        """Return configured radio channels (primary and secondary)."""
        result: list[dict[str, Any]] = []

        with self._lock:
            if not self._interface or not hasattr(self._interface, "localNode") or not self._interface.localNode:
                return result

            local_node = self._interface.localNode
            channels = getattr(local_node, "channels", []) or []

            for ch in channels:
                if ch is None:
                    continue

                try:
                    ch_dict = MessageToDict(ch)
                except Exception:
                    ch_dict = {}

                # Determine role name
                role_val = getattr(ch, "role", 0)
                if hasattr(role_val, "name"):
                    role_str = role_val.name
                else:
                    try:
                        role_str = channel_pb2.Channel.Role.Name(role_val)
                    except Exception:
                        role_str = str(role_val)

                name = ""
                if hasattr(ch, "settings") and ch.settings and hasattr(ch.settings, "name"):
                    name = ch.settings.name

                index = getattr(ch, "index", 0)
                result.append({
                    "index": index,
                    "name": name,
                    "role": role_str,
                    "raw": ch_dict,
                })

        return result

    def __enter__(self) -> RadioClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
