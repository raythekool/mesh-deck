"""Auto-discovery and hardware detection for Meshtastic USB/serial devices."""

from __future__ import annotations

import logging
from typing import Final
import serial.tools.list_ports

from mesh_deck.core.events import DeviceConnectionInfo

logger = logging.getLogger(__name__)

# Known USB Vendor IDs used by Meshtastic devices and USB-UART bridges
KNOWN_MESHTASTIC_VIDS: Final[dict[int, str]] = {
    0x303A: "Espressif Systems",       # ESP32-S2/S3 (Heltec, LilyGo T-Deck, T-Beam S3, etc.)
    0x10C4: "Silicon Laboratories",   # CP210x (NodeMCU, T-Beam, Heltec V2)
    0x1A86: "QinHeng Electronics",    # CH340 / CH341 (Budget ESP32 & Arduino)
    0x0403: "FTDI",                   # Future Technology Devices (FT232 etc.)
    0x2E8A: "Raspberry Pi",           # RP2040 (Pico, Waveshare RP2040-LoRa)
    0x1915: "Nordic Semiconductor",   # nRF52840 (RAK4631, T-Echo)
    0x1366: "SEGGER Microcontroller", # J-Link onboard on devboards
}

# Substrings that strongly suggest a Meshtastic or compatible LoRa device
DESCRIPTIVE_KEYWORDS: Final[tuple[str, ...]] = (
    "heltec",
    "lilygo",
    "tlora",
    "t-lora",
    "tbeam",
    "t-beam",
    "techo",
    "t-echo",
    "meshtastic",
    "esp32",
    "wisblock",
    "rak",
    "station g1",
    "nano g1",
    "tracker",
    "e290",
    "vision master",
    "tinyusb cdc",
    "ch340",
    "cp210",
    "rp2040",
)


def _extract_clean_hw_name(port_info: serial.tools.list_ports_common.ListPortInfo) -> str:
    """Derive a friendly, concise hardware name from port metadata."""
    # 1. If product field is cleanly populated by USB descriptor, prefer it
    if port_info.product and port_info.product.strip() and port_info.product.strip().lower() != "n/a":
        product = port_info.product.strip()
        # Clean redundant suffixes like "- TinyUSB CDC" if present in product
        for suffix in (" - TinyUSB CDC", " TinyUSB CDC", " - CDC", " CDC"):
            if product.endswith(suffix):
                product = product[: -len(suffix)].strip()
        return product

    # 2. Extract from description
    desc = (port_info.description or "").strip()
    if desc and desc.lower() != "n/a":
        # Remove trailing protocol/CDC tags
        clean = desc
        for delim in (" - TinyUSB CDC", " - CDC", " (CDC)", " USB to UART Bridge Controller"):
            if delim in clean:
                clean = clean.split(delim)[0].strip()
        if clean:
            return clean

    # 3. Fallback based on known VID
    if port_info.vid in KNOWN_MESHTASTIC_VIDS:
        vendor = KNOWN_MESHTASTIC_VIDS[port_info.vid]
        return f"{vendor} Serial Device"

    return f"Meshtastic Device ({port_info.device})"


def scan_meshtastic_ports() -> list[DeviceConnectionInfo]:
    """Scan available system serial ports and detect connected Meshtastic devices.

    Inspects both hardware IDs (VID/PID) and textual descriptions to identify
    Meshtastic hardware (Heltec, LilyGo, RAK WisBlock, T-Beam, etc.).

    Returns:
        A list of DeviceConnectionInfo objects representing detected ports,
        sorted by device path (e.g. /dev/ttyACM0 before /dev/ttyACM1).
    """
    detected_devices: list[DeviceConnectionInfo] = []

    try:
        available_ports = serial.tools.list_ports.comports()
    except Exception as exc:
        logger.error("Failed to list serial ports: %s", exc)
        return []

    for port_info in available_ports:
        device_path = port_info.device

        # Skip motherboard standard UARTs (/dev/ttyS*) without valid USB VID
        if device_path.startswith("/dev/ttyS") and port_info.vid is None:
            continue

        is_meshtastic_candidate = False

        # 1. Check VID against known Meshtastic / MCU vendors
        if port_info.vid is not None and port_info.vid in KNOWN_MESHTASTIC_VIDS:
            is_meshtastic_candidate = True

        # 2. Check textual descriptors (description, product, manufacturer, hwid)
        combined_text = (
            f"{port_info.description or ''} "
            f"{port_info.manufacturer or ''} "
            f"{port_info.product or ''} "
            f"{port_info.hwid or ''}"
        ).lower()

        if any(keyword in combined_text for keyword in DESCRIPTIVE_KEYWORDS):
            is_meshtastic_candidate = True

        if is_meshtastic_candidate:
            hw_name = _extract_clean_hw_name(port_info)
            description = (port_info.description or hw_name).strip()

            detected_devices.append(
                DeviceConnectionInfo(
                    port=device_path,
                    description=description,
                    hw_name=hw_name,
                    is_connected=False,
                )
            )

    # Sort ports naturally (e.g. /dev/ttyACM0, /dev/ttyACM1)
    detected_devices.sort(key=lambda dev: dev.port)
    return detected_devices


if __name__ == "__main__":
    devices = scan_meshtastic_ports()
    print(f"Found {len(devices)} Meshtastic candidate port(s):")
    for dev in devices:
        print(f"  • {dev.port}: {dev.hw_name} ({dev.description})")
