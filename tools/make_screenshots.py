"""Regenerate the SVG screenshots embedded in README.md.

Run with ``uv run python tools/make_screenshots.py``. Everything is rendered
from fixed sample data with no radio attached, so the output only changes when
the UI does. Pass ``--theme <name>`` to render a different palette.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mesh_deck.core.events import MeshMessage, NodeData  # noqa: E402
from mesh_deck.core.node_store import NodeStore  # noqa: E402
from mesh_deck.ui.banner import render_banner  # noqa: E402
from mesh_deck.ui.tables import (  # noqa: E402
    render_message,
    render_node_detail,
    render_nodes_table,
)
from mesh_deck.ui.theme import DEFAULT_THEME, set_theme, theme_names  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots"
CONSOLE_WIDTH = 132
NOW = datetime(2026, 3, 14, 9, 30, 0)


def _sample_nodes() -> list[NodeData]:
    """Fixed node set: local node plus a spread of roles, links and telemetry."""
    return [
        NodeData(
            id="!45a466e4", num=1168402148,
            long_name="Morpheus Command Node", short_name="MRPH",
            hw_model="HELTEC_VISION_MASTER_E290", role="CLIENT",
            hops_away=0, battery_level=101, voltage=4.18,
            channel_util=12.4, air_util_tx=1.8,
            latitude=45.46420, longitude=9.19000, altitude=140.0,
            last_heard=NOW - timedelta(seconds=12), is_local=True,
            region="EU_868", modem_preset="MEDIUM_FAST",
            temperature=23.4, relative_humidity=48.0, barometric_pressure=1013.2,
            public_key="jDk0rN1s4mQ7xVb2PfE9wYt5Lq8cZaH3Rn6Uo0Ki", is_licensed=True,
        ),
        NodeData(
            id="!62d927b8", num=1658398648,
            long_name="Trinity Recon Scout", short_name="TRIN",
            hw_model="TLORA_T3_S3", role="TRACKER",
            snr=9.5, hops_away=0, battery_level=87, voltage=4.02,
            latitude=45.47510, longitude=9.20880, altitude=132.0,
            last_heard=NOW - timedelta(minutes=3),
        ),
        NodeData(
            id="!b8f862d9", num=3103285977,
            long_name="Zion Relay Tower", short_name="ZION",
            hw_model="RAK4631", role="ROUTER",
            snr=2.1, hops_away=1, battery_level=64, voltage=3.88,
            channel_util=21.7, air_util_tx=3.4,
            latitude=45.53100, longitude=9.25600, altitude=310.0,
            last_heard=NOW - timedelta(minutes=27),
            temperature=11.8, relative_humidity=71.0, barometric_pressure=978.4,
        ),
        NodeData(
            id="!1a2b3c4d", num=439041101,
            long_name="Niobe Field Repeater", short_name="NIOB",
            hw_model="TBEAM_V1_2", role="REPEATER",
            snr=-6.5, hops_away=2, battery_level=28, voltage=3.61,
            latitude=45.61200, longitude=9.41000,
            last_heard=NOW - timedelta(hours=2, minutes=10),
        ),
        NodeData(
            id="!7fe10c93", num=2145356947,
            long_name="Oracle Weather Sensor", short_name="ORCL",
            hw_model="HELTEC_V3", role="SENSOR",
            snr=-12.8, hops_away=3, voltage=3.42,
            last_heard=NOW - timedelta(days=1, hours=4),
        ),
    ]


def _sample_store() -> NodeStore:
    store = NodeStore()
    for node in _sample_nodes():
        store.update_node(node)
    store.set_local_node_id("!45a466e4")
    return store


def _sample_channels() -> list[dict[str, object]]:
    return [
        {"index": 0, "name": "LongFast", "role": "PRIMARY",
         "uplink_enabled": True, "downlink_enabled": True, "has_psk": False},
        {"index": 1, "name": "Ops", "role": "SECONDARY",
         "uplink_enabled": False, "downlink_enabled": True, "has_psk": True},
    ]


def _sample_messages() -> list[MeshMessage]:
    return [
        MeshMessage(
            sender_id="!62d927b8", sender_name="Trinity Recon Scout", sender_short_name="TRIN",
            receiver_id="^all", text="Perimetro nord libero, proseguo verso il ripetitore.",
            channel=0, channel_name="LongFast", snr=9.5, hops=0,
            timestamp=NOW - timedelta(minutes=6), is_dm=False,
        ),
        MeshMessage(
            sender_id="!b8f862d9", sender_name="Zion Relay Tower", sender_short_name="ZION",
            receiver_id="^all", text="Ricevuto. Carico canale al 21%, nessuna congestione.",
            channel=0, channel_name="LongFast", snr=2.1, hops=1,
            timestamp=NOW - timedelta(minutes=4), is_dm=False,
        ),
        MeshMessage(
            sender_id="!62d927b8", sender_name="Trinity Recon Scout", sender_short_name="TRIN",
            receiver_id="!45a466e4", recipient_name="Morpheus Command Node",
            text="Coordinate del punto di incontro confermate. Batteria all'87%.",
            channel=0, snr=9.5, hops=0,
            timestamp=NOW - timedelta(minutes=2), is_dm=True,
        ),
    ]


def _console() -> Console:
    # Recording console; output is captured as SVG, never printed to a terminal.
    return Console(record=True, width=CONSOLE_WIDTH, file=io.StringIO())


def _save(console: Console, name: str, title: str) -> None:
    path = OUTPUT_DIR / f"{name}.svg"
    console.save_svg(str(path), title=title)
    print(f"  wrote {path.relative_to(REPO_ROOT).as_posix()}")


def render_rich_screenshots() -> None:
    """Banner, node table, node dossier and message stream (Rich surfaces)."""
    store = _sample_store()
    nodes = store.get_all_nodes(sort_by="last_heard")
    local = store.get_local_node()

    console = _console()
    console.print(render_banner(local, port="/dev/ttyACM0", channels=_sample_channels()))
    _save(console, "banner", "mesh-deck — /banner")

    console = _console()
    console.print(render_nodes_table(nodes, local_node_id=local.id))
    _save(console, "nodes_table", "mesh-deck — /nodes")

    target = store.get_node("ZION")
    console = _console()
    console.print(render_node_detail(
        target,
        distance_km=store.calculate_distance(local.id, target.id),
        bearing_deg=store.calculate_bearing(local.id, target.id),
    ))
    _save(console, "node_detail", "mesh-deck — /node ZION")

    console = _console()
    for msg in _sample_messages():
        console.print(render_message(msg))
    _save(console, "messaging", "mesh-deck — message stream")


def _fake_client(store: NodeStore) -> MagicMock:
    client = MagicMock()
    client.store = store
    client.node_store = store
    client.port = "/dev/ttyACM0"
    client.is_connected = True
    client.get_local_node.return_value = store.get_local_node()
    client.get_channels.return_value = _sample_channels()
    client.get_neighbor_reports.return_value = []
    client.history = None
    client._callbacks = []
    client.on_message_received.side_effect = client._callbacks.append
    client.off_message_received.side_effect = lambda cb: client._callbacks.remove(cb)
    return client


async def render_textual_screenshots() -> None:
    """Main console and chat viewer (Textual surfaces)."""
    from mesh_deck.core.settings import Settings
    from mesh_deck.ui.channel_chat import ChannelChatApp
    from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL

    store = _sample_store()

    settings = Settings()
    settings.save = lambda: True  # never touch the user's real config
    repl = MeshDeckREPL(_fake_client(store), settings=settings)
    app = MeshDeckApp(repl)
    async with app.run_test(size=(CONSOLE_WIDTH, 40)) as pilot:
        await pilot.pause()
        repl.dispatcher.cmd_banner([])
        for msg in _sample_messages():
            app.write_output(render_message(msg))
        app.refresh_sidebar()
        await pilot.pause()
        app.show_node_detail("!62d927b8")
        await pilot.pause()
        (OUTPUT_DIR / "console.svg").write_text(app.export_screenshot(), encoding="utf-8")
        print("  wrote docs/screenshots/console.svg")

    chat = ChannelChatApp(_fake_client(store))
    async with chat.run_test(size=(CONSOLE_WIDTH, 40)) as pilot:
        await pilot.pause()
        screen = chat.screen
        for msg in _sample_messages():
            screen._handle_message(msg)
        screen._unread["dm"] = 1
        screen._refresh_channel_list()
        screen._render_selected()
        await pilot.pause()
        (OUTPUT_DIR / "chat.svg").write_text(chat.export_screenshot(), encoding="utf-8")
        print("  wrote docs/screenshots/chat.svg")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=theme_names(), default=DEFAULT_THEME)
    args = parser.parse_args()

    set_theme(args.theme)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Rendering screenshots with the '{args.theme}' theme:")
    render_rich_screenshots()
    asyncio.run(render_textual_screenshots())
    return 0


if __name__ == "__main__":
    sys.exit(main())
