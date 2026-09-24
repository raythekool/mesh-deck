"""Domain events and data models for Meshtastic network state and messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from meshtastic import config_pb2, mesh_pb2


@dataclass(frozen=True)
class NodeDbSyncProgress:
    """Observable progress for the initial NodeDB synchronization."""

    stage: str
    node_count: int = 0


def format_hw_model(val: Any) -> str:
    """Format a hardware model value (protobuf enum or string) to a name."""
    if isinstance(val, int):
        try:
            return mesh_pb2.HardwareModel.Name(val)
        except Exception:
            return f"HW_{val}"
    return str(val) if val is not None else "UNSET"


def format_role(val: Any) -> str:
    """Format a node role value (protobuf enum or string) to a name."""
    if isinstance(val, int):
        try:
            return config_pb2.Config.DeviceConfig.Role.Name(val)
        except Exception:
            return f"ROLE_{val}"
    return str(val) if val is not None else "CLIENT"


def _coordinate(pos: dict[str, Any], key: str) -> float | None:
    """Read a coordinate, falling back to the integer 1e-7 encoding."""
    value = pos.get(key)
    if value is not None:
        return float(value)
    scaled = pos.get(f"{key}I")  # latitudeI / longitudeI
    if scaled is not None:
        return float(scaled * 1e-7)
    return None


def parse_node_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw Meshtastic node dictionary into NodeData field names.

    Only keys actually present in ``data`` are returned, so callers can either
    build a fresh :class:`NodeData` or merge into an existing one without
    clobbering known values with absent ones. ``id`` and ``num`` are always
    resolved.
    """
    user = data.get("user") or {}
    pos = data.get("position") or {}
    dev_metrics = data.get("deviceMetrics") or {}
    env_metrics = data.get("environmentMetrics") or {}

    num = data.get("num")
    node_id = user.get("id")
    if not node_id:
        node_id = f"!{num:08x}" if num is not None else "!unknown"
    if num is None and node_id.startswith("!"):
        try:
            num = int(node_id[1:], 16)
        except ValueError:
            num = 0

    fields: dict[str, Any] = {"id": node_id, "num": int(num or 0)}

    # Identity: names are only overwritten when non-empty, so a partial update
    # never blanks out a name we already learned.
    if user.get("longName"):
        fields["long_name"] = user["longName"]
    if user.get("shortName"):
        fields["short_name"] = user["shortName"]
    if user.get("hwModel") is not None:
        fields["hw_model"] = format_hw_model(user["hwModel"])
    if user.get("role") is not None:
        fields["role"] = format_role(user["role"])
    if user.get("publicKey") is not None:
        fields["public_key"] = user["publicKey"]
    if user.get("isLicensed") is not None:
        fields["is_licensed"] = bool(user["isLicensed"])

    # Link quality
    if data.get("snr") is not None:
        fields["snr"] = float(data["snr"])
    if data.get("hopsAway") is not None:
        fields["hops_away"] = int(data["hopsAway"])

    # Device metrics
    for source_key, target_key, caster in (
        ("batteryLevel", "battery_level", int),
        ("voltage", "voltage", float),
        ("channelUtilization", "channel_util", float),
        ("airUtilTx", "air_util_tx", float),
    ):
        if dev_metrics.get(source_key) is not None:
            fields[target_key] = caster(dev_metrics[source_key])

    # Environment metrics
    for source_key, target_key in (
        ("temperature", "temperature"),
        ("relativeHumidity", "relative_humidity"),
        ("barometricPressure", "barometric_pressure"),
    ):
        if env_metrics.get(source_key) is not None:
            fields[target_key] = float(env_metrics[source_key])

    # Position
    latitude = _coordinate(pos, "latitude")
    longitude = _coordinate(pos, "longitude")
    if latitude is not None:
        fields["latitude"] = latitude
    if longitude is not None:
        fields["longitude"] = longitude
    if pos.get("altitude") is not None:
        fields["altitude"] = float(pos["altitude"])

    last_heard = data.get("lastHeard")
    if isinstance(last_heard, datetime):
        fields["last_heard"] = last_heard
    elif isinstance(last_heard, (int, float)) and last_heard > 0:
        try:
            fields["last_heard"] = datetime.fromtimestamp(last_heard)
        except (OverflowError, OSError, ValueError):
            pass

    if "isFavorite" in data:
        fields["is_favorite"] = bool(data["isFavorite"])

    return fields


