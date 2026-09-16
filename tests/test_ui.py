"""Unit tests for the Mesh-Deck UI layer using Python standard library unittest.

Covers theme formatters, banner, tables, detail dossiers, messages, and completer edge cases.
"""

import io
import math
import unittest
from datetime import datetime, timedelta, timezone

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mesh_deck.models import MeshMessage, NodeData
from mesh_deck.ui import (
    CYBERPUNK_THEME,
    MeshDeckCompleter,
    SLASH_COMMANDS,
    THEME_COLORS,
    format_battery,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
    render_banner,
    render_message,
    render_node_detail,
    render_nodes_table,
)


class TestThemeFormatters(unittest.TestCase):
    """Test Rich styling badge helper functions and all edge cases."""

    def test_format_snr(self):
        self.assertIn("#00ff66", format_snr(8.5))
        self.assertIn("+8.5 dB", format_snr(8.5))

        self.assertIn("#00f3ff", format_snr(2.4))
        self.assertIn("+2.4 dB", format_snr(2.4))

        self.assertIn("#ffb800", format_snr(-5.0))
        self.assertIn("-5.0 dB", format_snr(-5.0))

        self.assertIn("#ff3366", format_snr(-15.2))
        self.assertIn("-15.2 dB", format_snr(-15.2))

        self.assertIn("-- dB", format_snr(None))

    def test_format_snr_edge_cases(self):
        # Exact boundary 0.0 dB
        res_zero = format_snr(0.0)
        self.assertIn("+0.0 dB", res_zero)
        self.assertIn("#00f3ff", res_zero)

        # Exact boundary 5.0 dB
        res_five = format_snr(5.0)
        self.assertIn("+5.0 dB", res_five)
        self.assertIn("#00ff66", res_five)

        # Exact boundary -10.0 dB
        res_minus_ten = format_snr(-10.0)
        self.assertIn("-10.0 dB", res_minus_ten)
        self.assertIn("#ffb800", res_minus_ten)

        # Extreme values
        self.assertIn("-25.0 dB", format_snr(-25.0))
        self.assertIn("+20.0 dB", format_snr(20.0))

        # NaN & Inf
        self.assertIn("-- dB", format_snr(float("nan")))
        self.assertIn("+inf dB", format_snr(float("inf")))
        self.assertIn("-inf dB", format_snr(-float("inf")))

        # Non-numeric or invalid string
        self.assertIn("-- dB", format_snr("invalid"))  # type: ignore

    def test_format_battery(self):
        # Battery percentage thresholds
        self.assertIn("#00ff66", format_battery(85, 4.10))
        self.assertIn("85%", format_battery(85, 4.10))
        self.assertIn("4.10V", format_battery(85, 4.10))

        self.assertIn("#ffb800", format_battery(50, 3.80))
        self.assertIn("50%", format_battery(50, 3.80))

        self.assertIn("#ff3366", format_battery(20, 3.45))
        self.assertIn("20%", format_battery(20, 3.45))

        # Powered / USB
        usb_batt = format_battery(101, 4.25)
        self.assertIn("⚡", usb_batt)
        self.assertIn("USB", usb_batt)

        # Voltage only
        volt_batt = format_battery(None, 4.20)
        self.assertIn("⚡", volt_batt)
        self.assertIn("4.20V", volt_batt)

        # None
        self.assertIn("--", format_battery(None, None))

    def test_format_battery_edge_cases(self):
        # Exactly 0% and 100%
        b0 = format_battery(0, 3.20)
        self.assertIn("0%", b0)
        self.assertIn("#ff3366", b0)

        b100 = format_battery(100, 4.20)
        self.assertIn("100%", b100)
        self.assertIn("#00ff66", b100)

        # Overcharged / USB indicator without voltage
        b_usb = format_battery(105, None)
        self.assertIn("⚡ USB", b_usb)

        # Battery level only, voltage is None
        b_novolt = format_battery(55, None)
        self.assertIn("55%", b_novolt)
        self.assertNotIn("V", b_novolt)

        # Voltage only tier boundaries
        self.assertIn("⚡ 4.25V", format_battery(None, 4.25))
        self.assertIn("3.90V", format_battery(None, 3.90))
        self.assertIn("3.70V", format_battery(None, 3.70))
        self.assertIn("3.30V", format_battery(None, 3.30))

        # Anomalous / negative voltage or NaN
        self.assertIn("50%", format_battery(50, -1.0))
        self.assertIn("50%", format_battery(50, float("nan")))
        self.assertIn("--", format_battery(None, -3.5))

    def test_format_role(self):
        self.assertIn("ROUTER", format_role("ROUTER"))
        self.assertIn("#ff007f", format_role("ROUTER"))

        self.assertIn("CLIENT", format_role("CLIENT"))
        self.assertIn("#00ff66", format_role("client"))

        self.assertIn("REPEATER", format_role("REPEATER"))
        self.assertIn("#ffb800", format_role("REPEATER"))

        self.assertIn("TRACKER", format_role("TRACKER"))
        self.assertIn("#00f3ff", format_role("TRACKER"))

        self.assertIn("CUSTOM_ROLE", format_role("CUSTOM_ROLE"))

    def test_format_role_all_types(self):
        # All Meshtastic role types
        roles = [
            "ROUTER", "ROUTER_CLIENT", "REPEATER", "CLIENT",
            "CLIENT_MUTE", "TRACKER", "SENSOR", "TAK",
            "TAK_TRACKER", "LOST_AND_FOUND"
        ]
        for r in roles:
            formatted = format_role(r)
            self.assertIn(r.replace("_", "")[:4], formatted.replace("_", ""))

        # None or empty
        self.assertIn("CLIENT", format_role(None))
        self.assertIn("CLIENT", format_role(""))
        self.assertIn("CLIENT", format_role("   "))

        # Unknown custom role
        res_unk = format_role("EXT_RELAY_NODE")
        self.assertIn("EXT_RELAY_NODE", res_unk)

    def test_format_time_ago(self):
        now = datetime.now()
        self.assertIn("s fa", format_time_ago(now - timedelta(seconds=20)))
        self.assertIn("m fa", format_time_ago(now - timedelta(minutes=15)))
        self.assertIn("h fa", format_time_ago(now - timedelta(hours=4)))
        self.assertIn("d fa", format_time_ago(now - timedelta(days=3)))
        self.assertIn("mai", format_time_ago(None))

    def test_format_time_ago_edge_cases(self):
        now = datetime.now()
        # Future skew protection
        self.assertEqual(format_time_ago(now + timedelta(seconds=30)), "[bold #00ff66]0s fa[/bold #00ff66]")

        # Far past (months/years)
        self.assertIn("150d fa", format_time_ago(now - timedelta(days=150)))

        # Timezone aware datetime
        utc_now = datetime.now(timezone.utc)
        self.assertIn("s fa", format_time_ago(utc_now - timedelta(seconds=45)))
        self.assertIn("m fa", format_time_ago(utc_now - timedelta(minutes=10)))

    def test_format_hops(self):
        self.assertIn("Diretto (0)", format_hops(0))
        self.assertIn("1 hop", format_hops(1))
        self.assertIn("3 hops", format_hops(3))
        self.assertIn("--", format_hops(None))

    def test_format_distance(self):
        self.assertEqual("750 m", format_distance(0.75))
        self.assertEqual("3.45 km", format_distance(3.45))
        self.assertEqual("25.0 km", format_distance(25.02))
        self.assertIn("--", format_distance(None))

    def test_format_distance_edge_cases(self):
        self.assertEqual("0 m", format_distance(0.0))
        self.assertEqual("50 m", format_distance(0.05))
        self.assertEqual("999 m", format_distance(0.999))
        self.assertEqual("1.00 km", format_distance(1.0))
        self.assertEqual("9.99 km", format_distance(9.99))
        self.assertEqual("10.0 km", format_distance(10.0))
        self.assertEqual("125.4 km", format_distance(125.43))

        # Negative or invalid
        self.assertEqual("[dim]--[/dim]", format_distance(-5.0))
        self.assertEqual("[dim]--[/dim]", format_distance(float("nan")))
        self.assertEqual("[dim]--[/dim]", format_distance(float("inf")))
        self.assertEqual("[dim]--[/dim]", format_distance("invalid"))  # type: ignore


