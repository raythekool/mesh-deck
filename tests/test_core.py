"""Unit tests for the mesh_deck.core package."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from mesh_deck.core.events import DeviceConnectionInfo, MeshMessage, NodeData
from mesh_deck.core.node_store import NodeStore
from mesh_deck.core.radio_client import RadioClient
from mesh_deck.core.scanner import scan_meshtastic_ports


class TestEvents(unittest.TestCase):
    """Test NodeData, MeshMessage, and DeviceConnectionInfo dataclasses."""

    def test_node_data_creation_and_properties(self):
        node = NodeData(
            id="!45a466e4",
            num=1168467684,
            long_name="Heltec Vision Master",
            short_name="HVME",
            hw_model="HELTEC_V2_0",
            role="CLIENT",
            snr=10.5,
            hops_away=0,
            battery_level=95,
            voltage=4.12,
            channel_util=12.5,
            air_util_tx=1.2,
            latitude=45.4642,
            longitude=9.1900,
            altitude=120.0,
            last_heard=datetime(2026, 9, 16, 12, 0, 0),
            is_local=True,
            is_favorite=True,
        )

        self.assertEqual(node.id, "!45a466e4")
        self.assertEqual(node.num, 1168467684)
        self.assertEqual(node.aka, "HVME")
        self.assertEqual(node.hardware, "HELTEC_V2_0")
        self.assertEqual(node.channel_utilization, 12.5)
        self.assertTrue(node.has_position)
        self.assertTrue(node.has_coords)
        self.assertEqual(node.display_name, "Heltec Vision Master")
        self.assertIn("45.46420°", node.coords_str)

        d = node.to_dict()
        self.assertEqual(d["id"], "!45a466e4")
        self.assertTrue(d["is_local"])

    def test_mesh_message_creation_and_properties(self):
        msg = MeshMessage(
            sender_id="!45a466e4",
            sender_name="Heltec Node",
            receiver_id="^all",
            text="Hello Mesh!",
            channel=0,
            snr=8.5,
            hops=1,
            is_dm=False,
        )

        self.assertEqual(msg.recipient_id, "^all")
        self.assertFalse(msg.is_direct)
        self.assertEqual(msg.hops_away, 1)

        d = msg.to_dict()
        self.assertEqual(d["text"], "Hello Mesh!")
        self.assertFalse(d["is_dm"])

    def test_device_connection_info(self):
        dev = DeviceConnectionInfo(
            port="/dev/ttyACM0",
            description="Heltec Vision Master E290 - TinyUSB CDC",
            hw_name="Heltec Vision Master E290",
            is_connected=False,
        )
        self.assertEqual(dev.port, "/dev/ttyACM0")
        self.assertEqual(dev.hw_name, "Heltec Vision Master E290")
        self.assertFalse(dev.is_connected)


class TestScanner(unittest.TestCase):
    """Test serial port scanner and heuristics."""

    def test_scan_meshtastic_ports_on_current_system(self):
        ports = scan_meshtastic_ports()
        self.assertIsInstance(ports, list)
        self.assertGreaterEqual(len(ports), 2)

        port_names = [p.port for p in ports]
        self.assertIn("/dev/ttyACM0", port_names)
        self.assertIn("/dev/ttyACM1", port_names)

        acm0 = next(p for p in ports if p.port == "/dev/ttyACM0")
        self.assertEqual(acm0.hw_name, "Heltec Vision Master E290")

        acm1 = next(p for p in ports if p.port == "/dev/ttyACM1")
        self.assertEqual(acm1.hw_name, "LilyGo TLora-T3S3-V1")


class TestNodeStore(unittest.TestCase):
    """Test NodeStore caching, updates, Haversine distance, and queries."""

    def setUp(self):
        self.store = NodeStore()
        # Local node in Milan
        self.local_node = self.store.update_from_node_dict({
            "num": 1168467684,
            "user": {
                "id": "!45a466e4",
                "longName": "Milan Heltec Local",
                "shortName": "MILA",
                "hwModel": 5,  # HELTEC_V2_0
                "role": 0,  # CLIENT
            },
            "position": {
                "latitude": 45.4642,
                "longitude": 9.1900,
                "altitude": 120.0,
            },
            "snr": 12.0,
            "hopsAway": 0,
        }, is_local=True)
        self.store.set_local_node_id("!45a466e4")

    def test_update_and_lookup(self):
        # Remote node in Rome
        remote_node = self.store.update_from_node_dict({
            "num": 3103310553,
            "user": {
                "id": "!b8f862d9",
                "longName": "Rome LilyGo Remote",
                "shortName": "ROME",
            },
            "position": {
                "latitude": 41.9028,
                "longitude": 12.4964,
            },
            "snr": 4.5,
            "hopsAway": 2,
            "lastHeard": 1700000000,
        })

        self.assertEqual(len(self.store), 2)
        self.assertEqual(self.store.get_local_node().id, "!45a466e4")

        # Query by hex ID
        self.assertEqual(self.store.get_node("!b8f862d9").short_name, "ROME")
        self.assertEqual(self.store.get_node("b8f862d9").short_name, "ROME")

        # Query by AKA
        self.assertEqual(self.store.get_node("ROME").id, "!b8f862d9")

        # Query by substring of long name
        self.assertEqual(self.store.get_node("lilygo").id, "!b8f862d9")
        self.assertEqual(self.store.get_node("heltec").id, "!45a466e4")

        # Query by decimal num
        self.assertEqual(self.store.get_node("3103310553").short_name, "ROME")

    def test_haversine_distance(self):
        remote_node = self.store.update_from_node_dict({
            "num": 3103310553,
            "user": {"id": "!b8f862d9", "longName": "Rome", "shortName": "ROME"},
            "position": {"latitude": 41.9028, "longitude": 12.4964},
        })

        # Distance between Milan and Rome is ~476.88 km
        dist = self.store.calculate_distance("!b8f862d9")
        self.assertIsNotNone(dist)
        self.assertAlmostEqual(dist, 476.88, delta=1.0)
        self.assertEqual(remote_node.distance_km, dist)

    def test_telemetry_and_position_packet_updates(self):
        # Update telemetry
        telem_packet = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "rxSnr": 11.5,
            "decoded": {
                "telemetry": {
                    "deviceMetrics": {
                        "batteryLevel": 88,
                        "voltage": 4.05,
                        "channelUtilization": 7.2,
                        "airUtilTx": 0.8,
                    }
                }
            },
        }
        updated = self.store.update_from_telemetry_packet(telem_packet)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.battery_level, 88)
        self.assertEqual(updated.voltage, 4.05)
        self.assertEqual(updated.channel_util, 7.2)
        self.assertEqual(updated.air_util_tx, 0.8)

        # Update position
        pos_packet = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "decoded": {
                "position": {
                    "latitudeI": 454642000,
                    "longitudeI": 91900000,
                    "altitude": 150,
                }
            },
        }
        pos_updated = self.store.update_from_position_packet(pos_packet)
        self.assertIsNotNone(pos_updated)
        self.assertAlmostEqual(pos_updated.latitude, 45.4642)
        self.assertAlmostEqual(pos_updated.longitude, 9.1900)
        self.assertEqual(pos_updated.altitude, 150.0)

    def test_sorting_and_filtering(self):
        # Insert a third node with recent last_heard
        self.store.update_from_node_dict({
            "num": 999,
            "user": {"id": "!000003e7", "longName": "Alpha Node", "shortName": "ALPH"},
            "snr": 15.0,
            "hopsAway": 3,
            "lastHeard": datetime.now().timestamp(),
        })

        by_snr = self.store.get_all_nodes(sort_by="snr")
        self.assertEqual(by_snr[0].short_name, "ALPH")  # Highest SNR (15.0)

        by_hops = self.store.get_all_nodes(sort_by="hops")
        self.assertEqual(by_hops[0].short_name, "MILA")  # 0 hops

        by_name = self.store.get_all_nodes(sort_by="name")
        self.assertEqual(by_name[0].short_name, "ALPH")  # Alpha Node first alphabetically


class TestRadioClient(unittest.TestCase):
    """Test RadioClient pubsub event routing, callback dispatch, and state queries."""

    def test_radio_client_events_and_routing(self):
        store = NodeStore()
        client = RadioClient(node_store=store)

        received_messages = []
        updated_nodes = []
        received_telemetry = []

        client.on_message_received(lambda msg: received_messages.append(msg))
        client.on_node_updated(lambda node: updated_nodes.append(node))
        client.on_telemetry_received(lambda pkt, node: received_telemetry.append((pkt, node)))

        # Simulate pubsub text message
        fake_text_pkt = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "to": 0xFFFFFFFF,
            "toId": "^all",
            "channel": 0,
            "rxSnr": 9.0,
            "rxTime": int(datetime.now().timestamp()),
            "decoded": {
                "text": "Broadcast from test",
            },
        }

        # Trigger internal pubsub handler directly
        client._on_pubsub_text(fake_text_pkt)

        self.assertEqual(len(received_messages), 1)
        msg = received_messages[0]
        self.assertEqual(msg.sender_id, "!45a466e4")
        self.assertEqual(msg.text, "Broadcast from test")
        self.assertFalse(msg.is_dm)

        # Simulate node updated
        fake_node = {
            "num": 1168467684,
            "user": {"id": "!45a466e4", "longName": "Heltec E290", "shortName": "E290"},
        }
        client._on_pubsub_node_updated(fake_node)
        self.assertGreaterEqual(len(updated_nodes), 1)
        self.assertEqual(updated_nodes[-1].short_name, "E290")

        # Simulate telemetry
        fake_telemetry_pkt = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "decoded": {
                "telemetry": {
                    "deviceMetrics": {
                        "batteryLevel": 100,
                        "voltage": 4.2,
                    }
                }
            },
        }
        client._on_pubsub_telemetry(fake_telemetry_pkt)
        self.assertEqual(len(received_telemetry), 1)
        pkt, node = received_telemetry[0]
        self.assertEqual(node.battery_level, 100)

    def test_send_broadcast_and_dm_with_mock_interface(self):
        client = RadioClient()
        mock_iface = MagicMock()
        mock_iface.sendText.return_value = {"id": 12345}

        client._interface = mock_iface
        client._is_connected = True

        res_bc = client.send_broadcast("Test Broadcast", channel_index=1)
        self.assertEqual(res_bc, {"id": 12345})
        mock_iface.sendText.assert_called_with(text="Test Broadcast", destinationId="^all", channelIndex=1)

        res_dm = client.send_dm("!b8f862d9", "Secret DM")
        self.assertEqual(res_dm, {"id": 12345})
        mock_iface.sendText.assert_called_with(text="Secret DM", destinationId="!b8f862d9", wantAck=True)

    def test_send_fails_when_disconnected(self):
        client = RadioClient()
        self.assertFalse(client.is_connected)

        with self.assertRaises(ConnectionError):
            client.send_broadcast("Will fail")

        with self.assertRaises(ConnectionError):
            client.send_dm("!b8f862d9", "Will fail")


if __name__ == "__main__":
    unittest.main()
