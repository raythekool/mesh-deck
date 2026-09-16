"""Domain events and data models for Meshtastic network state and messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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

    def __init__(
        self,
        id: str,
        num: int = 0,
        long_name: str = "",
        short_name: str = "",
        hw_model: str = "",
        role: str = "CLIENT",
        snr: float | None = None,
        hops_away: int | None = None,
        battery_level: int | None = None,
        voltage: float | None = None,
        channel_util: float | None = None,
        air_util_tx: float | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        altitude: float | None = None,
        last_heard: datetime | None = None,
        is_local: bool = False,
        is_favorite: bool = False,
        distance_km: float | None = None,
        temperature: float | None = None,
        relative_humidity: float | None = None,
        barometric_pressure: float | None = None,
        public_key: str | None = None,
        region: str | None = None,
        modem_preset: str | None = None,
        is_licensed: bool = False,
        raw: dict[str, Any] | None = None,
        hardware: str | None = None,
        channel_utilization: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.id = id
        self.num = num
        self.long_name = long_name
        self.short_name = short_name
        self.hw_model = hardware if hardware is not None else hw_model
        self.role = role
        self.snr = snr
        self.hops_away = hops_away
        self.battery_level = battery_level
        self.voltage = voltage
        self.channel_util = channel_utilization if channel_utilization is not None else channel_util
        self.air_util_tx = air_util_tx
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.last_heard = last_heard
        self.is_local = is_local
        self.is_favorite = is_favorite
        self.distance_km = distance_km
        self.temperature = temperature
        self.relative_humidity = relative_humidity
        self.barometric_pressure = barometric_pressure
        self.public_key = public_key
        self.region = region
        self.modem_preset = modem_preset
        self.is_licensed = is_licensed
        self.raw = raw or {}

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
        user = data.get("user", {})
        pos = data.get("position", {})
        dev_metrics = data.get("deviceMetrics", {})
        env_metrics = data.get("environmentMetrics", {})

        num = data.get("num")
        node_id = user.get("id") or (f"!{num:08x}" if num is not None else "!unknown")
        if num is None and node_id.startswith("!"):
            try:
                num = int(node_id[1:], 16)
            except ValueError:
                num = 0

        last_heard_ts = data.get("lastHeard")
        last_heard_dt = (
            datetime.fromtimestamp(last_heard_ts)
            if isinstance(last_heard_ts, (int, float)) and last_heard_ts > 0
            else None
        )

        lat = pos.get("latitude")
        lon = pos.get("longitude")
        if lat is None and "latitudeI" in pos and pos["latitudeI"] is not None:
            lat = float(pos["latitudeI"] * 1e-7)
        if lon is None and "longitudeI" in pos and pos["longitudeI"] is not None:
            lon = float(pos["longitudeI"] * 1e-7)

        return cls(
            id=node_id,
            num=int(num or 0),
            long_name=user.get("longName", "") or "",
            short_name=user.get("shortName", "") or "",
            hw_model=str(user.get("hwModel", "UNSET")),
            role=str(user.get("role", "CLIENT")),
            snr=float(data["snr"]) if data.get("snr") is not None else None,
            hops_away=int(data["hopsAway"]) if data.get("hopsAway") is not None else None,
            battery_level=int(dev_metrics["batteryLevel"]) if dev_metrics.get("batteryLevel") is not None else None,
            voltage=float(dev_metrics["voltage"]) if dev_metrics.get("voltage") is not None else None,
            channel_util=float(dev_metrics["channelUtilization"]) if dev_metrics.get("channelUtilization") is not None else None,
            air_util_tx=float(dev_metrics["airUtilTx"]) if dev_metrics.get("airUtilTx") is not None else None,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            altitude=float(pos["altitude"]) if pos.get("altitude") is not None else None,
            last_heard=last_heard_dt,
            is_local=is_local,
            is_favorite=bool(data.get("isFavorite", False)),
            temperature=float(env_metrics["temperature"]) if env_metrics.get("temperature") is not None else None,
            relative_humidity=float(env_metrics["relativeHumidity"]) if env_metrics.get("relativeHumidity") is not None else None,
            barometric_pressure=float(env_metrics["barometricPressure"]) if env_metrics.get("barometricPressure") is not None else None,
            public_key=user.get("publicKey"),
            is_licensed=bool(user.get("isLicensed", False)),
            raw=data,
        )


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

    def __init__(
        self,
        sender_id: str = "",
        sender_name: str = "",
        receiver_id: str = "^all",
        text: str = "",
        channel: int | str = 0,
        snr: float | None = None,
        hops: int | None = None,
        timestamp: datetime | None = None,
        is_dm: bool = False,
        sender_short_name: str | None = None,
        recipient_name: str | None = None,
        channel_name: str | None = None,
        raw: dict[str, Any] | None = None,
        recipient_id: str | None = None,
        is_direct: bool | None = None,
        hops_away: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.receiver_id = recipient_id if recipient_id is not None else receiver_id
        self.text = text
        self.channel = channel
        self.snr = snr
        self.hops = hops_away if hops_away is not None else hops
        self.timestamp = timestamp if timestamp is not None else datetime.now()
        self.is_dm = is_direct if is_direct is not None else is_dm
        self.sender_short_name = sender_short_name
        self.recipient_name = recipient_name
        self.channel_name = channel_name
        self.raw = raw or {}

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
        """Convert MeshMessage to a plain dictionary."""
        return {
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "sender_short_name": self.sender_short_name,
            "receiver_id": self.receiver_id,
            "recipient_id": self.receiver_id,
            "recipient_name": self.recipient_name,
            "text": self.text,
            "channel": self.channel,
            "channel_name": self.channel_name,
            "snr": self.snr,
            "hops": self.hops,
            "hops_away": self.hops,
            "timestamp": self.timestamp.isoformat(),
            "is_dm": self.is_dm,
            "is_direct": self.is_dm,
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