class TestBanner(unittest.TestCase):
    """Test tactical status banner rendering with various configurations and edge cases."""

    def test_render_banner_with_node(self):
        node = NodeData(
            id="!45a466e4",
            num=1168467684,
            long_name="Heltec Master",
            short_name="HMST",
            hardware="HELTEC_V3",
            role="CLIENT",
            battery_level=90,
            voltage=4.12,
            channel_utilization=8.5,
        )
        channels = [{"index": 0, "name": "Primary", "modem": "LongFast"}]
        panel = render_banner(node, port="/dev/ttyACM0", channels=channels)

        self.assertIsInstance(panel, Panel)
        self.assertIn("MESH-DECK // TACTICAL CONSOLE", str(panel.title))

    def test_render_banner_disconnected(self):
        panel = render_banner(None, port="/dev/ttyACM0")
        self.assertIsInstance(panel, Panel)
        buf = io.StringIO()
        c = Console(file=buf)
        c.print(panel)
        self.assertIn("IN CONNESSIONE", buf.getvalue())

    def test_render_banner_edge_cases(self):
        # Long node name with emojis and markup-like syntax
        node = NodeData(
            id="!abcdef12",
            long_name="Tactical Rover 🏎️💨 [ALPHA_TEAM] (Special Ops) 🎯",
            short_name="RC01",
            hardware="HELTEC_VISION_MASTER_E290_V3",
            role="ROUTER",
            battery_level=18,
            voltage=3.45,
            region="US_915",
            modem_preset="SHORT_FAST",
            channel_utilization=82.4,
        )
        channels = [
            {"index": 0, "name": "Main", "modem": "ShortFast"},
            {"index": 1, "name": "Telemetry [Private]", "modem": None},
            {"index": 2, "name": "", "modem": "LongFast"},  # Unnamed channel
        ]
        panel = render_banner(node, port="/dev/ttyUSB99", channels=channels)
        buf = io.StringIO()
        c = Console(file=buf)
        c.print(panel)
        output = buf.getvalue()

        self.assertIn("Tactical Rover", output)
        self.assertIn("!abcdef12", output)
        self.assertIn("/dev/ttyUSB99", output)
        self.assertIn("US_915", output)
        self.assertIn("#Main", output)
        self.assertIn("#Ch_2", output)