@dataclass
class NodeData:
    """Represents the complete state of a Meshtastic mesh node."""

    id: str  # Hex format, e.g. "!45a466e4"
    num: int = 0  # Decimal node number, e.g. 1168467684
    long_name: str = ""
    short_name: str = ""  # AKA
    hw_model: str = ""  # e.g. "HELTEC_V2_0", "TLORA_V2_1_16", "E290"
    role: str = "CLIENT"  # e.g. "CLIENT", "ROUTER", "REPEATER"
    snr: float | None = None  # Signal-to-noise ratio in dB
    hops_away: int | None = None  # Hop count to reach node
    battery_level: int | None = None  # 0-100%, or >100 for USB powered
    voltage: float | None = None  # Volts (e.g. 4.15)
    channel_util: float | None = None  # Channel utilization percentage
    air_util_tx: float | None = None  # Tx air utilization percentage
    latitude: float | None = None  # Degrees (-90.0 to 90.0)
    longitude: float | None = None  # Degrees (-180.0 to 180.0)
    altitude: float | None = None  # Meters above sea level
    last_heard: datetime | None = None
    is_local: bool = False
    is_favorite: bool = False

    # Optional extension fields for UI rendering, compatibility, and caching
    distance_km: float | None = None
    temperature: float | None = None
    relative_humidity: float | None = None
    barometric_pressure: float | None = None
    public_key: str | None = None
    region: str | None = None
    modem_preset: str | None = None
    is_licensed: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def aka(self) -> str:
        """Alias for short_name."""
        return self.short_name or (self.id[-4:] if len(self.id) >= 4 else self.id)

    @property
    def hardware(self) -> str:
        """Alias for hw_model."""
        return self.hw_model

    @property
    def channel_utilization(self) -> float | None:
        """Alias for channel_util."""
        return self.channel_util

    @property
    def has_position(self) -> bool:
        """Check if node has valid geographical coordinates."""
        if self.latitude is None or self.longitude is None:
            return False
        try:
            lat = float(self.latitude)
            lon = float(self.longitude)
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return False
            # 0.0, 0.0 indicates an unacquired GPS fix in Meshtastic hardware
            if lat == 0.0 and lon == 0.0:
                return False
            return True
        except (ValueError, TypeError):
            return False

    @property
    def has_coords(self) -> bool:
        """Alias for has_position."""
        return self.has_position

    @property
    def display_name(self) -> str:
        """Human-readable display name for this node."""
        return self.long_name or self.short_name or self.id

    @property
    def coords_str(self) -> str:
        """Formatted coordinates string."""
        if not self.has_coords:
            return "N/A"
        alt_str = f", {self.altitude:.0f}m" if self.altitude is not None else ""
        return f"{self.latitude:.5f}°, {self.longitude:.5f}°{alt_str}"

    @property
    def osm_url(self) -> str | None:
        """OpenStreetMap URL if coordinates are available."""
        if not self.has_coords:
            return None
        return f"https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}#map=15/{self.latitude}/{self.longitude}"

    def to_dict(self) -> dict[str, Any]:
        """Convert NodeData to a plain dictionary."""
        return {
            "id": self.id,
            "num": self.num,
            "long_name": self.long_name,
            "short_name": self.short_name,
            "hw_model": self.hw_model,
            "role": self.role,
            "snr": self.snr,
            "hops_away": self.hops_away,
            "battery_level": self.battery_level,
            "voltage": self.voltage,
            "channel_util": self.channel_util,
            "air_util_tx": self.air_util_tx,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "last_heard": self.last_heard.isoformat() if self.last_heard else None,
            "is_local": self.is_local,
            "is_favorite": self.is_favorite,
            "distance_km": self.distance_km,
            "temperature": self.temperature,
            "relative_humidity": self.relative_humidity,
            "barometric_pressure": self.barometric_pressure,
            "public_key": self.public_key,
            "is_licensed": self.is_licensed,
        }

    @classmethod
    def from_meshtastic_dict(cls, data: dict[str, Any], is_local: bool = False) -> NodeData:
        """Instantiate NodeData from a raw Meshtastic node dictionary."""
        return cls(**parse_node_fields(data), is_local=is_local, raw=data)


