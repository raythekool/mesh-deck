"""Unit tests for Mesh-Deck CommandDispatcher with comprehensive edge cases."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from mesh_deck.commands.dispatcher import CommandDispatcher
from mesh_deck.core.events import DeviceConnectionInfo, NodeData


class TestCommandDispatcher(unittest.TestCase):
    """Test suite for command dispatching, execution, and robust error handling."""

    def setUp(self) -> None:
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
        self.remote_node = NodeData(
            id="!62d927b8",
            num=1658398648,
            long_name="Trinity Recon Scout",
            short_name="TRIN",
            hw_model="TLORA_T3_S3",
            role="CLIENT",
            snr=11.5,
            hops_away=0,
            is_local=False,
        )

        self.mock_client.get_local_node.return_value = self.local_node
        self.mock_store.get_all_nodes.return_value = [self.local_node, self.remote_node]
        self.mock_store.calculate_distance.return_value = 14.2
        self.mock_store.get_node.side_effect = lambda q: self.remote_node if "62d927b8" in q or "TRIN" in q else None
        self.mock_client.get_channels.return_value = [
            {"index": 0, "name": "Primary", "role": "PRIMARY", "uplink_enabled": True, "downlink_enabled": True, "has_psk": True}
        ]
        self.mock_client.get_my_info.return_value = {
            "region": "EU_868",
            "modem_preset": "MEDIUM_FAST",
            "firmware_version": "2.5.1",
        }

        # Null console to avoid stdout clutter
        self.console = Console(quiet=True)
        self.dispatcher = CommandDispatcher(self.mock_client, console=self.console)

    def test_dispatch_help(self) -> None:
        res = self.dispatcher.dispatch("/help")
        self.assertTrue(res)

        res_q = self.dispatcher.dispatch("/?")
        self.assertTrue(res_q)

    def test_dispatch_nodes(self) -> None:
        res = self.dispatcher.dispatch("/nodes")
        self.assertTrue(res)
        self.mock_store.get_all_nodes.assert_called_with(sort_by="last_heard", active_only=False)

    def test_dispatch_nodes_filtered_and_sorted(self) -> None:
        self.dispatcher.dispatch("/nodes active")
        self.mock_store.get_all_nodes.assert_called_with(sort_by="last_heard", active_only=True)

        self.dispatcher.dispatch("/nodes snr")
        self.mock_store.get_all_nodes.assert_called_with(sort_by="snr", active_only=False)

        # Invalid option falls back to default without crashing
        self.dispatcher.dispatch("/nodes unknown_sort_option")
        self.mock_store.get_all_nodes.assert_called_with(sort_by="last_heard", active_only=False)

    def test_dispatch_nodes_empty(self) -> None:
        self.mock_store.get_all_nodes.return_value = []
        res = self.dispatcher.dispatch("/nodes")
        self.assertTrue(res)

    def test_dispatch_node_found(self) -> None:
        res = self.dispatcher.dispatch("/node TRIN")
        self.assertTrue(res)
        self.mock_store.get_node.assert_called_with("TRIN")

    def test_dispatch_node_missing_arg(self) -> None:
        # Calling /node with no query should not crash
        res = self.dispatcher.dispatch("/node")
        self.assertTrue(res)

    def test_dispatch_node_not_found(self) -> None:
        res = self.dispatcher.dispatch("/node NON_EXISTENT")
        self.assertTrue(res)

    def test_dispatch_send_broadcast(self) -> None:
        self.mock_client.send_broadcast.return_value = True
        res = self.dispatcher.dispatch("/send Hello mesh network!")
        self.assertTrue(res)
        self.mock_client.send_broadcast.assert_called_with("Hello mesh network!")

    def test_dispatch_send_missing_arg(self) -> None:
        # /send without text
        res = self.dispatcher.dispatch("/send")
        self.assertTrue(res)

        res_spaces = self.dispatcher.dispatch("/send    ")
        self.assertTrue(res_spaces)

    def test_dispatch_send_unclosed_quotes(self) -> None:
        # Unclosed quotation should be handled cleanly without crashing shlex
        self.mock_client.send_broadcast.return_value = True
        res = self.dispatcher.dispatch('/send "Unclosed quote text')
        self.assertTrue(res)
        self.mock_client.send_broadcast.assert_called()

    def test_dispatch_plaintext_as_broadcast(self) -> None:
        self.mock_client.send_broadcast.return_value = True
        res = self.dispatcher.dispatch("Direct broadcast message")
        self.assertTrue(res)
        self.mock_client.send_broadcast.assert_called_with("Direct broadcast message")

    def test_dispatch_dm(self) -> None:
        self.mock_client.send_dm.return_value = True
        res = self.dispatcher.dispatch("/dm TRIN Secret ping message")
        self.assertTrue(res)
        self.mock_client.send_dm.assert_called_with("!62d927b8", "Secret ping message")

    def test_dispatch_dm_missing_args(self) -> None:
        # /dm with no args or only target
        res1 = self.dispatcher.dispatch("/dm")
        self.assertTrue(res1)

        res2 = self.dispatcher.dispatch("/dm TRIN")
        self.assertTrue(res2)

    def test_dispatch_dm_quoted_args(self) -> None:
        self.mock_client.send_dm.return_value = True
        res = self.dispatcher.dispatch('/dm "TRIN" "Hello from quotes"')
        self.assertTrue(res)
        self.mock_client.send_dm.assert_called_with("!62d927b8", "Hello from quotes")

    def test_dispatch_dm_unclosed_quotes(self) -> None:
        self.mock_client.send_dm.return_value = True
        res = self.dispatcher.dispatch('/dm "TRIN Unclosed message')
        self.assertTrue(res)
        self.mock_client.send_dm.assert_called()

    def test_dispatch_channels(self) -> None:
        res = self.dispatcher.dispatch("/channels")
        self.assertTrue(res)
        self.mock_client.get_channels.assert_called()

    def test_dispatch_channels_empty(self) -> None:
        self.mock_client.get_channels.return_value = []
        res = self.dispatcher.dispatch("/channels")
        self.assertTrue(res)

    def test_dispatch_info(self) -> None:
        res = self.dispatcher.dispatch("/info")
        self.assertTrue(res)
        self.mock_client.get_my_info.assert_called()

    def test_dispatch_info_disconnected(self) -> None:
        self.mock_client.get_my_info.return_value = None
        self.mock_client.get_local_node.return_value = None
        res = self.dispatcher.dispatch("/info")
        self.assertTrue(res)

    @patch("mesh_deck.commands.dispatcher.scan_meshtastic_ports")
    def test_dispatch_scan(self, mock_scan) -> None:
        mock_scan.return_value = [
            DeviceConnectionInfo(port="/dev/ttyACM0", description="Heltec", hw_name="Heltec V3"),
            DeviceConnectionInfo(port="/dev/ttyACM1", description="LilyGo", hw_name="LilyGo T-Beam"),
        ]
        res = self.dispatcher.dispatch("/scan")
        self.assertTrue(res)

    @patch("mesh_deck.commands.dispatcher.scan_meshtastic_ports")
    def test_dispatch_scan_empty(self, mock_scan) -> None:
        mock_scan.return_value = []
        res = self.dispatcher.dispatch("/scan")
        self.assertTrue(res)

    @patch("mesh_deck.commands.dispatcher.scan_meshtastic_ports")
    def test_dispatch_switch(self, mock_scan) -> None:
        p1 = DeviceConnectionInfo(port="/dev/ttyACM0", description="Heltec", hw_name="Heltec V3")
        p2 = DeviceConnectionInfo(port="/dev/ttyACM1", description="LilyGo", hw_name="LilyGo T-Beam")
        mock_scan.return_value = [p1, p2]
        self.mock_client.connect.return_value = True

        # Switch by port name
        res = self.dispatcher.dispatch("/switch /dev/ttyACM1")
        self.assertTrue(res)
        self.mock_client.connect.assert_called_with("/dev/ttyACM1", blocking=True)

        # Switch by index 1
        res_idx = self.dispatcher.dispatch("/switch 1")
        self.assertTrue(res_idx)
        self.mock_client.connect.assert_called_with("/dev/ttyACM0", blocking=True)

        # Switch by invalid index (e.g. 99 or 0)
        res_inv = self.dispatcher.dispatch("/switch 99")
        self.assertTrue(res_inv)

    @patch("mesh_deck.commands.dispatcher.scan_meshtastic_ports")
    def test_dispatch_switch_no_ports(self, mock_scan) -> None:
        mock_scan.return_value = []
        res = self.dispatcher.dispatch("/switch")
        self.assertTrue(res)

    def test_dispatch_clear_and_banner(self) -> None:
        res_b = self.dispatcher.dispatch("/banner")
        self.assertTrue(res_b)

        res_c = self.dispatcher.dispatch("/clear")
        self.assertTrue(res_c)

    @unittest.mock.patch("mesh_deck.ui.interactive_table.launch_interactive_nodes")
    def test_dispatch_view(self, mock_launch) -> None:
        res = self.dispatcher.dispatch("/view")
        self.assertTrue(res)
        mock_launch.assert_called_once()

    def test_dispatch_settings_view(self) -> None:
        res = self.dispatcher.dispatch("/settings")
        self.assertTrue(res)

    def test_dispatch_settings_update(self) -> None:
        self.assertTrue(self.dispatcher.dispatch("/settings lang en"))
        self.assertTrue(self.dispatcher.dispatch("/settings lang it"))
        self.assertTrue(self.dispatcher.dispatch("/settings theme high_contrast"))
        self.assertTrue(self.dispatcher.dispatch("/settings theme cyberpunk"))
        self.assertTrue(self.dispatcher.dispatch("/settings sort snr"))
        self.assertTrue(self.dispatcher.dispatch("/settings port /dev/ttyACM0"))

    def test_dispatch_unknown_command(self) -> None:
        res = self.dispatcher.dispatch("/not_a_valid_command")
        self.assertTrue(res)

    def test_dispatch_empty_input(self) -> None:
        self.assertTrue(self.dispatcher.dispatch(""))
        self.assertTrue(self.dispatcher.dispatch("   "))
        self.assertTrue(self.dispatcher.dispatch("\t\n"))

    def test_dispatch_quit(self) -> None:
        res = self.dispatcher.dispatch("/quit")
        self.assertFalse(res)
        self.assertFalse(self.dispatcher.running)
        self.mock_client.disconnect.assert_called()


if __name__ == "__main__":
    unittest.main()