class TestTablesAndViews(unittest.TestCase):
    """Test tables and analytical view rendering with extensive edge cases."""

    def setUp(self):
        self.sample_nodes = [
            NodeData(
                id="!45a466e4",
                long_name="Local Heltec",
                short_name="HELT",
                hardware="HELTEC_V3",
                role="CLIENT",
                snr=6.2,
                hops_away=0,
                battery_level=95,
                voltage=4.15,
            ),
            NodeData(
                id="!78b211a0",
                long_name="Remote LilyGo",
                short_name="LILY",
                hardware="TLORA_V2",
                role="ROUTER",
                snr=-4.0,
                hops_away=2,
                battery_level=60,
                voltage=3.85,
                distance_km=8.4,
                latitude=45.4642,
                longitude=9.1900,
                altitude=120.0,
            ),
        ]

    def test_render_nodes_table(self):
        table = render_nodes_table(self.sample_nodes, local_node_id="!45a466e4")
        self.assertIsInstance(table, Table)
        self.assertEqual(len(table.rows), 2)
        self.assertIn("NODI NELLA MESH", str(table.title))

    def test_render_nodes_table_empty(self):
        table = render_nodes_table([], local_node_id=None)
        self.assertIsInstance(table, Table)
        self.assertEqual(len(table.rows), 0)
        self.assertIn("0 rilevati", str(table.title))

        buf = io.StringIO()
        Console(file=buf).print(table)
        self.assertIn("Nome Nodo", buf.getvalue())

    def test_render_nodes_table_single(self):
        table = render_nodes_table([self.sample_nodes[0]], local_node_id="!45a466e4")
        self.assertEqual(len(table.rows), 1)

    def test_render_nodes_table_many_nodes(self):
        # Render table with 120 nodes to ensure scalability
        many_nodes = [
            NodeData(
                id=f"!node{i:04x}",
                num=1000 + i,
                long_name=f"Repeater Node {i:03d}",
                short_name=f"R{i:03d}",
                hardware="RAK4631",
                role="REPEATER" if i % 2 == 0 else "CLIENT",
                snr=float(10 - (i % 25)),
                hops_away=i % 4,
                battery_level=80,
                voltage=3.95,
            )
            for i in range(120)
        ]
        table = render_nodes_table(many_nodes)
        self.assertEqual(len(table.rows), 120)

        buf = io.StringIO()
        Console(file=buf).print(table)
        self.assertIn("120", buf.getvalue())

    def test_render_nodes_table_emoji_and_long_names(self):
        exotic_nodes = [
            NodeData(
                id="!11111111",
                long_name="Banana Mode 🍌 Node [EXPERIMENTAL_STATION] High Mountain",
                short_name="🍌BAN",
                hardware="TBEAM_V1_2",
                role="ROUTER",
            ),
            NodeData(
                id="!22222222",
                long_name="TBeam Vaiano 🎯🇮🇹 [UPLINK] Station",
                short_name="VAI🎯",
                hardware="TLORA_T3S3",
                role="CLIENT",
            ),
            NodeData(
                id="!33333333",
                long_name="Portofino 🏖️ 🚤 [SEASIDE_GATEWAY]",
                short_name="PORT",
                hardware="HELTEC_V3",
                role="SENSOR",
            ),
        ]
        table = render_nodes_table(exotic_nodes)
        buf = io.StringIO()
        Console(file=buf).print(table)
        output = buf.getvalue()

        self.assertIn("Banana Mode 🍌", output)
        self.assertIn("TBeam Vaiano", output)
        self.assertIn("Portofino", output)

    def test_render_node_detail_sparse(self):
        # Node with minimal information (no GPS, no telemetry, no battery)
        sparse_node = NodeData(
            id="!00000001",
            long_name="Minimal Node",
            short_name="MINI",
            hardware="UNSET",
        )
        panel = render_node_detail(sparse_node)
        self.assertIsInstance(panel, Panel)

        buf = io.StringIO()
        Console(file=buf).print(panel)
        output = buf.getvalue()

        self.assertIn("MINI", output)
        self.assertIn("!00000001", output)
        self.assertIn("Non disponibili", output)

    def test_render_node_detail_full(self):
        full_node = NodeData(
            id="!78b211a0",
            num=2024935840,
            long_name="Full Telemetry Base Station",
            short_name="BASE",
            hardware="HELTEC_VISION_MASTER_E290",
            role="ROUTER",
            snr=9.5,
            hops_away=0,
            battery_level=98,
            voltage=4.18,
            channel_utilization=12.5,
            air_util_tx=2.1,
            latitude=45.4642,
            longitude=9.1900,
            altitude=150.0,
            distance_km=4.2,
            temperature=22.5,
            relative_humidity=45.0,
            barometric_pressure=1013.25,
            public_key="0123456789abcdef0123456789abcdef",
            is_licensed=True,
            last_heard=datetime.now() - timedelta(minutes=2),
        )
        panel = render_node_detail(full_node, distance_km=4.2)
        buf = io.StringIO()
        Console(file=buf).print(panel)
        output = buf.getvalue()

        self.assertIn("BASE", output)
        self.assertIn("22.5 °C", output)
        self.assertIn("45.0%", output)
        self.assertIn("1013.2 hPa", output)
        self.assertIn("45.46420, 9.19000", output)
        self.assertIn("openstreetmap.org", output)
        self.assertIn("Amateur Radio", output)

    def test_render_broadcast_message(self):
        msg = MeshMessage(
            text="Hello mesh network!",
            sender_id="!45a466e4",
            sender_name="Local Heltec",
            channel=0,
            channel_name="Primary",
            snr=5.0,
        )
        rendered = render_message(msg)
        self.assertIsInstance(rendered, Text)
        self.assertIn("Hello mesh network!", rendered.plain)
        self.assertIn("Local Heltec", rendered.plain)
        self.assertIn("#Primary", rendered.plain)

    def test_render_direct_message(self):
        msg = MeshMessage(
            text="Secret ping message",
            sender_id="!45a466e4",
            sender_name="Local Heltec",
            recipient_id="!78b211a0",
            recipient_name="Remote LilyGo",
            is_direct=True,
            snr=7.5,
        )
        rendered = render_message(msg)
        self.assertIsInstance(rendered, Panel)
        self.assertIn("MESSAGGIO DIRETTO", str(rendered.title))
        buf = io.StringIO()
        Console(file=buf).print(rendered)
        self.assertIn("Secret ping message", buf.getvalue())

    def test_render_message_edge_cases(self):
        # 1. Empty message text
        msg_empty = MeshMessage(text="", sender_id="!11223344", sender_name="Ghost")
        rendered_empty = render_message(msg_empty)
        self.assertIsInstance(rendered_empty, Text)

        # 2. Very long message text (> 600 chars)
        long_body = "Sensors: OK. " * 50
        msg_long = MeshMessage(text=long_body, sender_id="!11223344", sender_name="SensorBase")
        rendered_long = render_message(msg_long)
        self.assertIn("Sensors: OK.", rendered_long.plain)

        # 3. Message containing dangerous Rich markup syntax
        msg_markup = MeshMessage(
            text="Dangerous text: [/closing_tag] and [bold] unclosed [not_a_tag]",
            sender_id="!11223344",
            sender_name="Hacker [TAG]",
            is_direct=True,
        )
        panel_markup = render_message(msg_markup)
        buf = io.StringIO()
        Console(file=buf).print(panel_markup)
        self.assertIn("[/closing_tag]", buf.getvalue())

        # 4. Unknown sender and recipient
        msg_unknown = MeshMessage(text="Ping", sender_id="", is_direct=True)
        panel_unknown = render_message(msg_unknown)
        buf_unk = io.StringIO()
        Console(file=buf_unk).print(panel_unknown)
        self.assertIn("Sconosciuto", buf_unk.getvalue())