@dataclass
class MeshMessage:
    """Represents a message (broadcast or direct) exchanged over the mesh."""

    sender_id: str = ""  # e.g. "!45a466e4"
    sender_name: str = ""  # Display name or alias of sender
    receiver_id: str = "^all"  # e.g. "^all" or "!b8f862d9"
    text: str = ""  # Text message content
    channel: int | str = 0  # Channel index or channel name
    snr: float | None = None  # Signal-to-noise ratio
    hops: int | None = None  # Hops taken or hops away
    timestamp: datetime = field(default_factory=datetime.now)
    is_dm: bool = False  # True if direct message, False if broadcast
    sender_short_name: str | None = None
    recipient_name: str | None = None
    channel_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    # Legacy aliases kept as properties so existing call sites keep working;
    # the canonical field names are receiver_id / is_dm / hops.
    @property
    def recipient_id(self) -> str:
        """Alias for receiver_id."""
        return self.receiver_id

    @recipient_id.setter
    def recipient_id(self, value: str) -> None:
        self.receiver_id = value

    @property
    def is_direct(self) -> bool:
        """Alias for is_dm."""
        return self.is_dm

    @is_direct.setter
    def is_direct(self, value: bool) -> None:
        self.is_dm = value

    @property
    def hops_away(self) -> int | None:
        """Alias for hops."""
        return self.hops

    @hops_away.setter
    def hops_away(self, value: int | None) -> None:
        self.hops = value

    def to_dict(self) -> dict[str, Any]:
        """Convert MeshMessage to a plain dictionary using canonical key names."""
        return {
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "sender_short_name": self.sender_short_name,
            "receiver_id": self.receiver_id,
            "recipient_name": self.recipient_name,
            "text": self.text,
            "channel": self.channel,
            "channel_name": self.channel_name,
            "snr": self.snr,
            "hops": self.hops,
            "timestamp": self.timestamp.isoformat(),
            "is_dm": self.is_dm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeshMessage:
        """Rebuild a MeshMessage from a ``to_dict()`` payload or a history record.

        Unknown keys (e.g. the ``direction``/``recorded_at`` tags added by
        HistoryStore) are ignored, and the legacy ``recipient_id`` /
        ``is_direct`` / ``hops_away`` spellings written by older versions are
        still accepted so existing ``messages.jsonl`` files keep loading.
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = None
        elif not isinstance(timestamp, datetime):
            timestamp = None

        raw = data.get("raw")
        return cls(
            sender_id=data.get("sender_id", "") or "",
            sender_name=data.get("sender_name", "") or "",
            receiver_id=data.get("receiver_id") or data.get("recipient_id") or "^all",
            text=data.get("text", "") or "",
            channel=data.get("channel", 0),
            snr=data.get("snr"),
            hops=data.get("hops") if data.get("hops") is not None else data.get("hops_away"),
            timestamp=timestamp if timestamp is not None else datetime.now(),
            is_dm=bool(data["is_dm"] if "is_dm" in data else data.get("is_direct", False)),
            sender_short_name=data.get("sender_short_name"),
            recipient_name=data.get("recipient_name"),
            channel_name=data.get("channel_name"),
            raw=raw if isinstance(raw, dict) else {},
        )


@dataclass
class NeighborLink:
    """A single neighbor reported by a node's NeighborInfo broadcast."""

    node_id: str  # Neighbor node ID, e.g. "!45a466e4"
    snr: float | None = None  # SNR of the neighbor as heard by the reporter
    last_rx_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "snr": self.snr,
            "last_rx_time": self.last_rx_time.isoformat() if self.last_rx_time else None,
        }


@dataclass
class NeighborReport:
    """The neighbor table broadcast by one node (NEIGHBORINFO_APP)."""

    node_id: str
    neighbors: list[NeighborLink] = field(default_factory=list)
    broadcast_interval_secs: int | None = None
    received_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "neighbors": [n.to_dict() for n in self.neighbors],
            "broadcast_interval_secs": self.broadcast_interval_secs,
            "received_at": self.received_at.isoformat(),
        }


@dataclass
class TraceRouteResult:
    """The hop path returned by a TRACEROUTE_APP response."""

    target_id: str
    route_to: list[str] = field(default_factory=list)  # Node IDs, origin excluded
    snr_to: list[float] = field(default_factory=list)
    route_back: list[str] = field(default_factory=list)
    snr_back: list[float] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.now)

    @property
    def hop_count(self) -> int:
        """Number of intermediate hops on the forward path."""
        return len(self.route_to)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "route_to": list(self.route_to),
            "snr_to": list(self.snr_to),
            "route_back": list(self.route_back),
            "snr_back": list(self.snr_back),
            "hop_count": self.hop_count,
            "completed_at": self.completed_at.isoformat(),
        }


@dataclass
class DeviceConnectionInfo:
    """Connection and hardware identification details for a Meshtastic serial port."""

    port: str  # e.g. "/dev/ttyACM0"
    description: str  # e.g. "Heltec Vision Master E290 - TinyUSB CDC"
    hw_name: str  # Clean hardware model name e.g. "Heltec Vision Master E290"
    is_connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert DeviceConnectionInfo to a plain dictionary."""
        return {
            "port": self.port,
            "description": self.description,
            "hw_name": self.hw_name,
            "is_connected": self.is_connected,
        }
