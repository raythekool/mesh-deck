"""In-memory node database, state manager, and geospatial calculations for Meshtastic nodes."""

from __future__ import annotations

import logging
import math
import threading
from datetime import datetime
from typing import Any

from meshtastic import config_pb2, mesh_pb2
from mesh_deck.core.events import NodeData

logger = logging.getLogger(__name__)


def _format_hw_model(val: Any) -> str:
    """Format hardware model value to string."""
    if isinstance(val, int):
        try:
            return mesh_pb2.HardwareModel.Name(val)
        except Exception:
            return f"HW_{val}"
    return str(val) if val is not None else "UNSET"


def _format_role(val: Any) -> str:
    """Format node role value to string."""
    if isinstance(val, int):
        try:
            return config_pb2.Config.DeviceConfig.Role.Name(val)
        except Exception:
            return f"ROLE_{val}"
    return str(val) if val is not None else "CLIENT"


class NodeStore:
    """Thread-safe store for Mesh network nodes with indexing, filtering, and distance calculations."""

    def __init__(self, local_node_id: str | None = None) -> None:
        self._lock = threading.RLock()
        self._nodes: dict[str, NodeData] = {}
        self._nodes_by_num: dict[int, str] = {}
        self._local_node_id: str | None = local_node_id

    @property
    def local_node_id(self) -> str | None:
        """ID of the current locally connected node."""
        with self._lock:
            return self._local_node_id

    @local_node_id.setter
    def local_node_id(self, node_id: str | int | None) -> None:
        self.set_local_node_id(node_id)

    def set_local_node_id(self, node_id: str | int | None) -> None:
        """Set or update the local node identifier and refresh node flags."""
        with self._lock:
            if isinstance(node_id, int):
                node_id = f"!{node_id:08x}"
            self._local_node_id = node_id

            # Update is_local flag on all nodes in store
            for nid, node in self._nodes.items():
                node.is_local = (nid == self._local_node_id)

            self.recalculate_all_distances()

    def get_local_node(self) -> NodeData | None:
        """Return NodeData for the locally connected device, if known."""
        with self._lock:
            if self._local_node_id and self._local_node_id in self._nodes:
                return self._nodes[self._local_node_id]
            # Fallback search for any node flagged as local
            for node in self._nodes.values():
                if node.is_local:
                    return node
            return None

    def get_node_by_id(self, node_id: str) -> NodeData | None:
        """Look up a node by its hex ID (e.g. '!45a466e4')."""
        with self._lock:
            if not node_id.startswith("!") and not node_id.startswith("0x"):
                formatted = f"!{node_id.lower()}"
                if formatted in self._nodes:
                    return self._nodes[formatted]
            return self._nodes.get(node_id.lower()) or self._nodes.get(node_id)

    def get_node_by_num(self, num: int) -> NodeData | None:
        """Look up a node by its decimal integer number."""
        with self._lock:
            node_id = self._nodes_by_num.get(num)
            if node_id and node_id in self._nodes:
                return self._nodes[node_id]
            return None

    def get_node(self, query: str) -> NodeData | None:
        """Search for a node by ID, AKA/short name, decimal number, or long name substring.

        Search priority:
        1. Exact match on node ID (e.g. '!45a466e4', '45a466e4', '0x45a466e4')
        2. Exact match on AKA / short name (case-insensitive)
        3. Exact match on decimal node number
        4. Hexadecimal conversion match on node number (e.g. 0x45a466e4)
        5. Substring match on long name (case-insensitive, supports unicode & emojis)
        6. Substring match on short name (case-insensitive)
        7. Substring match on hex ID (e.g. '66e4' or '!45a4')
        """
        if not query or not isinstance(query, str):
            return None

        q = query.strip()
        if not q:
            return None
        q_lower = q.lower()

        with self._lock:
            # 1. Exact or normalized ID match
            direct = self.get_node_by_id(q)
            if direct:
                return direct

            # Strip leading !, 0x, #
            normalized_q = q_lower.lstrip("!#")
            if normalized_q.startswith("0x"):
                normalized_q = normalized_q[2:]

            for nid, node in self._nodes.items():
                clean_nid = nid.lstrip("!").lower()
                if clean_nid == normalized_q:
                    return node

            # 2. Exact match on short name / AKA
            for node in self._nodes.values():
                if node.short_name and node.short_name.lower() == q_lower:
                    return node

            # 3. Exact match on decimal node number
            try:
                num_val = int(q, 10)
                node_by_num = self.get_node_by_num(num_val)
                if node_by_num:
                    return node_by_num
            except ValueError:
                pass

            # 4. Hex match on node number
            try:
                hex_val = int(normalized_q, 16)
                node_by_num = self.get_node_by_num(hex_val)
                if node_by_num:
                    return node_by_num
            except ValueError:
                pass

            # 5. Case-insensitive substring match on long name (handles unicode/emojis)
            for node in self._nodes.values():
                if node.long_name and q_lower in node.long_name.lower():
                    return node

            # 6. Case-insensitive substring match on short name
            for node in self._nodes.values():
                if node.short_name and q_lower in node.short_name.lower():
                    return node

            # 7. Substring match on hex ID (e.g. '66e4' matching '!45a466e4')
            if len(normalized_q) >= 2:
                for nid, node in self._nodes.items():
                    clean_nid = nid.lstrip("!").lower()
                    if normalized_q in clean_nid or q_lower in nid.lower():
                        return node

            return None

    def get_all_nodes(
        self,
        sort_by: str = "last_heard",
        active_only: bool = False,
        active_threshold_seconds: int = 7200,
    ) -> list[NodeData]:
        """Return all nodes, optionally filtered and sorted.

        Args:
            sort_by: Sort criterion ("last_heard", "snr", "hops", or "name").
            active_only: If True, only include nodes heard recently or local node.
            active_threshold_seconds: Window in seconds for activity (default: 2 hours).

        Returns:
            Sorted list of NodeData instances.
        """
        now = datetime.now()

        with self._lock:
            node_list = list(self._nodes.values())

            if active_only:
                filtered: list[NodeData] = []
                for n in node_list:
                    if n.is_local:
                        filtered.append(n)
                    elif n.last_heard is not None:
                        try:
                            if n.last_heard.tzinfo is not None:
                                now_cmp = datetime.now(n.last_heard.tzinfo)
                            else:
                                now_cmp = now
                            delta = (now_cmp - n.last_heard).total_seconds()
                            if 0 <= delta <= active_threshold_seconds:
                                filtered.append(n)
                        except Exception:
                            pass
                node_list = filtered

            # Sorting
            if sort_by == "snr":
                # Highest SNR first; None placed last
                node_list.sort(
                    key=lambda n: (
                        n.snr is not None,
                        float(n.snr) if n.snr is not None else float("-inf"),
                    ),
                    reverse=True,
                )
            elif sort_by == "hops":
                # Lowest hops first; None placed last
                node_list.sort(
                    key=lambda n: (
                        n.hops_away is None,
                        int(n.hops_away) if n.hops_away is not None else float("inf"),
                    ),
                )
            elif sort_by == "name":
                # Alphabetical by long_name, then short_name, then ID
                node_list.sort(
                    key=lambda n: (str(n.long_name or n.short_name or n.id or "")).lower(),
                )
            else:
                # Default "last_heard": most recent first; None placed last
                def _last_heard_key(node: NodeData):
                    if node.last_heard is None:
                        return (False, 0.0)
                    try:
                        return (True, node.last_heard.timestamp())
                    except Exception:
                        return (False, 0.0)

                node_list.sort(key=_last_heard_key, reverse=True)

            return node_list

    def update_from_node_dict(self, node_dict: dict[str, Any], is_local: bool | None = None) -> NodeData:
        """Update or insert a node from a raw Meshtastic node dictionary.

        Args:
            node_dict: Meshtastic node dictionary (from interface.nodes or pubsub).
            is_local: Optional override for is_local flag.

        Returns:
            The updated or created NodeData instance.
        """
        num = node_dict.get("num")
        user = node_dict.get("user") or {}
        pos = node_dict.get("position") or {}
        dev_metrics = node_dict.get("deviceMetrics") or {}

        # Resolve ID and Num
        node_id = user.get("id")
        if not node_id:
            if num is not None:
                node_id = f"!{num:08x}"
            else:
                node_id = "!unknown"

        if num is None and node_id.startswith("!"):
            try:
                num = int(node_id[1:], 16)
            except ValueError:
                num = 0

        num = int(num or 0)

        # Parse position
        lat = pos.get("latitude")
        lon = pos.get("longitude")
        if lat is None and "latitudeI" in pos and pos["latitudeI"] is not None:
            lat = float(pos["latitudeI"] * 1e-7)
        if lon is None and "longitudeI" in pos and pos["longitudeI"] is not None:
            lon = float(pos["longitudeI"] * 1e-7)
        alt = pos.get("altitude")

        # Parse last heard
        lh_val = node_dict.get("lastHeard")
        last_heard_dt: datetime | None = None
        if isinstance(lh_val, (int, float)) and lh_val > 0:
            try:
                last_heard_dt = datetime.fromtimestamp(lh_val)
            except Exception:
                last_heard_dt = None
        elif isinstance(lh_val, datetime):
            last_heard_dt = lh_val

        # Determine local status
        if is_local is None:
            is_local = (
                (self._local_node_id is not None and node_id == self._local_node_id)
                or bool(node_dict.get("is_local", False))
            )

        with self._lock:
            existing = self._nodes.get(node_id)
            if existing:
                # Merge fields non-destructively
                if user.get("longName"):
                    existing.long_name = user["longName"]
                if user.get("shortName"):
                    existing.short_name = user["shortName"]
                if user.get("hwModel") is not None:
                    existing.hw_model = _format_hw_model(user["hwModel"])
                if user.get("role") is not None:
                    existing.role = _format_role(user["role"])

                if node_dict.get("snr") is not None:
                    existing.snr = float(node_dict["snr"])
                if node_dict.get("hopsAway") is not None:
                    existing.hops_away = int(node_dict["hopsAway"])
                if dev_metrics.get("batteryLevel") is not None:
                    existing.battery_level = int(dev_metrics["batteryLevel"])
                if dev_metrics.get("voltage") is not None:
                    existing.voltage = float(dev_metrics["voltage"])
                if dev_metrics.get("channelUtilization") is not None:
                    existing.channel_util = float(dev_metrics["channelUtilization"])
                if dev_metrics.get("airUtilTx") is not None:
                    existing.air_util_tx = float(dev_metrics["airUtilTx"])

                if lat is not None:
                    existing.latitude = float(lat)
                if lon is not None:
                    existing.longitude = float(lon)
                if alt is not None:
                    existing.altitude = float(alt)

                if last_heard_dt is not None:
                    existing.last_heard = last_heard_dt

                if "isFavorite" in node_dict:
                    existing.is_favorite = bool(node_dict["isFavorite"])

                if is_local:
                    existing.is_local = True

                self._nodes_by_num[num] = node_id
                existing.distance_km = self.calculate_distance(existing)
                return existing

            # Create new NodeData
            new_node = NodeData(
                id=node_id,
                num=num,
                long_name=user.get("longName") or "",
                short_name=user.get("shortName") or "",
                hw_model=_format_hw_model(user.get("hwModel")),
                role=_format_role(user.get("role")),
                snr=float(node_dict["snr"]) if node_dict.get("snr") is not None else None,
                hops_away=int(node_dict["hopsAway"]) if node_dict.get("hopsAway") is not None else None,
                battery_level=int(dev_metrics["batteryLevel"]) if dev_metrics.get("batteryLevel") is not None else None,
                voltage=float(dev_metrics["voltage"]) if dev_metrics.get("voltage") is not None else None,
                channel_util=float(dev_metrics["channelUtilization"]) if dev_metrics.get("channelUtilization") is not None else None,
                air_util_tx=float(dev_metrics["airUtilTx"]) if dev_metrics.get("airUtilTx") is not None else None,
                latitude=float(lat) if lat is not None else None,
                longitude=float(lon) if lon is not None else None,
                altitude=float(alt) if alt is not None else None,
                last_heard=last_heard_dt,
                is_local=is_local,
                is_favorite=bool(node_dict.get("isFavorite", False)),
            )
            self._nodes[node_id] = new_node
            self._nodes_by_num[num] = node_id
            new_node.distance_km = self.calculate_distance(new_node)
            return new_node

    def update_from_telemetry_packet(self, packet: dict[str, Any]) -> NodeData | None:
        """Update node state from a received telemetry packet.

        Parses deviceMetrics, environmentMetrics, powerMetrics, and localStats.
        """
        from_num = packet.get("from")
        from_id = packet.get("fromId")
        if from_num is None and not from_id:
            return None

        with self._lock:
            node = (
                self.get_node_by_id(from_id)
                if from_id
                else self.get_node_by_num(from_num)
            )
            if not node:
                # Synthesize a minimal node entry
                n_id = from_id or f"!{from_num:08x}"
                node = self.update_from_node_dict({"num": from_num or 0, "user": {"id": n_id}})

            telemetry = packet.get("decoded", {}).get("telemetry", {})
            dev_metrics = telemetry.get("deviceMetrics", {})
            env_metrics = telemetry.get("environmentMetrics", {})
            power_metrics = telemetry.get("powerMetrics", {})
            local_stats = telemetry.get("localStats", {})

            # Device metrics
            if dev_metrics.get("batteryLevel") is not None:
                node.battery_level = int(dev_metrics["batteryLevel"])
            if dev_metrics.get("voltage") is not None:
                node.voltage = float(dev_metrics["voltage"])
            elif env_metrics.get("voltage") is not None:
                node.voltage = float(env_metrics["voltage"])
            elif power_metrics.get("ch1Voltage") is not None:
                node.voltage = float(power_metrics["ch1Voltage"])

            if dev_metrics.get("channelUtilization") is not None:
                node.channel_util = float(dev_metrics["channelUtilization"])
            elif local_stats.get("channelUtilization") is not None:
                node.channel_util = float(local_stats["channelUtilization"])

            if dev_metrics.get("airUtilTx") is not None:
                node.air_util_tx = float(dev_metrics["airUtilTx"])
            elif local_stats.get("airUtilTx") is not None:
                node.air_util_tx = float(local_stats["airUtilTx"])

            # Environment metrics
            if env_metrics.get("temperature") is not None:
                node.temperature = float(env_metrics["temperature"])
            if env_metrics.get("relativeHumidity") is not None:
                node.relative_humidity = float(env_metrics["relativeHumidity"])
            elif env_metrics.get("humidity") is not None:
                node.relative_humidity = float(env_metrics["humidity"])

            if env_metrics.get("barometricPressure") is not None:
                node.barometric_pressure = float(env_metrics["barometricPressure"])
            elif env_metrics.get("pressure") is not None:
                node.barometric_pressure = float(env_metrics["pressure"])

            self._update_common_packet_fields(node, packet)
            return node

    def update_from_position_packet(self, packet: dict[str, Any]) -> NodeData | None:
        """Update node coordinates from a received position packet with bounds validation."""
        from_num = packet.get("from")
        from_id = packet.get("fromId")
        if from_num is None and not from_id:
            return None

        pos = packet.get("decoded", {}).get("position", {})

        with self._lock:
            node = (
                self.get_node_by_id(from_id)
                if from_id
                else self.get_node_by_num(from_num)
            )
            if not node:
                n_id = from_id or f"!{from_num:08x}"
                node = self.update_from_node_dict({"num": from_num or 0, "user": {"id": n_id}})

            lat = pos.get("latitude")
            lon = pos.get("longitude")
            if lat is None and "latitudeI" in pos and pos["latitudeI"] is not None:
                lat = float(pos["latitudeI"] * 1e-7)
            if lon is None and "longitudeI" in pos and pos["longitudeI"] is not None:
                lon = float(pos["longitudeI"] * 1e-7)

            # Validate coordinate ranges [-90, 90] and [-180, 180]
            valid_coords = False
            if lat is not None and lon is not None:
                try:
                    f_lat, f_lon = float(lat), float(lon)
                    if -90.0 <= f_lat <= 90.0 and -180.0 <= f_lon <= 180.0:
                        # Reject 0.0, 0.0 if existing node already has a valid fix
                        if not (f_lat == 0.0 and f_lon == 0.0 and node.has_position):
                            node.latitude = f_lat
                            node.longitude = f_lon
                            valid_coords = True
                except (ValueError, TypeError):
                    pass

            if pos.get("altitude") is not None:
                try:
                    node.altitude = float(pos["altitude"])
                except (ValueError, TypeError):
                    pass

            self._update_common_packet_fields(node, packet)
            if valid_coords:
                node.distance_km = self.calculate_distance(node)
            return node

    def update_from_packet(self, packet: dict[str, Any]) -> NodeData | None:
        """Update node last_heard, SNR, and hops from any generic packet."""
        from_num = packet.get("from")
        from_id = packet.get("fromId")
        if from_num is None and not from_id:
            return None

        with self._lock:
            node = (
                self.get_node_by_id(from_id)
                if from_id
                else self.get_node_by_num(from_num)
            )
            if not node:
                n_id = from_id or f"!{from_num:08x}"
                node = self.update_from_node_dict({"num": from_num or 0, "user": {"id": n_id}})

            self._update_common_packet_fields(node, packet)
            return node

    def _update_common_packet_fields(self, node: NodeData, packet: dict[str, Any]) -> None:
        """Helper to update SNR, hops, and timestamp from packet header."""
        if packet.get("rxSnr") is not None:
            try:
                node.snr = float(packet["rxSnr"])
            except (ValueError, TypeError):
                pass

        # Calculate hops if hopStart and hopLimit are present
        hop_start = packet.get("hopStart")
        hop_limit = packet.get("hopLimit")
        if hop_start is not None and hop_limit is not None:
            try:
                hops = int(hop_start) - int(hop_limit)
                if hops >= 0:
                    node.hops_away = hops
            except (ValueError, TypeError):
                pass

        rx_time = packet.get("rxTime")
        if isinstance(rx_time, (int, float)) and rx_time > 0:
            try:
                node.last_heard = datetime.fromtimestamp(rx_time)
            except Exception:
                node.last_heard = datetime.now()
        else:
            node.last_heard = datetime.now()

    def update_node(self, node_data: NodeData) -> None:
        """Insert or replace a NodeData instance in the store."""
        with self._lock:
            self._nodes[node_data.id] = node_data
            self._nodes_by_num[node_data.num] = node_data.id
            node_data.distance_km = self.calculate_distance(node_data)

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float | None:
        """Calculate great-circle distance in kilometers using the Haversine formula.

        Returns None if coordinates are missing, non-numeric, or out of geographical range.
        """
        try:
            lat1, lon1 = float(lat1), float(lon1)
            lat2, lon2 = float(lat2), float(lon2)
        except (ValueError, TypeError):
            return None

        # Geographical bounds validation
        if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
            return None
        if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
            return None
        if (lat1 == 0.0 and lon1 == 0.0) or (lat2 == 0.0 and lon2 == 0.0):
            return None

        r_earth = 6371.0  # Mean radius of Earth in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        # Protect against floating-point precision error where a > 1.0
        a = min(1.0, max(0.0, a))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r_earth * c, 2)

    def calculate_distance(
        self, target_or_a: str | NodeData, b: str | NodeData | None = None
    ) -> float | None:
        """Calculate distance in km between local node and target, or between two nodes.

        If b is provided, calculates distance between target_or_a and b.
        Otherwise, calculates distance between local node and target_or_a.
        Returns None if either node lacks valid coordinates.
        """
        if b is not None:
            return self.distance_between(target_or_a, b)

        with self._lock:
            local = self.get_local_node()
            if not local or not local.has_position:
                return None

            if isinstance(target_or_a, str):
                target_node = self.get_node(target_or_a)
            else:
                target_node = target_or_a

            if not target_node or not target_node.has_position:
                return None

            # Same node has 0.0 distance
            if target_node.id == local.id:
                return 0.0

            return self.haversine_distance(
                local.latitude, local.longitude, target_node.latitude, target_node.longitude
            )

    def distance_between(self, node_a: str | NodeData, node_b: str | NodeData) -> float | None:
        """Calculate distance in km between any two nodes."""
        with self._lock:
            na = self.get_node(node_a) if isinstance(node_a, str) else node_a
            nb = self.get_node(node_b) if isinstance(node_b, str) else node_b

            if not na or not na.has_position or not nb or not nb.has_position:
                return None

            return self.haversine_distance(na.latitude, na.longitude, nb.latitude, nb.longitude)

    def recalculate_all_distances(self) -> None:
        """Recalculate distance_km for all stored nodes relative to local node."""
        with self._lock:
            for node in self._nodes.values():
                node.distance_km = self.calculate_distance(node)

    def clear(self) -> None:
        """Remove all nodes from store."""
        with self._lock:
            self._nodes.clear()
            self._nodes_by_num.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

    def __contains__(self, item: str) -> bool:
        with self._lock:
            return item in self._nodes or item in self._nodes_by_num

    def __iter__(self):
        with self._lock:
            return iter(list(self._nodes.values()))
