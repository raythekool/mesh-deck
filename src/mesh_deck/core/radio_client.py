"""RadioClient encapsulating meshtastic SerialInterface and pubsub event routing.

Locking: ``RadioClient`` guards its own connection state with ``self._lock``
and may call into ``NodeStore`` while holding it. The lock order is therefore
``RadioClient`` → ``NodeStore``; never take the radio lock from code that
already holds the store lock.
"""

from __future__ import annotations

import inspect
import logging
import threading
import time
from datetime import datetime
from typing import Any
from collections.abc import Callable

from google.protobuf.json_format import MessageToDict
from meshtastic import channel_pb2, mesh_pb2, portnums_pb2
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

from mesh_deck.core.events import (
    MeshMessage,
    NeighborLink,
    NeighborReport,
    NodeData,
    TraceRouteResult,
)
from mesh_deck.core.history import HistoryStore
from mesh_deck.core.node_store import NodeStore

logger = logging.getLogger(__name__)

# RF-1.4: exponential backoff (seconds) used when a connection drops
# unexpectedly. The last value repeats until the radio comes back or the user
# disconnects, so an unplugged cable settles into a quiet slow poll.
RECONNECT_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 5.0, 10.0, 20.0, 30.0)


class RadioOperationError(RuntimeError):
    """A radio operation failed inside meshtastic-python."""


class RadioOperationCancelled(RuntimeError):
    """A caller cancelled a radio operation while waiting for a response."""


