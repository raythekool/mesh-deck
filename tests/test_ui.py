"""Unit tests for the Mesh-Deck UI layer using Python standard library unittest.

Covers theme formatters, banner, tables, detail dossiers, messages, and completer edge cases.
"""

import io
import unittest
import unittest.mock
from datetime import datetime, timedelta, UTC

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Input, OptionList, Static

from mesh_deck.i18n import command_descriptions
from mesh_deck.models import DeviceConnectionInfo, MeshMessage, NodeData
from mesh_deck.ui.device_selector import DeviceSelectorScreen
from mesh_deck.core.settings import Settings
from mesh_deck.ui.repl import ConnectionScreen, MeshDeckApp, MeshDeckREPL, SettingsScreen
from mesh_deck.ui import (
    MeshDeckCompleter,
    THEME_COLORS,
    THEMES,
    css_variables,
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
    set_theme,
    theme_names,
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
        self.assertIn("#7c3aed", format_role("ROUTER"))

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
        utc_now = datetime.now(UTC)
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
            hw_model="HELTEC_V3",
            role="CLIENT",
            battery_level=90,
            voltage=4.12,
            channel_util=8.5,
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
            hw_model="HELTEC_VISION_MASTER_E290_V3",
            role="ROUTER",
            battery_level=18,
            voltage=3.45,
            region="US_915",
            modem_preset="SHORT_FAST",
            channel_util=82.4,
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
                hw_model="HELTEC_V3",
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
                hw_model="TLORA_V2",
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
                hw_model="RAK4631",
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
                hw_model="TBEAM_V1_2",
                role="ROUTER",
            ),
            NodeData(
                id="!22222222",
                long_name="TBeam Vaiano 🎯🇮🇹 [UPLINK] Station",
                short_name="VAI🎯",
                hw_model="TLORA_T3S3",
                role="CLIENT",
            ),
            NodeData(
                id="!33333333",
                long_name="Portofino 🏖️ 🚤 [SEASIDE_GATEWAY]",
                short_name="PORT",
                hw_model="HELTEC_V3",
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
            hw_model="UNSET",
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
            hw_model="HELTEC_VISION_MASTER_E290",
            role="ROUTER",
            snr=9.5,
            hops_away=0,
            battery_level=98,
            voltage=4.18,
            channel_util=12.5,
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
            receiver_id="!78b211a0",
            recipient_name="Remote LilyGo",
            is_dm=True,
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
            is_dm=True,
        )
        panel_markup = render_message(msg_markup)
        buf = io.StringIO()
        Console(file=buf).print(panel_markup)
        self.assertIn("[/closing_tag]", buf.getvalue())

        # 4. Unknown sender and recipient
        msg_unknown = MeshMessage(text="Ping", sender_id="", is_dm=True)
        panel_unknown = render_message(msg_unknown)
        buf_unk = io.StringIO()
        Console(file=buf_unk).print(panel_unknown)
        self.assertIn("Sconosciuto", buf_unk.getvalue())


class TestCompleter(unittest.TestCase):
    """Test Textual command-input completion data and edge cases."""

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
        texts = [c.value for c in self.completer.suggestions("/n")]
        self.assertIn("/nodes", texts)
        self.assertIn("/node", texts)
        self.assertNotIn("/dm", texts)

    def test_settings_and_restart_are_suggested(self):
        self.assertEqual([item.value for item in self.completer.suggestions("/set")], ["/settings"])
        self.assertEqual([item.value for item in self.completer.suggestions("/res")], ["/restart"])

    def test_localized_command_descriptions(self):
        self.assertIn("List", command_descriptions("en")["/nodes"])
        self.assertIn("Elenca", command_descriptions("it")["/nodes"])
        self.assertIn("/history", command_descriptions("en"))
        self.assertIn("/topology", command_descriptions("en"))
        self.assertIn("/logs", command_descriptions("en"))
        self.assertIn("/device-settings", command_descriptions("en"))

    def test_completer_empty_or_whitespace_input(self):
        # Empty text yields no completions
        completions_empty = self.completer.suggestions("")
        self.assertEqual(len(completions_empty), 0)

        # Whitespace-only yields no completions
        completions_spaces = self.completer.suggestions("    ")
        self.assertEqual(len(completions_spaces), 0)

    def test_completer_leading_spaces(self):
        # Command with leading whitespace should autocomplete correctly
        texts = [c.value for c in self.completer.suggestions("   /sw")]
        self.assertIn("/switch", texts)

    def test_node_target_completion(self):
        texts = [c.value for c in self.completer.suggestions("/node AL")]
        self.assertIn("ALPHA", texts)
        self.assertNotIn("BRAVO", texts)

    def test_dm_target_completion(self):
        texts = [c.value for c in self.completer.suggestions("/dm BR")]
        self.assertIn("BRAVO", texts)

        # After target is entered and space is typed, do not suggest nodes
        completions_msg = self.completer.suggestions("/dm BRAVO Ciao come stai")
        self.assertEqual(len(completions_msg), 0)

    def test_completer_names_with_spaces_and_emoji(self):
        # Autocompleting a short name with spaces should wrap in quotes
        texts = [c.value for c in self.completer.suggestions("/node Vai")]
        self.assertIn('"Vaiano 1"', texts)

        # Autocompleting with emoji
        texts_emoji = [c.value for c in self.completer.suggestions("/node 🎯")]
        self.assertIn("🎯IT", texts_emoji)

    def test_completer_with_open_quotes(self):
        # User starts typing with a quote: /node "Vai
        texts = [c.value for c in self.completer.suggestions('/node "Vai')]
        self.assertIn('"Vaiano 1"', texts)

    def test_switch_port_completion(self):
        texts = [c.value for c in self.completer.suggestions("/switch /dev/ttyA")]
        self.assertIn("/dev/ttyACM0", texts)
        self.assertIn("/dev/ttyACM1", texts)
        self.assertNotIn("/dev/ttyUSB0", texts)

        # Empty query after /switch
        completions_all = self.completer.suggestions("/switch ")
        self.assertEqual(len(completions_all), 3)


class TestMeshDeckREPLIntegration(unittest.TestCase):
    """Integration tests for MeshDeckREPL initialization, prompt and event wiring."""

    def setUp(self):
        from unittest.mock import MagicMock
        from mesh_deck.ui import MeshDeckREPL

        self.mock_client = MagicMock()
        self.mock_store = MagicMock()
        self.mock_client.store = self.mock_store
        self.mock_client.port = "/dev/ttyACM0"
        self.mock_client.is_connected = True

        self.local_node = NodeData(
            id="!45a466e4",
            num=1168402148,
            long_name="Morpheus Command Node",
            short_name="MRPH",
            hw_model="HELTEC_VISION_MASTER_E290",
            role="CLIENT",
            is_local=True,
        )
        self.mock_client.get_local_node.return_value = self.local_node
        self.mock_store.get_all_nodes.return_value = [self.local_node]

        self.console = Console(file=io.StringIO())
        self.repl = MeshDeckREPL(self.mock_client, console=self.console)

    def test_repl_initialization(self):
        """Verify REPL instantiates completer, dispatcher and message callbacks cleanly."""
        self.assertIsNotNone(self.repl.completer)
        self.assertIsNotNone(self.repl.dispatcher)
        self.mock_client.on_message_received.assert_called_once()

    def test_repl_dynamic_prompt(self):
        """Verify dynamic prompt generation with local node."""
        prompt = self.repl._get_prompt()
        self.assertIn("MRPH", str(prompt))

        # Test prompt without local node
        self.mock_client.get_local_node.return_value = None
        prompt_no_node = self.repl._get_prompt()
        self.assertIn("mesh-deck", str(prompt_no_node))

    def test_repl_incoming_message_handler(self):
        """Verify incoming message handler formats and prints without error."""
        msg = MeshMessage(
            sender_id="!62d927b8",
            sender_name="Trinity",
            receiver_id="^all",
            text="Testing REPL stream non-disruptive print",
            channel=0,
            snr=10.5,
            hops=0,
        )
        self.repl._handle_incoming_message(msg)
        output = self.console.file.getvalue()
        self.assertIn("Trinity", output)
        self.assertIn("Testing REPL stream", output)


