"""Unit tests for the Mesh-Deck UI layer using Python standard library unittest."""

import unittest
from datetime import datetime, timedelta
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
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
    """Test Rich styling badge helper functions."""

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

    def test_format_time_ago(self):
        now = datetime.now()
        self.assertIn("s fa", format_time_ago(now - timedelta(seconds=20)))
        self.assertIn("m fa", format_time_ago(now - timedelta(minutes=15)))
        self.assertIn("h fa", format_time_ago(now - timedelta(hours=4)))
        self.assertIn("d fa", format_time_ago(now - timedelta(days=3)))
        self.assertIn("mai", format_time_ago(None))

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


class TestBanner(unittest.TestCase):
    """Test tactical status banner rendering."""

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
        import io
        from rich.console import Console
        panel = render_banner(None, port="/dev/ttyACM0")
        self.assertIsInstance(panel, Panel)
        buf = io.StringIO()
        c = Console(file=buf)
        c.print(panel)
        self.assertIn("IN CONNESSIONE", buf.getvalue())


class TestTablesAndViews(unittest.TestCase):
    """Test tables and analytical view rendering."""

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

    def test_render_node_detail(self):
        node = self.sample_nodes[1]
        panel = render_node_detail(node, distance_km=8.4)
        self.assertIsInstance(panel, Panel)
        self.assertIn("SCHEDA ANALITICA", str(panel.title))
        self.assertIn(node.short_name, str(panel.title))
        self.assertIn(node.id, str(panel.title))
        self.assertIsNotNone(node.osm_url)
        self.assertIn("openstreetmap.org", node.osm_url)

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
        import io
        from rich.console import Console
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
        c = Console(file=buf)
        c.print(rendered)
        self.assertIn("Secret ping message", buf.getvalue())


class TestCompleter(unittest.TestCase):
    """Test interactive prompt_toolkit autocompletion."""

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
                long_name="Bravo Node",
                short_name="BRAVO",
                role="ROUTER",
                snr=-2.0,
            ),
        ]
        self.ports = ["/dev/ttyACM0", "/dev/ttyACM1"]
        self.completer = MeshDeckCompleter(get_nodes=self.nodes, get_ports=self.ports)

    def test_slash_command_completion(self):
        doc = Document("/n")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("/nodes", texts)
        self.assertIn("/node", texts)
        self.assertNotIn("/dm", texts)

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

    def test_switch_port_completion(self):
        doc = Document("/switch /dev/ttyA")
        completions = list(self.completer.get_completions(doc, CompleteEvent()))
        texts = [c.text for c in completions]
        self.assertIn("/dev/ttyACM0", texts)
        self.assertIn("/dev/ttyACM1", texts)


if __name__ == "__main__":
    unittest.main()
