"""Unit tests for Mesh-Deck CommandDispatcher."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from rich.console import Console

from mesh_deck.commands.dispatcher import CommandDispatcher
from mesh_deck.core.events import NodeData


class TestCommandDispatcher(unittest.TestCase):
    """Test suite for command dispatching and execution."""

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

    def test_dispatch_nodes(self) -> None:
        res = self.dispatcher.dispatch("/nodes")
        self.assertTrue(res)
        self.mock_store.get_all_nodes.assert_called_with(sort_by="last_heard", active_only=False)

    def test_dispatch_node_found(self) -> None:
        res = self.dispatcher.dispatch("/node TRIN")
        self.assertTrue(res)
        self.mock_store.get_node.assert_called_with("TRIN")

    def test_dispatch_send_broadcast(self) -> None:
        self.mock_client.send_broadcast.return_value = True
        res = self.dispatcher.dispatch("/send Hello mesh network!")
        self.assertTrue(res)
        self.mock_client.send_broadcast.assert_called_with("Hello mesh network!")

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

    def test_dispatch_channels(self) -> None:
        res = self.dispatcher.dispatch("/channels")
        self.assertTrue(res)
        self.mock_client.get_channels.assert_called()

    def test_dispatch_info(self) -> None:
        res = self.dispatcher.dispatch("/info")
        self.assertTrue(res)
        self.mock_client.get_my_info.assert_called()

    def test_dispatch_quit(self) -> None:
        res = self.dispatcher.dispatch("/quit")
        self.assertFalse(res)
        self.assertFalse(self.dispatcher.running)
        self.mock_client.disconnect.assert_called()


if __name__ == "__main__":
    unittest.main()