def _guard_library_exit(operation: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a meshtastic call, converting its ``sys.exit()`` into an exception.

    meshtastic-python reports some failures (an unknown destination node, for
    instance) by calling ``our_exit()``, which prints and raises SystemExit.
    SystemExit derives from BaseException, so it sails past every ``except
    Exception`` in the app and takes the whole process — or the Textual
    worker running the command — down with it. Converting it here fixes the
    REPL, the CLI and the MCP server at once, since they all send through
    RadioClient.
    """
    try:
        return func(*args, **kwargs)
    except SystemExit as exc:
        raise RadioOperationError(
            f"{operation} was rejected by the radio library "
            f"(the destination may be unknown to this node)."
        ) from exc


class RadioClient:
    """High-level client for Meshtastic serial connection, event dispatching, and state tracking."""

    def __init__(
        self,
        node_store: NodeStore | None = None,
        history: HistoryStore | None = None,
        auto_reconnect: bool = True,
    ) -> None:
        self._node_store = node_store if node_store is not None else NodeStore()
        self._history = history
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
        self._device_log_callbacks: list[Callable[[str, str | None], Any]] = []

        # Pubsub subscription flags
        self._subscribed = False

        # Automatic reconnection state (RF-1.4)
        self.auto_reconnect = auto_reconnect
        self._reconnect_thread: threading.Thread | None = None
        self._reconnect_stop = threading.Event()
        self._reconnect_callbacks: list[Callable[[str, int], Any]] = []
        self._expect_disconnect = threading.Event()

        # Mesh topology state (RF-2.3) and traceroute plumbing (RF-3.1)
        self._neighbor_reports: dict[str, NeighborReport] = {}
        self._neighbor_callbacks: list[Callable[[NeighborReport], Any]] = []
        self._traceroute_callbacks: list[Callable[[TraceRouteResult], Any]] = []
        self._traceroute_waiters: dict[str, list[Any]] = {}
        self._last_traceroute: TraceRouteResult | None = None

    @property
    def node_store(self) -> NodeStore:
        """Underlying NodeStore instance."""
        return self._node_store

    @property
    def history(self) -> HistoryStore | None:
        """Attached HistoryStore instance, or None if history persistence is disabled."""
        return self._history

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
                event = self._interface.isConnected
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

    def off_message_received(self, callback: Callable[[MeshMessage], Any]) -> None:
        """Unregister a previously registered message callback, if present."""
        with self._lock:
            if callback in self._message_callbacks:
                self._message_callbacks.remove(callback)

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

    def on_device_log(self, callback: Callable[[str, str | None], Any]) -> None:
        """Register a callback for log lines forwarded by the active radio."""
        with self._lock:
            if callback not in self._device_log_callbacks:
                self._device_log_callbacks.append(callback)

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
        # A user-driven connect supersedes any pending automatic retry.
        self._stop_reconnect()

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

                # RF profile lives on the interface, not in the node DB: copy it
                # onto the local node so the banner can render region/preset.
                local_node = self._node_store.get_local_node()
                if local_node is not None:
                    profile = self._radio_profile()
                    local_node.region = profile.get("region") or local_node.region
                    local_node.modem_preset = (
                        profile.get("modem_preset") or local_node.modem_preset
                    )

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
        # An explicit disconnect wins over an automatic retry.
        self._stop_reconnect()
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
            # Closing publishes meshtastic.connection.lost; flag it so the echo
            # of our own shutdown is not reported to the user as a failure.
            self._expect_disconnect.set()
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
            pub.subscribe(self._on_pubsub_neighborinfo, "meshtastic.receive.neighborinfo")
            pub.subscribe(self._on_pubsub_traceroute, "meshtastic.receive.traceroute")
            pub.subscribe(self._on_pubsub_log_line, "meshtastic.log.line")
            pub.subscribe(self._on_pubsub_connection_lost, "meshtastic.connection.lost")
            self._subscribed = True

    @staticmethod
    def _as_node_id(value: Any) -> str | None:
        """Normalize a node reference (int or string) to '!hex' form."""
        if value is None:
            return None
        if isinstance(value, int):
            return f"!{value & 0xFFFFFFFF:08x}"
        text = str(value).strip()
        if not text:
            return None
        if text.startswith("!"):
            return text.lower()
        try:
            return f"!{int(text) & 0xFFFFFFFF:08x}"
        except ValueError:
            return text.lower()

    def _on_pubsub_log_line(self, line: str, interface=None, **kwargs) -> None:
        """Forward a line published by the connected Meshtastic device."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return
        port = self.port
        for callback in list(self._device_log_callbacks):
            try:
                callback(line, port)
            except Exception as callback_exc:
                logger.exception("Error in device log callback: %s", callback_exc)

    def _on_pubsub_neighborinfo(self, packet: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle a NeighborInfo broadcast, recording the reporter's neighbor table."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            self._node_store.update_from_packet(packet)
            info = (packet.get("decoded") or {}).get("neighborinfo") or {}
            reporter = self._as_node_id(info.get("nodeId") or packet.get("fromId") or packet.get("from"))
            if not reporter:
                return

            links: list[NeighborLink] = []
            for raw in info.get("neighbors") or []:
                neighbor_id = self._as_node_id(raw.get("nodeId"))
                if not neighbor_id:
                    continue
                last_rx = raw.get("lastRxTime")
                last_rx_dt: datetime | None = None
                if isinstance(last_rx, (int, float)) and last_rx > 0:
                    try:
                        last_rx_dt = datetime.fromtimestamp(last_rx)
                    except (OverflowError, OSError, ValueError):
                        last_rx_dt = None
                snr = raw.get("snr")
                links.append(NeighborLink(
                    node_id=neighbor_id,
                    snr=float(snr) if snr is not None else None,
                    last_rx_time=last_rx_dt,
                ))

            interval = info.get("nodeBroadcastIntervalSecs")
            report = NeighborReport(
                node_id=reporter,
                neighbors=links,
                broadcast_interval_secs=int(interval) if interval is not None else None,
            )
            with self._lock:
                self._neighbor_reports[reporter] = report

            for cb in list(self._neighbor_callbacks):
                try:
                    cb(report)
                except Exception as cb_exc:
                    logger.exception("Error in neighbor callback: %s", cb_exc)
        except Exception as exc:
            logger.exception("Error processing neighbor info: %s", exc)

    def _on_pubsub_traceroute(self, packet: dict[str, Any], interface=None, **kwargs) -> None:
        """Handle a traceroute reply and hand the hop path to any waiter."""
        if self._interface is not None and interface is not None and interface != self._interface:
            return

        try:
            self._node_store.update_from_packet(packet)
            discovery = (packet.get("decoded") or {}).get("traceroute") or {}
            target = self._as_node_id(packet.get("fromId") or packet.get("from")) or "!unknown"

            def _ids(values: Any) -> list[str]:
                return [nid for nid in (self._as_node_id(v) for v in (values or [])) if nid]

            def _snrs(values: Any) -> list[float]:
                # The firmware scales SNR by 4 and uses -128 for "unknown".
                return [float(v) / 4.0 for v in (values or []) if v is not None and v != -128]

            result = TraceRouteResult(
                target_id=target,
                route_to=_ids(discovery.get("route")),
                snr_to=_snrs(discovery.get("snrTowards")),
                route_back=_ids(discovery.get("routeBack")),
                snr_back=_snrs(discovery.get("snrBack")),
            )
            with self._lock:
                self._last_traceroute = result
                waiter = self._traceroute_waiters.pop(target, None)
            if waiter is not None:
                waiter[0] = result
                waiter[1].set()

            for cb in list(self._traceroute_callbacks):
                try:
                    cb(result)
                except Exception as cb_exc:
                    logger.exception("Error in traceroute callback: %s", cb_exc)
        except Exception as exc:
            logger.exception("Error processing traceroute reply: %s", exc)

    def on_neighbor_report(self, callback: Callable[[NeighborReport], Any]) -> None:
        """Register a callback for incoming NeighborInfo broadcasts."""
        with self._lock:
            if callback not in self._neighbor_callbacks:
                self._neighbor_callbacks.append(callback)

    def on_traceroute_result(self, callback: Callable[[TraceRouteResult], Any]) -> None:
        """Register a callback for traceroute replies."""
        with self._lock:
            if callback not in self._traceroute_callbacks:
                self._traceroute_callbacks.append(callback)

    def get_neighbor_reports(self) -> list[NeighborReport]:
        """Return every neighbor table observed so far, newest report per node."""
        with self._lock:
            return list(self._neighbor_reports.values())

    def get_neighbors_of(self, node_id: str) -> NeighborReport | None:
        """Return the neighbor table broadcast by one node, if it was heard."""
        key = self._as_node_id(node_id)
        with self._lock:
            return self._neighbor_reports.get(key) if key else None

    def trace_route(
        self,
        target_id: str | int,
        hop_limit: int = 7,
        timeout: float = 30.0,
        channel_index: int = 0,
        cancel_event: threading.Event | None = None,
    ) -> TraceRouteResult | None:
        """Send a traceroute request and wait for the hop path.

        Uses ``sendData`` rather than ``SerialInterface.sendTraceRoute`` because
        the latter blocks on its own acknowledgment and prints to stdout, which
        would break the MCP stdio contract (RNF-6).

        Returns:
            The route, or None if no reply arrived before the timeout.
        """
        with self._lock:
            if not self._is_connected or self._interface is None:
                raise ConnectionError("RadioClient is not connected to any radio.")
            iface = self._interface

        target = self._as_node_id(target_id) or str(target_id)
        waiter: list[Any] = [None, threading.Event()]
        with self._lock:
            self._traceroute_waiters[target] = waiter

        try:
            _guard_library_exit(
                "The traceroute request",
                iface.sendData,
                mesh_pb2.RouteDiscovery(),
                destinationId=target,
                portNum=portnums_pb2.PortNum.TRACEROUTE_APP,
                wantResponse=True,
                channelIndex=channel_index,
                hopLimit=hop_limit,
            )
        except Exception:
            with self._lock:
                self._traceroute_waiters.pop(target, None)
            raise

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if waiter[1].wait(min(remaining, 0.1)):
                return waiter[0]
            if cancel_event is not None and cancel_event.is_set():
                with self._lock:
                    self._traceroute_waiters.pop(target, None)
                raise RadioOperationCancelled(f"Traceroute to {target} was cancelled.")

        with self._lock:
            self._traceroute_waiters.pop(target, None)
        logger.info("Traceroute to %s timed out after %.0fs", target, timeout)
        return None

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

            # 7. Persist to local history, if enabled
            if self._history is not None:
                try:
                    self._history.record_message(msg, direction="in")
                except Exception as hist_exc:
                    logger.exception("Error recording message history: %s", hist_exc)

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

        if self._expect_disconnect.is_set():
            # Echo of a disconnect() or a port switch we initiated ourselves.
            self._expect_disconnect.clear()
            logger.debug("Ignoring connection.lost echo from our own shutdown")
            return

        logger.warning("Pubsub signaled connection lost on %s", self._port)
        lost_port = self._port
        with self._lock:
            self._is_connected = False
            if self._interface is not None:
                try:
                    self._interface.close()
                except Exception:
                    pass
                self._interface = None
            self._port = None
        self._notify_connection_change(False, lost_port)
        if lost_port:
            self._start_reconnect(lost_port)

    def on_reconnect_attempt(self, callback: Callable[[str, int], Any]) -> None:
        """Register a callback invoked before each reconnection attempt (port, attempt)."""
        with self._lock:
            if callback not in self._reconnect_callbacks:
                self._reconnect_callbacks.append(callback)

    @property
    def is_reconnecting(self) -> bool:
        """Whether a background reconnection loop is currently running."""
        thread = self._reconnect_thread
        return thread is not None and thread.is_alive()

    def _start_reconnect(self, port: str) -> None:
        """Begin retrying the lost port in the background, unless already trying."""
        if not self.auto_reconnect or self.is_reconnecting:
            return
        self._reconnect_stop.clear()
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            args=(port,),
            name=f"RadioClient-Reconnect-{port}",
            daemon=True,
        )
        self._reconnect_thread.start()

    def _stop_reconnect(self) -> None:
        """Signal any running reconnection loop to give up."""
        self._reconnect_stop.set()

    def _reconnect_loop(self, port: str) -> None:
        """Retry the dropped port with backoff until it answers or we're told to stop."""
        attempt = 0
        while not self._reconnect_stop.is_set():
            delay = RECONNECT_BACKOFF_SECONDS[min(attempt, len(RECONNECT_BACKOFF_SECONDS) - 1)]
            if self._reconnect_stop.wait(delay):
                return
            if self.is_connected:
                return

            attempt += 1
            for cb in list(self._reconnect_callbacks):
                try:
                    cb(port, attempt)
                except Exception as cb_exc:
                    logger.exception("Error in reconnect callback: %s", cb_exc)

            logger.info("Reconnection attempt %d on %s", attempt, port)
            try:
                self._do_connect(port, timeout=30)
            except Exception as exc:
                logger.debug("Reconnection attempt %d failed: %s", attempt, exc)
                continue
            if self.is_connected:
                logger.info("Reconnected to %s after %d attempt(s)", port, attempt)
                return

    def _notify_node_updated(self, node: NodeData) -> None:
        """Dispatch node updated event to all registered listeners."""
        for cb in list(self._node_updated_callbacks):
            try:
                cb(node)
            except Exception as cb_exc:
                logger.exception("Error in node_updated callback: %s", cb_exc)

        if self._history is not None:
            try:
                self._history.record_node(node)
            except Exception as hist_exc:
                logger.exception("Error recording node history: %s", hist_exc)

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

        result = _guard_library_exit(
            "Broadcast",
            iface.sendText,
            text=text,
            destinationId="^all",
            channelIndex=channel_index,
        )
        self._record_outgoing_message(
            text,
            receiver_id="^all",
            recipient_name="Broadcast",
            channel=channel_index,
            is_dm=False,
        )
        return result

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

        result = _guard_library_exit(
            "The direct message",
            iface.sendText,
            text=text,
            destinationId=target_id,
            wantAck=True,
        )
        target_node = self._node_store.get_node(str(target_id))
        self._record_outgoing_message(
            text,
            receiver_id=str(target_id),
            recipient_name=target_node.display_name if target_node else str(target_id),
            channel=0,
            is_dm=True,
        )
        return result

    def _record_outgoing_message(
        self,
        text: str,
        *,
        receiver_id: str,
        recipient_name: str,
        channel: int,
        is_dm: bool,
    ) -> None:
        """Persist a locally-sent message to history, if enabled."""
        if self._history is None:
            return
        local = self.get_local_node()
        msg = MeshMessage(
            sender_id=local.id if local else "^local",
            sender_name=local.display_name if local else "Locale",
            sender_short_name=local.short_name if local else None,
            receiver_id=receiver_id,
            recipient_name=recipient_name,
            text=text,
            channel=channel,
            is_dm=is_dm,
        )
        try:
            self._history.record_message(msg, direction="out")
        except Exception as hist_exc:
            logger.exception("Error recording outgoing message history: %s", hist_exc)

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

    def _radio_profile(self) -> dict[str, Any]:
        """Return firmware/region/modem preset, which live outside ``myInfo``.

        ``MyNodeInfo`` carries neither the firmware version nor the LoRa
        settings, so ``/info`` and the status banner have to read them from
        ``interface.metadata`` and ``localNode.localConfig.lora``.
        """
        profile: dict[str, Any] = {}
        iface = self._interface
        if iface is None:
            return profile

        firmware = getattr(getattr(iface, "metadata", None), "firmware_version", None)
        if firmware:
            profile["firmware_version"] = str(firmware)

        lora = getattr(
            getattr(getattr(iface, "localNode", None), "localConfig", None), "lora", None
        )
        if lora is not None:
            try:
                # MessageToDict resolves protobuf enums to their symbolic names.
                lora_dict = MessageToDict(lora)
            except Exception:
                lora_dict = {}
            if lora_dict.get("region"):
                profile["region"] = lora_dict["region"]
            if lora_dict.get("modemPreset"):
                profile["modem_preset"] = lora_dict["modemPreset"]
        return profile

    def get_my_info(self) -> dict[str, Any]:
        """Return hardware metadata and node info for the local device.

        Keys are normalized to snake_case (``my_node_num``, ``firmware_version``,
        ``region``, ``modem_preset``) so every consumer reads one stable shape.
        """
        with self._lock:
            if not self._interface or not self._interface.myInfo:
                return {
                    "is_connected": False,
                    "port": self._port,
                }

            try:
                info_dict = MessageToDict(self._interface.myInfo)
            except Exception:
                info_dict = {}

            my_node_num = info_dict.pop("myNodeNum", None)
            if my_node_num is None:
                my_node_num = getattr(self._interface.myInfo, "my_node_num", 0)
            info_dict["my_node_num"] = my_node_num

            info_dict.update(self._radio_profile())
            info_dict["port"] = self._port
            info_dict["is_connected"] = self.is_connected
            return info_dict

    def get_channels(self) -> list[dict[str, Any]]:
        """Return configured radio channels (primary and secondary).

        Emits the normalized keys every consumer expects (``uplink_enabled``,
        ``downlink_enabled``, ``has_psk``); the pre-shared key itself is never
        exposed, only whether one is configured.
        """
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

                settings = getattr(ch, "settings", None)
                name = getattr(settings, "name", "") or "" if settings is not None else ""
                psk = getattr(settings, "psk", b"") if settings is not None else b""

                index = getattr(ch, "index", 0)
                result.append({
                    "index": index,
                    "name": name,
                    "role": role_str,
                    "uplink_enabled": bool(getattr(settings, "uplink_enabled", False)) if settings is not None else False,
                    "downlink_enabled": bool(getattr(settings, "downlink_enabled", False)) if settings is not None else False,
                    "has_psk": bool(psk),
                    "raw": ch_dict,
                })

        return result

    def __enter__(self) -> RadioClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