class TestCompleter(unittest.TestCase):
    """Test interactive prompt_toolkit autocompletion and edge cases."""

    def setUp(self):
        self.nodes = [
            NodeData(
                id="!45a466e4",
                long_name="Heltec Alpha",
                short_name="ALPHA",
                role="CLIENT",
                snr=5.0,
            ),
            NodeData(
                id="!78b211a0",
                long_name="Bravo Station",
                short_name="BRAVO",
                role="ROUTER",
                snr=-2.0,
            ),
            NodeData(
                id="!99c345f1",
                long_name="Mount Vaiano Repeater",
                short_name="Vaiano 1",
                role="REPEATER",
            ),
            NodeData(
                id="!12a344d9",
                long_name="Target Italian Scout",
                short_name="🎯IT",
                role="TRACKER",
            ),
        ]
        self.ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"]
        self.completer = MeshDeckCompleter(get_nodes=self.nodes, get_ports=self.ports)

    def test_slash_command_completion(self):
        doc = Document("/n")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("/nodes", texts)
        self.assertIn("/node", texts)
        self.assertNotIn("/dm", texts)

    def test_completer_empty_or_whitespace_input(self):
        # Empty text yields no completions
        doc_empty = Document("")
        completions_empty = list(self.completer.get_completions(doc_empty, CompleteEvent()))
        self.assertEqual(len(completions_empty), 0)

        # Whitespace-only yields no completions
        doc_spaces = Document("    ")
        completions_spaces = list(self.completer.get_completions(doc_spaces, CompleteEvent()))
        self.assertEqual(len(completions_spaces), 0)

    def test_completer_leading_spaces(self):
        # Command with leading whitespace should autocomplete correctly
        doc = Document("   /sw")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("/switch", texts)

    def test_node_target_completion(self):
        doc = Document("/node AL")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("ALPHA", texts)
        self.assertNotIn("BRAVO", texts)

    def test_dm_target_completion(self):
        doc = Document("/dm BR")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("BRAVO", texts)

        # After target is entered and space is typed, do not suggest nodes
        doc_msg = Document("/dm BRAVO Ciao come stai")
        completions_msg = list(self.completer.get_completions(doc_msg, CompleteEvent()))
        self.assertEqual(len(completions_msg), 0)

    def test_completer_names_with_spaces_and_emoji(self):
        # Autocompleting a short name with spaces should wrap in quotes
        doc = Document("/node Vai")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn('"Vaiano 1"', texts)

        # Autocompleting with emoji
        doc_emoji = Document("/node 🎯")
        completions_emoji = list(self.completer.get_completions(doc_emoji, CompleteEvent()))
        texts_emoji = [c.text for c in completions_emoji]
        self.assertIn("🎯IT", texts_emoji)

    def test_completer_with_open_quotes(self):
        # User starts typing with a quote: /node "Vai
        doc = Document('/node "Vai')
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn('"Vaiano 1"', texts)

    def test_switch_port_completion(self):
        doc = Document("/switch /dev/ttyA")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("/dev/ttyACM0", texts)
        self.assertIn("/dev/ttyACM1", texts)
        self.assertNotIn("/dev/ttyUSB0", texts)

        # Empty query after /switch
        doc_all = Document("/switch ")
        completions_all = list(self.completer.get_completions(doc_all, CompleteEvent()))
        self.assertEqual(len(completions_all), 3)


if __name__ == "__main__":
    unittest.main()