class _IsolatedSettingsTestCase(unittest.IsolatedAsyncioTestCase):
    """Base test case that redirects Settings persistence to a throwaway temp directory.

    Prevents tests that call Settings.update()/.save() from reading or polluting
    the developer's real ~/.config/mesh-deck/settings.json.
    """

    def setUp(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        self._settings_tmp = TemporaryDirectory()
        config_dir = Path(self._settings_tmp.name) / "mesh-deck"
        self._settings_patchers = [
            unittest.mock.patch("mesh_deck.core.settings.CONFIG_DIR", config_dir),
            unittest.mock.patch("mesh_deck.core.settings.CONFIG_FILE", config_dir / "settings.json"),
        ]
        for patcher in self._settings_patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self._settings_patchers:
            patcher.stop()
        self._settings_tmp.cleanup()


class TestDeviceSelectorKeyboard(_IsolatedSettingsTestCase):
    """Test keyboard navigation through startup screens in the unified TUI."""

    async def test_arrows_select_device_with_saved_command_history(self):
        from unittest.mock import MagicMock
        from textual.widgets import OptionList

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.connect.return_value = False

        repl = MeshDeckREPL(client)
        repl.settings.command_history = ["/nodes", "/info"]
        app = MeshDeckApp(repl, devices=[
            DeviceConnectionInfo("/dev/ttyACM0", "Heltec", "Heltec"),
            DeviceConnectionInfo("/dev/ttyACM1", "LilyGo", "LilyGo"),
        ])

        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, DeviceSelectorScreen)
            devices = app.screen.query_one(OptionList)

            await pilot.press("down")
            self.assertEqual(devices.highlighted, 1)
            await pilot.press("up")
            self.assertEqual(devices.highlighted, 0)
            await pilot.press("down", "enter")
            await pilot.pause()

            client.connect.assert_called_once_with("/dev/ttyACM1", blocking=True)
            self.assertIsInstance(app.screen, ConnectionScreen)

    async def test_successful_connection_returns_to_command_input(self):
        from unittest.mock import MagicMock
        from textual.widgets import Input

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.connect.return_value = True

        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl, devices=[
            DeviceConnectionInfo("/dev/ttyACM0", "Heltec", "Heltec"),
        ])

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            self.assertNotIsInstance(app.screen, DeviceSelectorScreen)
            self.assertNotIsInstance(app.screen, ConnectionScreen)
            self.assertIsInstance(app.focused, Input)

    async def test_device_selector_footer_bindings_follow_language(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []

        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl, devices=[
            DeviceConnectionInfo("/dev/ttyACM0", "Heltec", "Heltec"),
        ])

        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            self.assertIsInstance(screen, DeviceSelectorScreen)
            self.assertEqual(screen._bindings.key_to_bindings["r"][0].description, "Refresh")
            self.assertEqual(screen._bindings.key_to_bindings["q"][0].description, "Cancel")

    async def test_selector_shows_preferred_active_and_retry_context(self):
        from mesh_deck.ui.device_selector import DeviceSelectorApp

        app = DeviceSelectorApp(
            [
                DeviceConnectionInfo("COM6", "T-Beam", "T-Beam"),
                DeviceConnectionInfo("COM7", "Heltec", "Heltec"),
            ],
            preferred_port="COM6",
            active_port="COM6",
            failed_port="COM7",
            failure_reason="Access denied",
            lang="en",
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            options = screen.query_one("#devices", OptionList)
            first = str(options.get_option_at_index(0).prompt)
            second = str(options.get_option_at_index(1).prompt)
            self.assertIn("PREFERRED", first)
            self.assertIn("ACTIVE", first)
            self.assertIn("RETRY", second)
            self.assertEqual(options.highlighted, 0)
            self.assertTrue(screen.query_one("#device-error", Static).display)
            self.assertIn("Access denied", str(screen.query_one("#device-error", Static).content))
            self.assertEqual(screen._bindings.key_to_bindings["t"][0].description, "Retry")

    async def test_selector_retry_action_returns_failed_port(self):
        from mesh_deck.ui.device_selector import DeviceSelectorApp

        app = DeviceSelectorApp(
            [DeviceConnectionInfo("COM7", "Heltec", "Heltec")],
            failed_port="COM7",
            lang="en",
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            with unittest.mock.patch.object(screen, "dismiss") as dismiss:
                screen.action_retry_failed_device()
                dismiss.assert_called_once_with("COM7")

    async def test_selector_empty_state_explains_recovery(self):
        from mesh_deck.ui.device_selector import DeviceSelectorApp

        app = DeviceSelectorApp([], lang="en")
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            empty = screen.query_one("#device-empty", Static)
            self.assertTrue(empty.display)
            self.assertIn("No Meshtastic radio was detected", str(empty.content))

    async def test_failed_handshake_is_presented_on_return_to_selector(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.last_connection_error = "Access denied"
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(
            repl,
            devices=[DeviceConnectionInfo("COM6", "T-Beam", "T-Beam")],
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ConnectionScreen("COM6", lang="en"))
            await pilot.pause()
            self.assertIsInstance(app.screen, ConnectionScreen)
            app.connection_complete(False)
            app.return_to_device_selector()
            await pilot.pause()
            self.assertIsInstance(app.screen, DeviceSelectorScreen)
            error = app.screen.query_one("#device-error", Static)
            self.assertTrue(error.display)
            self.assertIn("Access denied", str(error.content))

    async def test_activate_console_opens_explorer_with_saved_mode_and_history(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.history = object()
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        repl.settings.explorer_view_mode = "compact"
        app = MeshDeckApp(repl)
        app.open_explorer_on_connect = True

        async with app.run_test() as pilot:
            await pilot.pause()
            with unittest.mock.patch.object(app, "open_node_explorer") as open_node_explorer:
                app.activate_console()
                open_node_explorer.assert_called_once_with(
                    client.store,
                    None,
                    "en",
                    "compact",
                    client.history,
                )


class TestNodeSidebar(_IsolatedSettingsTestCase):
    """Test the mouse-clickable node sidebar in the main console."""

    async def test_sidebar_lists_nodes_and_enter_opens_node_detail(self):
        from unittest.mock import MagicMock

        node = NodeData(id="!45a466e4", short_name="ALPHA", long_name="Alpha Node")
        client = MagicMock()
        client.store.get_all_nodes.return_value = [node]
        client.store.get_node.return_value = node
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)
        show_detail = app.show_node_detail
        app.show_node_detail = MagicMock(wraps=show_detail)

        async with app.run_test() as pilot:
            await pilot.pause()
            sidebar = app.query_one("#sidebar-nodes", OptionList)
            self.assertEqual(sidebar.option_count, 1)
            sidebar.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            app.show_node_detail.assert_called_once_with("!45a466e4")
            self.assertTrue(app.query_one("#node-detail").display)

    async def test_node_detail_can_be_collapsed_from_its_control(self):
        from unittest.mock import MagicMock

        node = NodeData(id="!45a466e4", short_name="ALPHA", long_name="Alpha Node")
        client = MagicMock()
        client.store.get_all_nodes.return_value = [node]
        client.store.get_node.return_value = node
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        app = MeshDeckApp(MeshDeckREPL(client))

        async with app.run_test() as pilot:
            await pilot.pause()
            app.show_node_detail(node.id)
            await pilot.pause()
            self.assertTrue(app.query_one("#node-detail").display)
            self.assertTrue(app.query_one("#node-detail-collapse").display)

            await pilot.click("#node-detail-collapse")
            await pilot.pause()
            self.assertFalse(app.query_one("#node-detail").display)
            self.assertFalse(app.query_one("#node-detail-collapse").display)

    async def test_workflow_screen_replaces_the_previous_one(self):
        from unittest.mock import MagicMock

        from mesh_deck.core.node_store import NodeStore
        from mesh_deck.ui.channel_chat import ChannelChatScreen
        from mesh_deck.ui.interactive_table import InteractiveNodesScreen

        client = MagicMock()
        client.store = NodeStore()
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        app = MeshDeckApp(MeshDeckREPL(client))

        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_node_explorer(client.store, None, "en", "full")
            await pilot.pause()
            self.assertIsInstance(app.screen, InteractiveNodesScreen)
            self.assertEqual(len(app.screen_stack), 2)

            app.open_channel_chat(client, "en")
            await pilot.pause()
            self.assertIsInstance(app.screen, ChannelChatScreen)
            self.assertEqual(len(app.screen_stack), 2)

            app.pop_screen()
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)

    async def test_quit_button_uses_quit_command(self):
        from unittest.mock import MagicMock, patch

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        app = MeshDeckApp(MeshDeckREPL(client))

        async with app.run_test() as pilot:
            await pilot.pause()
            with patch.object(app, "_submit_command") as submit_command:
                await pilot.click("#quit-button")
                submit_command.assert_called_once_with("/quit")

    async def test_display_command_replaces_console_output(self):
        from unittest.mock import MagicMock, patch

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        app = MeshDeckApp(MeshDeckREPL(client))

        async with app.run_test() as pilot:
            await pilot.pause()
            with patch.object(app, "clear_output") as clear_output:
                app._submit_command("/nodes")
                clear_output.assert_called_once()

    async def test_node_explorer_preserves_filter_when_layout_rebuilds(self):
        from mesh_deck.core.node_store import NodeStore
        from mesh_deck.ui.interactive_table import InteractiveNodesScreen
        from textual.widgets import DataTable

        store = NodeStore()
        store.update_node(NodeData(id="!aaa", short_name="ALPHA", long_name="Alpha Node"))
        store.update_node(NodeData(id="!bbb", short_name="BRAVO", long_name="Bravo Node"))

        client = unittest.mock.MagicMock()
        client.store = store
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_node_explorer(store, None, "en", "full")
            await pilot.pause()
            screen = app.screen
            self.assertIsInstance(screen, InteractiveNodesScreen)
            filter_input = screen.query_one("#filter-input", Input)
            filter_input.value = "bravo"
            await pilot.pause()
            table = screen.query_one(DataTable)
            self.assertEqual(table.row_count, 1)

            screen.view_mode = "compact"
            screen._configure_layout(force=True)
            await pilot.pause()

            self.assertEqual(table.row_count, 1)
            self.assertIsNone(screen._selected_node_id)

    async def test_radio_status_escapes_remote_markup_in_local_name(self):
        client = unittest.mock.MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_channels.return_value = []
        client.port = "COM6"
        client.get_local_node.return_value = NodeData(
            id="!aaa",
            short_name="[bold]ALPHA[/]",
            long_name="Alpha",
        )
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)
        repl.connection_state = "connected"

        async with app.run_test() as pilot:
            await pilot.pause()
            app.refresh_radio_status()
            status = str(app.query_one("#radio-status", Static).content)
            self.assertIn("[bold]ALPHA[/]", status)

    async def test_ctrl_b_toggles_sidebar_visibility(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            sidebar = app.query_one("#sidebar")
            initial = sidebar.display
            await pilot.press("ctrl+b")
            await pilot.pause()
            self.assertEqual(sidebar.display, not initial)
            await pilot.press("ctrl+b")
            await pilot.pause()
            self.assertEqual(sidebar.display, initial)

    async def test_selecting_another_node_replaces_the_single_detail_card(self):
        from unittest.mock import MagicMock
        from textual.widgets import Static

        node_a = NodeData(id="!45a466e4", short_name="ALPHA", long_name="Alpha Node")
        node_b = NodeData(id="!78b211a0", short_name="BRAVO", long_name="Bravo Node")
        client = MagicMock()
        client.store.get_all_nodes.return_value = [node_a, node_b]
        client.store.get_node.side_effect = lambda node_id: {node_a.id: node_a, node_b.id: node_b}.get(node_id)
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            sidebar = app.query_one("#sidebar-nodes", OptionList)
            detail = app.query_one("#node-detail", Static)

            sidebar.highlighted = 0
            sidebar.focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(detail.display)

            sidebar.highlighted = 1
            await pilot.press("enter")
            await pilot.pause()

            # A single card stays mounted and is replaced in place, never duplicated.
            self.assertEqual(len(app.query("#node-detail")), 1)
            self.assertTrue(detail.display)

    async def test_sidebar_row_shows_long_name_instead_of_node_id(self):
        from unittest.mock import MagicMock

        node = NodeData(id="!45a466e4", short_name="ALPHA", long_name="Alpha Relay Station")
        client = MagicMock()
        client.store.get_all_nodes.return_value = [node]
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            sidebar = app.query_one("#sidebar-nodes", OptionList)
            option_text = str(sidebar.get_option_at_index(0).prompt)
            self.assertIn("Alpha Relay Station", option_text)
            self.assertNotIn(node.id, option_text)

    async def test_dragging_the_resize_handle_changes_sidebar_width(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            sidebar = app.query_one("#sidebar")
            initial_width = sidebar.size.width

            await pilot.mouse_down("#sidebar-resizer")
            await pilot.hover("#body", offset=(50, 5))
            await pilot.mouse_up("#body", offset=(50, 5))
            await pilot.pause()

            self.assertNotEqual(sidebar.size.width, initial_width)
            self.assertEqual(repl.settings.sidebar_width, sidebar.size.width)

    async def test_sort_button_cycles_through_criteria_and_persists(self):
        from unittest.mock import MagicMock
        from textual.widgets import Static

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            sort_button = app.query_one("#sidebar-sort", Static)
            self.assertEqual(repl.settings.default_sort, "last_heard")

            await pilot.click("#sidebar-sort")
            await pilot.pause()
            self.assertEqual(repl.settings.default_sort, "snr")
            self.assertIn("Segnale", str(sort_button.content))

            await pilot.click("#sidebar-sort")
            await pilot.pause()
            self.assertEqual(repl.settings.default_sort, "hops")

            await pilot.click("#sidebar-sort")
            await pilot.pause()
            self.assertEqual(repl.settings.default_sort, "name")

            await pilot.click("#sidebar-sort")
            await pilot.pause()
            self.assertEqual(repl.settings.default_sort, "last_heard")

    async def test_filter_button_cycles_and_filters_favorites(self):
        from unittest.mock import MagicMock
        from textual.widgets import Static

        node_fav = NodeData(id="!11111111", short_name="FAV1", long_name="Favorite Node", is_favorite=True)
        node_plain = NodeData(id="!22222222", short_name="PLA1", long_name="Plain Node", is_favorite=False)
        all_nodes = [node_fav, node_plain]

        def fake_get_all_nodes(sort_by="last_heard", active_only=False, active_threshold_seconds=7200, favorites_only=False):
            if favorites_only:
                return [n for n in all_nodes if n.is_favorite]
            return list(all_nodes)

        client = MagicMock()
        client.store.get_all_nodes.side_effect = fake_get_all_nodes
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            filter_button = app.query_one("#sidebar-filter", Static)
            sidebar = app.query_one("#sidebar-nodes", OptionList)
            self.assertEqual(repl.settings.sidebar_filter, "all")
            self.assertEqual(sidebar.option_count, 2)

            await pilot.click("#sidebar-filter")
            await pilot.pause()
            self.assertEqual(repl.settings.sidebar_filter, "active")

            await pilot.click("#sidebar-filter")
            await pilot.pause()
            self.assertEqual(repl.settings.sidebar_filter, "favorites")
            self.assertIn("Preferiti", str(filter_button.content))
            self.assertEqual(sidebar.option_count, 1)

            await pilot.click("#sidebar-filter")
            await pilot.pause()
            self.assertEqual(repl.settings.sidebar_filter, "all")
            self.assertEqual(sidebar.option_count, 2)


class TestLanguageConsistency(_IsolatedSettingsTestCase):
    """Ensure UI-facing strings consistently follow the active language setting."""

    async def test_radio_status_strip_tracks_connection_and_reconnect_states(self):
        from unittest.mock import MagicMock
        from textual.widgets import Static

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#radio-status", Static)
            self.assertIn("Radio disconnected", str(status.content))

            client.port = "COM6"
            client.get_local_node.return_value = NodeData(
                id="!00000001", short_name="BASE", long_name="Base"
            )
            repl._handle_connection_change(True, "COM6")
            await pilot.pause()
            self.assertIn("Connected", str(status.content))
            self.assertIn("BASE", str(status.content))
            self.assertIn("COM6", str(status.content))

            repl._handle_reconnect_attempt("COM6", 2)
            await pilot.pause()
            self.assertIn("Reconnecting", str(status.content))
            self.assertIn("attempt 2", str(status.content))

    async def test_sidebar_toggle_footer_binding_follows_language(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app._bindings.key_to_bindings["ctrl+b"][0].description, "Toggle sidebar")

            app.update_language("it")
            await pilot.pause()
            self.assertEqual(
                app._bindings.key_to_bindings["ctrl+b"][0].description,
                "Mostra/nascondi barra laterale",
            )

    async def test_mounted_sidebar_title_and_controls_follow_language(self):
        from unittest.mock import MagicMock

        node = NodeData(id="!11111111", short_name="ALFA", long_name="Alpha")
        client = MagicMock()
        client.store.get_all_nodes.return_value = [node]
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.update_language("it")
            await pilot.pause()
            self.assertIn("NODI", str(app.query_one("#sidebar-title").content))
            self.assertIn("Recenti", str(app.query_one("#sidebar-sort").content))
            self.assertIn("Tutti", str(app.query_one("#sidebar-filter").content))

    async def test_incoming_message_toast_titles_follow_language(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            msg = MeshMessage(text="hi", sender_name="Alpha", is_dm=True)
            app.notify_message(msg)
            await pilot.pause()
            self.assertTrue(any("DM from Alpha" in n.title for n in app._notifications))


class TestCommandProgress(unittest.IsolatedAsyncioTestCase):
    """Long command feedback must be visible and traceroute cancellation must be explicit."""

    def _app(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        return MeshDeckApp(repl)

    async def test_trace_progress_is_cancellable_and_clears(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._start_command_progress("/trace TRIN")
            progress = app.query_one("#command-progress", Static)
            self.assertTrue(progress.display)
            self.assertIn("Esc to cancel", str(progress.content))
            cancel_event = app._active_cancel_event
            self.assertIsNotNone(cancel_event)

            app.action_clear_suggestions()
            self.assertTrue(cancel_event.is_set())
            self.assertIn("Cancellation requested", str(progress.content))

            app._finish_command_progress()
            self.assertFalse(progress.display)
            self.assertIsNone(app._active_command)

    async def test_non_cancellable_progress_does_not_capture_escape(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._start_command_progress("/switch COM7")
            self.assertIsNone(app._active_cancel_event)
            progress = app.query_one("#command-progress", Static)
            self.assertIn("Running: /switch COM7", str(progress.content))
            app.action_clear_suggestions()
            self.assertEqual(app.completions, [])
            app._finish_command_progress()

    async def test_second_command_is_rejected_while_worker_is_active(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._start_command_progress("/trace TRIN")
            with unittest.mock.patch.object(app, "notify") as notify:
                app._submit_command("/nodes")
                notify.assert_called_once()
            app._finish_command_progress()


class TestCommandAutocomplete(unittest.IsolatedAsyncioTestCase):
    """Test Enter behavior for command suggestions in the Textual input."""

    async def test_enter_executes_unique_incomplete_command(self):
        from unittest.mock import MagicMock
        from textual.widgets import Input

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        dispatch = repl.dispatcher.dispatch
        repl.dispatcher.dispatch = MagicMock(wraps=dispatch)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.press("/", "s", "e", "t", "enter")
            await pilot.pause()
            self.assertEqual(app.query_one(Input).value, "")
            repl.dispatcher.dispatch.assert_called_once_with("/settings")

    async def test_enter_executes_highlighted_command_when_multiple_match(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        dispatch = repl.dispatcher.dispatch
        repl.dispatcher.dispatch = MagicMock(wraps=dispatch)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.press("/", "n", "down", "down", "enter")
            await pilot.pause()
            repl.dispatcher.dispatch.assert_called_once_with("/node")

    async def test_enter_executes_complete_settings_command(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.press("/", "s", "e", "t", "t", "i", "n", "g", "s", "enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, SettingsScreen)


class TestChannelChatScreen(unittest.IsolatedAsyncioTestCase):
    """Test the mouse-usable channel chat screen: history preload, live updates, sending."""

    def _make_client(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_channels.return_value = [
            {"index": 0, "name": "Primary", "role": "PRIMARY"},
        ]
        client.history = None
        # Simulate on_message_received/off_message_received as plain callback registries.
        client._callbacks = []
        client.on_message_received.side_effect = lambda cb: client._callbacks.append(cb)
        client.off_message_received.side_effect = lambda cb: client._callbacks.remove(cb)
        return client

    async def test_preloads_history_and_lists_channels_without_empty_dm_entry(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp

        client = self._make_client()
        client.history = unittest.mock.MagicMock()
        client.history.iter_messages.return_value = [
            {
                "sender_id": "!aaa",
                "sender_name": "Neo",
                "receiver_id": "^all",
                "text": "Historical hello",
                "channel": 0,
                "is_dm": False,
                "timestamp": "2024-01-01T10:00:00",
                "direction": "in",
                "recorded_at": "2024-01-01T10:00:01",
            }
        ]
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            option_list = app.screen.query_one("#channel-list", OptionList)
            # Direct-message conversations are listed only when a peer exists.
            self.assertEqual(option_list.option_count, 1)

            # History preloaded into the in-memory per-channel buffer used to render the log.
            buffered = app.screen._buffers.get(0, [])
            self.assertTrue(any(m.text == "Historical hello" for m in buffered))

    async def test_incoming_dm_creates_a_peer_conversation_with_unread_badge(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp, DM_KEY

        client = self._make_client()
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            dm_msg = MeshMessage(sender_id="!bbb", sender_name="Trinity", text="psst", is_dm=True)
            screen._handle_message(dm_msg)
            await pilot.pause()

            dm_key = f"{DM_KEY}!bbb"
            self.assertEqual(screen._unread.get(dm_key), 1)

            option_list = screen.query_one("#channel-list", OptionList)
            dm_index = next(i for i, (key, _n) in enumerate(screen._entries) if key == dm_key)
            option_list.highlighted = dm_index
            await pilot.press("enter")
            await pilot.pause()

            self.assertEqual(screen._unread.get(dm_key), 0)
            self.assertEqual(screen._selected_key, dm_key)
            self.assertIn("Trinity", str(screen.query_one("#chat-hint", Static).content))
            self.assertFalse(screen.query_one("#chat-input", Input).disabled)

    async def test_submitting_input_sends_broadcast_on_selected_channel(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp

        client = self._make_client()
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            chat_input = app.screen.query_one("#chat-input", Input)
            chat_input.focus()
            await pilot.pause()
            await pilot.press(*"hello mesh")
            await pilot.press("enter")
            await pilot.pause()

            client.send_broadcast.assert_called_once_with("hello mesh", channel_index=0)

    async def test_submitting_reply_sends_dm_to_selected_peer_and_updates_buffer(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp, DM_KEY

        client = self._make_client()
        client.get_local_node.return_value = NodeData(
            id="!local", short_name="BASE", long_name="Base"
        )
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen._handle_message(
                MeshMessage(sender_id="!bbb", sender_name="Trinity", text="ping", is_dm=True)
            )
            dm_key = f"{DM_KEY}!bbb"
            screen._selected_key = dm_key
            screen._unread[dm_key] = 0
            screen._render_selected()
            chat_input = screen.query_one("#chat-input", Input)
            chat_input.focus()
            await pilot.press(*"pong")
            await pilot.press("enter")
            await pilot.pause()

            client.send_dm.assert_called_once_with("!bbb", "pong")
            self.assertEqual([msg.text for msg in screen._buffers[dm_key]], ["ping", "pong"])
            self.assertEqual(screen._buffers[dm_key][-1].sender_id, "!local")

    async def test_history_splits_direct_messages_by_peer(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp, DM_KEY

        client = self._make_client()
        client.history = unittest.mock.MagicMock()
        client.history.iter_messages.return_value = [
            {
                "sender_id": "!bbb",
                "sender_name": "Trinity",
                "receiver_id": "^local",
                "text": "one",
                "channel": 0,
                "is_dm": True,
                "timestamp": "2024-01-01T10:00:00",
            },
            {
                "sender_id": "!ccc",
                "sender_name": "Zion",
                "receiver_id": "^local",
                "text": "two",
                "channel": 0,
                "is_dm": True,
                "timestamp": "2024-01-01T10:01:00",
            },
        ]
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            self.assertIn(f"{DM_KEY}!bbb", screen._buffers)
            self.assertIn(f"{DM_KEY}!ccc", screen._buffers)
            self.assertEqual(screen.query_one("#channel-list", OptionList).option_count, 4)

    async def test_history_uses_recorded_outbound_direction_for_dm_threads(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp, DM_KEY

        client = self._make_client()
        client.history = unittest.mock.MagicMock()
        client.history.iter_messages.return_value = [
            {
                "sender_id": "^local",
                "sender_name": "Local",
                "receiver_id": "!bbb",
                "recipient_name": "Trinity",
                "text": "reply",
                "channel": 0,
                "is_dm": True,
                "direction": "out",
                "timestamp": "2024-01-01T10:00:00",
            }
        ]
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn(f"{DM_KEY}!bbb", app.screen._buffers)
            self.assertNotIn(f"{DM_KEY}^local", app.screen._buffers)

    async def test_local_dm_echo_stays_in_selected_peer_when_local_identity_is_missing(self):
        from mesh_deck.ui.channel_chat import ChannelChatApp, DM_KEY

        client = self._make_client()
        client.get_local_node.return_value = None
        app = ChannelChatApp(client)

        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            dm_key = f"{DM_KEY}!bbb"
            screen._buffers[dm_key] = []
            screen._dm_names[dm_key] = "Trinity"
            screen._selected_key = dm_key
            screen._render_selected()
            chat_input = screen.query_one("#chat-input", Input)
            chat_input.focus()
            await pilot.press(*"pong")
            await pilot.press("enter")
            await pilot.pause()

            self.assertIn(dm_key, screen._buffers)
            self.assertNotIn(f"{DM_KEY}^local", screen._buffers)
            self.assertEqual([msg.text for msg in screen._buffers[dm_key]], ["pong"])


class TestLogViewerScreen(unittest.IsolatedAsyncioTestCase):
    """The bounded diagnostic viewer filters, pauses, copies, and exports without stdout."""

    def _app(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        return MeshDeckApp(repl)

    async def test_viewer_filters_device_entries_and_pauses_live_refresh(self):
        from mesh_deck.ui.log_viewer import LogViewerScreen
        from textual.widgets import DataTable, Select

        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.repl.log_buffer.record_device("radio ready", "COM6")
            app.open_logs()
            await pilot.pause()
            self.assertIsInstance(app.screen, LogViewerScreen)
            screen = app.screen
            screen.query_one("#log-level", Select).value = "info"
            screen.query_one("#log-query", Input).value = "radio ready"
            screen.refresh_entries()
            table = screen.query_one("#log-table", DataTable)
            self.assertEqual(table.row_count, 1)

            screen.action_toggle_pause()
            app.repl.log_buffer.record_device("second line", "COM6")
            screen.request_refresh()
            await pilot.pause()
            self.assertEqual(table.row_count, 1)
            self.assertIn("paused", str(screen.query_one("#log-status", Static).content))
            self.assertIn("new", str(screen.query_one("#log-status", Static).content))

            screen.action_toggle_pause()
            screen.query_one("#log-query", Input).value = ""
            screen.refresh_entries()
            await pilot.pause()
            self.assertIn("second line", [entry.message for entry in screen._visible_entries.values()])

    async def test_copy_and_export_use_the_filtered_log_view(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from mesh_deck.ui import log_viewer
        from textual.widgets import DataTable, Select

        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.repl.log_buffer.record_device("copy this", "COM6")
            app.open_logs()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#log-level", Select).value = "info"
            screen.query_one("#log-query", Input).value = "copy this"
            screen.refresh_entries()
            table = screen.query_one("#log-table", DataTable)
            table.move_cursor(row=0, column=0)
            screen.action_copy_selected()
            self.assertIn("copy this", app.clipboard)

            with TemporaryDirectory() as temp_dir, patch.object(log_viewer, "LOG_EXPORT_DIR", Path(temp_dir)):
                screen.action_export_entries()
                exports = list(Path(temp_dir).glob("*.log"))
                self.assertEqual(len(exports), 1)
                self.assertIn("copy this", exports[0].read_text(encoding="utf-8"))


class TestTopologyScreen(unittest.IsolatedAsyncioTestCase):
    """Topology remains useful as a filtered edge list before a graph is justified."""

    def _app(self, reports):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.store.get_all_nodes.return_value = []
        nodes = {
            "!aaa": NodeData(id="!aaa", long_name="Alpha"),
            "!bbb": NodeData(id="!bbb", long_name="Bravo"),
            "!ccc": NodeData(id="!ccc", long_name="Charlie"),
        }
        client.store.get_node.side_effect = nodes.get
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.get_neighbor_reports.return_value = reports
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        return MeshDeckApp(repl), client

    async def test_empty_topology_explains_missing_neighborinfo(self):
        from mesh_deck.ui.topology import TopologyScreen
        from textual.widgets import DataTable

        app, client = self._app([])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_topology(client, "en")
            await pilot.pause()
            self.assertIsInstance(app.screen, TopologyScreen)
            self.assertEqual(app.screen.query_one("#topology-table", DataTable).row_count, 0)
            quality = str(app.screen.query_one("#topology-quality-content", Static).content)
            self.assertIn("No node has broadcast NeighborInfo yet", quality)

    async def test_topology_lists_and_filters_neighbor_edges(self):
        from mesh_deck.core.events import NeighborLink, NeighborReport
        from mesh_deck.ui.topology import TopologyScreen
        from textual.widgets import DataTable

        reports = [
            NeighborReport(
                node_id="!aaa",
                neighbors=[
                    NeighborLink(node_id="!bbb", snr=5.5),
                    NeighborLink(node_id="!ccc", snr=-2.0),
                ],
            )
        ]
        app, client = self._app(reports)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_topology(client, "en")
            await pilot.pause()
            screen = app.screen
            self.assertIsInstance(screen, TopologyScreen)
            table = screen.query_one("#topology-table", DataTable)
            self.assertEqual(table.row_count, 2)
            screen.query_one("#topology-filter-input", Input).value = "bravo"
            await pilot.pause()
            self.assertEqual(table.row_count, 1)
            self.assertIn("1 NeighborInfo reports received", str(screen.query_one("#topology-quality-content", Static).content))


class TestNodeHistoryScreen(unittest.IsolatedAsyncioTestCase):
    """JSONL node history renders only on demand and stays useful without all metrics."""

    def _history(self):
        from tempfile import TemporaryDirectory

        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        from mesh_deck.core.history import HistoryStore

        return HistoryStore(temp.name)

    async def test_history_screen_renders_snapshot_metrics(self):
        from unittest.mock import MagicMock

        from mesh_deck.ui.node_history import NodeHistoryScreen

        history = self._history()
        node = NodeData(id="!aaa", long_name="Alpha", battery_level=80, snr=2.0)
        history.record_node(node)
        node.battery_level = 75
        node.snr = 4.0
        node.temperature = 21.5
        node.channel_util = 12.0
        history.record_node(node)

        client = MagicMock()
        client.is_connected = False
        client.port = None
        client.history = history
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        app = MeshDeckApp(repl)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_node_history(node)
            await pilot.pause()
            self.assertIsInstance(app.screen, NodeHistoryScreen)
            self.assertIn("2 snapshots", str(app.screen.query_one("#history-summary", Static).content))
            self.assertIn("75.0%", str(app.screen.query_one("#history-battery-value", Static).content))
            self.assertIn("4.0 dB", str(app.screen.query_one("#history-snr-value", Static).content))
            self.assertIn("21.5 °C", str(app.screen.query_one("#history-temperature-value", Static).content))

    async def test_history_screen_explains_absent_snapshots(self):
        from mesh_deck.ui.node_history import NodeHistoryScreen

        history = self._history()
        node = NodeData(id="!bbb", long_name="Bravo")
        app = NodeHistoryScreen(node, history, lang="en")
        from mesh_deck.ui.theme import ThemedApp
        from textual.app import App

        class HistoryApp(ThemedApp, App):
            def on_mount(self):
                self.push_screen(app, callback=lambda _: self.exit())

        host = HistoryApp()
        async with host.run_test() as pilot:
            await pilot.pause()
            self.assertIn("No local snapshots", str(host.screen.query_one("#history-summary", Static).content))

    def test_history_range_filter_accepts_timezone_aware_snapshots(self):
        from mesh_deck.ui.node_history import NodeHistoryScreen

        history = self._history()
        node = NodeData(id="!aaa", long_name="Alpha")
        history._append(
            history.nodes_file,
            {
                "id": "!aaa",
                "observed_at": datetime.now(UTC).isoformat(),
                "battery_level": 80,
            },
        )

        screen = NodeHistoryScreen(node, history, lang="en")
        self.assertEqual(len(screen._entries("24h")), 1)


class TestDeviceSettingsScreen(unittest.IsolatedAsyncioTestCase):
    """Connected-device identity settings are draft-first and confirmation-gated."""

    def _app(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.is_connected = True
        client.port = "COM6"
        client.get_device_identity.return_value = {
            "id": "!local",
            "long_name": "Old Name",
            "short_name": "OLD",
            "role": "CLIENT",
            "hardware": "TBEAM",
        }
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = NodeData(
            id="!local", long_name="Old Name", short_name="OLD"
        )
        client.get_channels.return_value = []
        repl = MeshDeckREPL(client)
        repl.settings.language = "en"
        return MeshDeckApp(repl), client

    async def test_draft_shows_diff_and_validation_before_confirm(self):
        from mesh_deck.ui.device_settings import DeviceSettingsScreen

        app, _client = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_device_settings()
            await pilot.pause()
            self.assertIsInstance(app.screen, DeviceSettingsScreen)
            screen = app.screen
            long_name = screen.query_one("#device-settings-long-name", Input)
            short_name = screen.query_one("#device-settings-short-name", Input)
            long_name.value = "New Name"
            short_name.value = "NEW"
            await pilot.pause()
            diff = str(screen.query_one("#device-settings-diff", Static).content)
            self.assertIn("Old Name", diff)
            self.assertIn("New Name", diff)

            short_name.value = "TOO-LONG"
            await pilot.pause()
            self.assertIn("at most 4 characters", str(screen.query_one("#device-settings-diff", Static).content))

    async def test_confirmed_draft_applies_then_refreshes_snapshot(self):
        app, client = self._app()
        client.update_device_identity.return_value = {
            "id": "!local",
            "long_name": "New Name",
            "short_name": "NEW",
            "role": "CLIENT",
            "hardware": "TBEAM",
        }
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_device_settings()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#device-settings-long-name", Input).value = "New Name"
            screen.query_one("#device-settings-short-name", Input).value = "NEW"
            screen._on_identity_confirmed(True)
            await pilot.pause()
            await pilot.pause()
            client.update_device_identity.assert_called_once_with(long_name="New Name", short_name="NEW")
            self.assertIn("Identity sent", str(screen.query_one("#device-settings-status", Static).content))


class TestNotifyMessageWiring(unittest.IsolatedAsyncioTestCase):
    """Test that MeshDeckApp.notify_message builds the expected toast for DMs/broadcasts."""

    def _make_app(self):
        from unittest.mock import MagicMock
        from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client.connect.return_value = True

        repl = MeshDeckREPL(client)
        return MeshDeckApp(repl, devices=[])

    async def test_dm_notification_uses_warning_severity(self):
        app = self._make_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            with unittest.mock.patch.object(app, "notify") as mock_notify:
                msg = MeshMessage(sender_id="!bbb", sender_name="Trinity", text="psst", is_dm=True)
                app.notify_message(msg)
                mock_notify.assert_called_once()
                _, kwargs = mock_notify.call_args
                self.assertEqual(kwargs["severity"], "warning")
                self.assertIn("Trinity", kwargs["title"])

    async def test_broadcast_notification_uses_information_severity(self):
        app = self._make_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            with unittest.mock.patch.object(app, "notify") as mock_notify:
                msg = MeshMessage(sender_id="!aaa", sender_name="Neo", text="hi all", channel=0, is_dm=False)
                app.notify_message(msg)
                mock_notify.assert_called_once()
                _, kwargs = mock_notify.call_args
                self.assertEqual(kwargs["severity"], "information")


class TestConnectionScreen(unittest.IsolatedAsyncioTestCase):
    """The NodeDB loader reports real counts while remaining indeterminate."""

    async def test_node_db_sync_progress_updates_connection_status(self):
        from unittest.mock import MagicMock

        from mesh_deck.core.events import NodeDbSyncProgress

        client = MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        app = MeshDeckApp(MeshDeckREPL(client))
        async with app.run_test() as pilot:
            app.push_screen(ConnectionScreen("COM6", lang="en"))
            await pilot.pause()
            screen = app.screen
            self.assertIsInstance(screen, ConnectionScreen)

            screen.show_sync_progress(NodeDbSyncProgress(stage="syncing", node_count=12))
            await pilot.pause()
            status = screen.query_one("#connection-status", Static)
            loader = screen.query_one("#connection-loader", Static)
            self.assertIn("12 nodes received", str(status.content))
            self.assertIn("━", str(loader.content))


class TestThemeEngine(unittest.TestCase):
    """Test that themes are complete, switchable, and actually drive the renderers."""

    def setUp(self):
        self.addCleanup(set_theme, "cyberpunk")

    def test_all_themes_expose_the_same_keys(self):
        key_sets = [set(palette) for palette in THEMES.values()]
        self.assertTrue(all(keys == key_sets[0] for keys in key_sets))
        self.assertGreaterEqual(len(THEMES), 3)
        for palette in THEMES.values():
            for value in palette.values():
                self.assertRegex(value, r"^#[0-9a-f]{6}$")

    def test_theme_names_lists_default_first(self):
        self.assertEqual(theme_names()[0], "cyberpunk")
        self.assertEqual(sorted(theme_names()), sorted(THEMES))

    def test_set_theme_mutates_shared_palette_in_place(self):
        palette = THEME_COLORS
        set_theme("nord")
        self.assertIs(palette, THEME_COLORS)
        self.assertEqual(THEME_COLORS["primary"], THEMES["nord"]["primary"])

    def test_set_theme_falls_back_to_default_for_unknown_names(self):
        self.assertEqual(set_theme("matrix"), "cyberpunk")
        self.assertEqual(set_theme(None), "cyberpunk")
        self.assertEqual(THEME_COLORS, THEMES["cyberpunk"])

    def test_formatters_follow_the_active_theme(self):
        set_theme("ember")
        self.assertIn(THEMES["ember"]["secondary"], format_snr(9.0))
        self.assertIn(THEMES["ember"]["alert"], format_battery(12, None))
        self.assertIn(THEMES["ember"]["purple"], format_role("ROUTER"))
        self.assertNotIn(THEMES["cyberpunk"]["secondary"], format_snr(9.0))

    def test_css_variables_are_namespaced_and_dash_separated(self):
        set_theme("midnight")
        variables = css_variables()
        self.assertEqual(variables["mesh-primary"], THEMES["midnight"]["primary"])
        self.assertIn("mesh-bg-panel", variables)
        self.assertTrue(all(key.startswith("mesh-") for key in variables))

    def test_every_theme_meets_semantic_text_contrast_gate(self):
        from mesh_deck.ui.accessibility import palette_contrast_failures

        failures = {
            name: palette_contrast_failures(palette)
            for name, palette in THEMES.items()
        }
        self.assertEqual({name: issues for name, issues in failures.items() if issues}, {})

    def test_contrast_helper_rejects_invalid_colour_values(self):
        from mesh_deck.ui.accessibility import contrast_ratio

        with self.assertRaises(ValueError):
            contrast_ratio("not-a-colour", "#000000")

    def test_primary_ui_screens_declare_visible_focus_treatment(self):
        from mesh_deck.ui.channel_chat import ChannelChatScreen
        from mesh_deck.ui.device_selector import DeviceSelectorScreen
        from mesh_deck.ui.device_settings import DeviceSettingsScreen
        from mesh_deck.ui.interactive_table import InteractiveNodesScreen
        from mesh_deck.ui.repl import MeshDeckApp

        for screen in (
            MeshDeckApp,
            InteractiveNodesScreen,
            ChannelChatScreen,
            DeviceSelectorScreen,
            DeviceSettingsScreen,
        ):
            self.assertIn(":focus", screen.CSS)
            self.assertIn("double $mesh-primary", screen.CSS)


class TestNodePresentation(unittest.TestCase):
    """Node values must agree across every UI surface."""

    def test_presentation_reuses_semantic_formatters(self):
        from mesh_deck.ui.node_presentation import plain_markup, present_node

        node = NodeData(
            id="!00000001",
            long_name="Relay",
            short_name="RLY",
            hw_model="RAK4631",
            role="ROUTER",
            snr=4.25,
            hops_away=1,
            battery_level=55,
            voltage=3.8,
        )
        display = present_node(node, lang="en", distance_km=1.25)

        self.assertEqual(display.snr_text, plain_markup(format_snr(node.snr)))
        self.assertEqual(display.hops_text, plain_markup(format_hops(node.hops_away, "en")))
        self.assertEqual(display.battery_text, plain_markup(format_battery(node.battery_level, node.voltage)))
        self.assertEqual(display.distance_text, plain_markup(format_distance(1.25)))
        self.assertIn("ROUTER", display.role_markup)


class TestInteractiveNodesSorting(unittest.IsolatedAsyncioTestCase):
    """Sorting must never crash on columns that mix values with '--' placeholders."""

    def _store(self):
        located = NodeData(id="!aaa", num=1, long_name="Alpha", short_name="ALFA", snr=7.5, hops_away=2)
        far = NodeData(id="!bbb", num=2, long_name="Bravo", short_name="BRVO", snr=-3.0, hops_away=0)
        unknown = NodeData(id="!ccc", num=3, long_name="Charlie Room", short_name="CHRL")
        store = unittest.mock.MagicMock()
        store.get_all_nodes.return_value = [located, far, unknown]
        distances = {"!aaa": 0.82, "!bbb": 14.3, "!ccc": None}
        store.calculate_distance.side_effect = lambda _local, node_id: distances[node_id]
        return store, NodeData(id="!local", num=9, long_name="Base")

    async def test_every_column_sorts_both_directions_with_missing_values(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="it")
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            column_count = len(screen.column_keys)
            self.assertGreater(column_count, 0)
            for col_idx in range(column_count):
                for reverse in (False, True):
                    screen._sort_and_repopulate(col_idx, reverse)
                    await pilot.pause()

    async def test_distance_column_orders_numerically_with_missing_last(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="it")
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            distance_idx = screen.column_keys.index("distance")
            screen._sort_and_repopulate(distance_idx, False)
            await pilot.pause()
            ordered = [row[distance_idx] for row in screen._raw_rows]
            # 820 m < 14.3 km, and the node without a fix sorts last.
            self.assertEqual(ordered[0], "820 m")
            self.assertEqual(ordered[-1], "--")


class TestInteractiveNodesMasterDetail(unittest.IsolatedAsyncioTestCase):
    """The node explorer keeps details and responsive density in one interaction model."""

    def _store(self):
        from mesh_deck.core.node_store import NodeStore

        store = NodeStore()
        local = NodeData(
            id="!00000001",
            num=1,
            long_name="Base",
            short_name="BASE",
            latitude=45.0,
            longitude=9.0,
            is_local=True,
        )
        remote = NodeData(
            id="!00000002",
            num=2,
            long_name="Remote",
            short_name="RMT",
            role="ROUTER",
            snr=6.5,
            hops_away=1,
            battery_level=78,
            voltage=3.98,
            latitude=45.1,
            longitude=9.2,
        )
        store.update_node(local)
        store.update_node(remote)
        store.set_local_node_id(local.id)
        return store, local, remote

    async def test_wide_mode_renders_selected_node_in_side_detail(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local, remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="full")
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            screen._open_node(remote.id)
            await pilot.pause()
            self.assertTrue(screen.query_one("#detail-container").display)
            self.assertIn("Remote", str(screen.query_one("#detail-heading").content))
            self.assertIsInstance(screen.query_one("#node-detail").content, Panel)

    async def test_compact_mode_opens_internal_detail_screen(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp, NodeDetailScreen

        store, local, remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="compact")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            self.assertFalse(screen.query_one("#detail-container").display)
            screen._open_node(remote.id)
            await pilot.pause()
            self.assertIsInstance(app.screen, NodeDetailScreen)
            self.assertIsInstance(app.screen.query_one("#compact-node-detail").content, Panel)

    async def test_enter_opens_exactly_one_detail_for_the_selected_row(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp, NodeDetailScreen
        from textual.widgets import DataTable

        store, local, _remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="compact")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            table = app.screen.query_one(DataTable)
            table.focus()
            table.move_cursor(row=1, column=0)
            initial_screen_count = len(app.screen_stack)
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, NodeDetailScreen)
            self.assertEqual(len(app.screen_stack), initial_screen_count + 1)

    async def test_compact_mode_uses_only_operator_critical_columns(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local, _remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="compact")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            self.assertEqual(
                screen.column_keys,
                ["name", "role", "snr", "hops", "battery", "last_heard"],
            )
            self.assertNotIn("id", screen.column_keys)
            self.assertNotIn("distance", screen.column_keys)

    async def test_auto_mode_selects_density_from_terminal_width(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local, _remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="auto")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            self.assertTrue(app.screen.is_compact)
            self.assertNotIn("distance", app.screen.column_keys)

        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="auto")
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()
            self.assertFalse(app.screen.is_compact)
            self.assertIn("distance", app.screen.column_keys)

    async def test_view_mode_cycle_persists_through_callback(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local, _remote = self._store()
        changed = []
        app = InteractiveNodesApp(store, local_node=local, lang="en", view_mode="full")
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            screen._on_view_mode_change = changed.append
            screen.action_cycle_view_mode()
            await pilot.pause()
            self.assertEqual(screen.view_mode, "compact")
            self.assertEqual(changed, ["compact"])
            self.assertEqual(
                screen.column_keys,
                ["name", "role", "snr", "hops", "battery", "last_heard"],
            )

    async def test_language_update_refreshes_explorer_labels(self):
        from mesh_deck.ui.interactive_table import InteractiveNodesApp

        store, local, _remote = self._store()
        app = InteractiveNodesApp(store, local_node=local, lang="it", view_mode="full")
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            screen.update_language("en")
            await pilot.pause()
            self.assertIn("INTERACTIVE NODE EXPLORER", screen.title)
            self.assertEqual(str(screen.query_one("#filter-label").content), "🔍 Filter:")
            self.assertEqual(screen.column_keys[0], "idx")


class TestNodeSidebarLiveUpdates(unittest.IsolatedAsyncioTestCase):
    """Node updates arriving from the radio thread must repaint the sidebar, coalesced."""

    def _make_repl(self, nodes):
        from mesh_deck.ui.repl import MeshDeckREPL

        client = unittest.mock.MagicMock()
        client.store.get_all_nodes.return_value = nodes
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        client._node_callbacks = []
        client.on_node_updated.side_effect = client._node_callbacks.append
        settings = Settings()
        settings.save = lambda: True
        return MeshDeckREPL(client, console=unittest.mock.MagicMock(),
                            dispatcher=unittest.mock.MagicMock(), settings=settings), client

    async def test_node_update_repaints_sidebar_once_per_burst(self):
        from mesh_deck.ui.repl import MeshDeckApp

        node = NodeData(id="!aaa", num=1, long_name="Alpha", short_name="ALFA")
        repl, client = self._make_repl([node])
        app = MeshDeckApp(repl)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.refresh_sidebar()
            await pilot.pause()

            with unittest.mock.patch.object(app, "refresh_sidebar") as repaint:
                # A burst of radio-side updates collapses into one pending repaint.
                for _ in range(20):
                    app.request_sidebar_refresh()
                self.assertTrue(app._sidebar_refresh_pending)
                repaint.assert_not_called()
                app._flush_sidebar_refresh()
                repaint.assert_called_once()

    async def test_repl_forwards_node_updates_to_the_console_bridge(self):
        node = NodeData(id="!bbb", num=2, long_name="Bravo", short_name="BRVO")
        repl, client = self._make_repl([node])
        # MeshDeckREPL must have subscribed to the radio's node updates.
        self.assertEqual(len(client._node_callbacks), 1)
        client._node_callbacks[0](node)
        repl.console.request_sidebar_refresh.assert_called_once_with()

    async def test_disabled_sidebar_skips_scheduling(self):
        from mesh_deck.ui.repl import MeshDeckApp

        node = NodeData(id="!ccc", num=3, long_name="Charlie", short_name="CHRL")
        repl, _client = self._make_repl([node])
        repl.settings.sidebar_enabled = False
        app = MeshDeckApp(repl)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.request_sidebar_refresh()
            self.assertFalse(app._sidebar_refresh_pending)


class TestScreenshotGenerator(unittest.TestCase):
    """The docs screenshot generator must keep working as the UI evolves."""

    def _module(self):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "tools" / "make_screenshots.py"
        spec = importlib.util.spec_from_file_location("make_screenshots", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_sample_data_renders_every_rich_surface(self):
        module = self._module()
        store = module._sample_store()
        local = store.get_local_node()
        self.assertIsNotNone(local)
        self.assertTrue(local.is_local)
        # Sample data must exercise distance and bearing, not just names.
        target = store.get_node("ZION")
        self.assertIsNotNone(store.calculate_distance(local.id, target.id))
        self.assertIsNotNone(store.calculate_bearing(local.id, target.id))

        console = module._console()
        console.print(render_banner(local, port="/dev/ttyACM0", channels=module._sample_channels()))
        console.print(render_nodes_table(store.get_all_nodes(), local_node_id=local.id))
        console.print(render_node_detail(target, distance_km=1.0, bearing_deg=42.0))
        for msg in module._sample_messages():
            console.print(render_message(msg))
        exported = console.export_svg(title="test")
        self.assertIn("MRPH", exported)
        self.assertIn("ZION", exported)

    def test_sample_rendering_is_exercised_for_every_theme(self):
        module = self._module()
        store = module._sample_store()
        local = store.get_local_node()
        try:
            for theme_name in THEMES:
                set_theme(theme_name)
                console = module._console()
                console.print(render_banner(local, port="/dev/ttyACM0", channels=module._sample_channels()))
                console.print(render_nodes_table(store.get_all_nodes(), local_node_id=local.id))
                exported = console.export_svg(title=theme_name)
                self.assertIn("MRPH", exported)
        finally:
            set_theme("cyberpunk")


class TestConsoleBridgeTeardown(unittest.IsolatedAsyncioTestCase):
    """Radio threads keep publishing while the app shuts down; the bridge must absorb it."""

    async def test_console_print_after_shutdown_is_swallowed(self):
        from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL, TextualConsole

        client = unittest.mock.MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        settings = Settings()
        settings.save = lambda: True
        repl = MeshDeckREPL(client, console=unittest.mock.MagicMock(),
                            dispatcher=unittest.mock.MagicMock(), settings=settings)
        app = MeshDeckApp(repl)
        async with app.run_test() as pilot:
            await pilot.pause()
            console = TextualConsole(app)
            console.print("still alive")

        # The app is stopped and its widgets are gone: a late radio callback
        # must not raise NoMatches or "App is not running".
        console.print("too late")
        console.request_sidebar_refresh()
        console.notify_message(MeshMessage(sender_id="!a", text="late"))

    async def test_connection_change_callback_survives_a_dead_app(self):
        from mesh_deck.ui.repl import MeshDeckApp, MeshDeckREPL, TextualConsole

        client = unittest.mock.MagicMock()
        client.store.get_all_nodes.return_value = []
        client.get_local_node.return_value = None
        client.get_channels.return_value = []
        settings = Settings()
        settings.save = lambda: True
        repl = MeshDeckREPL(client, console=unittest.mock.MagicMock(),
                            dispatcher=unittest.mock.MagicMock(), settings=settings)
        app = MeshDeckApp(repl)
        async with app.run_test() as pilot:
            await pilot.pause()
            repl.console = TextualConsole(app)

        # Exactly the teardown race seen in the wild: the radio reports the
        # connection loss after the screen is gone.
        repl._handle_connection_change(False, "COM6")


if __name__ == "__main__":
    unittest.main()
