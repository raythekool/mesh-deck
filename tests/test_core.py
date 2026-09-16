"""Rigorous unit and integration test suite for the mesh_deck.core package."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from mesh_deck.core.events import DeviceConnectionInfo, MeshMessage, NodeData
from mesh_deck.core.node_store import NodeStore
from mesh_deck.core.radio_client import RadioClient
from mesh_deck.core.scanner import scan_meshtastic_ports


class TestEvents(unittest.TestCase):
    """Test NodeData, MeshMessage, and DeviceConnectionInfo dataclasses and edge cases."""

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
        self.assertIn("openstreetmap.org", node.osm_url)

        d = node.to_dict()
        self.assertEqual(d["id"], "!45a466e4")
        self.assertTrue(d["is_local"])

    def test_node_data_invalid_coordinates(self):
        # Out of bounds latitude (> 90)
        n1 = NodeData(id="!1", num=1, latitude=95.0, longitude=10.0)
        self.assertFalse(n1.has_position)
        self.assertFalse(n1.has_coords)
        self.assertEqual(n1.coords_str, "N/A")
        self.assertIsNone(n1.osm_url)

        # Out of bounds latitude (< -90)
        n2 = NodeData(id="!2", num=2, latitude=-95.0, longitude=10.0)
        self.assertFalse(n2.has_position)

        # Out of bounds longitude (> 180)
        n3 = NodeData(id="!3", num=3, latitude=45.0, longitude=185.0)
        self.assertFalse(n3.has_position)

        # Out of bounds longitude (< -180)
        n4 = NodeData(id="!4", num=4, latitude=45.0, longitude=-195.0)
        self.assertFalse(n4.has_position)

        # GPS glitch 0.0, 0.0
        n5 = NodeData(id="!5", num=5, latitude=0.0, longitude=0.0)
        self.assertFalse(n5.has_position)

        # None coordinates
        n6 = NodeData(id="!6", num=6, latitude=None, longitude=None)
        self.assertFalse(n6.has_position)

    def test_node_data_from_meshtastic_dict(self):
        raw = {
            "num": 1168467684,
            "user": {
                "id": "!45a466e4",
                "longName": "Heltec E290",
                "shortName": "E290",
                "hwModel": 5,
                "role": 0,
                "publicKey": "base64key",
                "isLicensed": True,
            },
            "position": {
                "latitudeI": 454642000,
                "longitudeI": 91900000,
                "altitude": 140,
            },
            "deviceMetrics": {
                "batteryLevel": 88,
                "voltage": 4.02,
                "channelUtilization": 5.5,
                "airUtilTx": 0.5,
            },
            "environmentMetrics": {
                "temperature": 22.4,
                "relativeHumidity": 55.0,
                "barometricPressure": 1013.2,
            },
            "snr": 9.5,
            "hopsAway": 1,
            "isFavorite": True,
            "lastHeard": 1700000000,
        }
        node = NodeData.from_meshtastic_dict(raw, is_local=True)
        self.assertEqual(node.id, "!45a466e4")
        self.assertEqual(node.num, 1168467684)
        self.assertTrue(node.is_local)
        self.assertTrue(node.is_favorite)
        self.assertAlmostEqual(node.latitude, 45.4642)
        self.assertAlmostEqual(node.longitude, 9.1900)
        self.assertEqual(node.altitude, 140.0)
        self.assertEqual(node.temperature, 22.4)
        self.assertEqual(node.relative_humidity, 55.0)
        self.assertEqual(node.barometric_pressure, 1013.2)
        self.assertTrue(node.is_licensed)
        self.assertEqual(node.public_key, "base64key")

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
        d = dev.to_dict()
        self.assertEqual(d["port"], "/dev/ttyACM0")


class TestScanner(unittest.TestCase):
    """Test serial port scanner and heuristics under normal and error conditions."""

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

    @patch("serial.tools.list_ports.comports")
    def test_scanner_multiple_and_unusual_devices(self, mock_comports):
        p1 = MagicMock()
        p1.device = "/dev/ttyUSB0"
        p1.vid = 0x10C4  # Silicon Labs
        p1.pid = 0xEA60
        p1.product = "CP2102 USB to UART Bridge Controller"
        p1.description = "CP2102 USB to UART Bridge Controller"
        p1.manufacturer = "Silicon Labs"
        p1.hwid = "USB VID:PID=10C4:EA60"

        p2 = MagicMock()
        p2.device = "/dev/ttyACM2"
        p2.vid = 0x1A86  # CH340
        p2.pid = 0x7523
        p2.product = None
        p2.description = "USB-Serial CH340"
        p2.manufacturer = "wch.cn"
        p2.hwid = "USB VID:PID=1A86:7523"

        p3 = MagicMock()
        p3.device = "/dev/ttyS0"
        p3.vid = None
        p3.pid = None
        p3.product = None
        p3.description = "n/a"
        p3.manufacturer = None
        p3.hwid = "n/a"

        mock_comports.return_value = [p3, p2, p1]

        results = scan_meshtastic_ports()
        self.assertEqual(len(results), 2)
        # Verify sorting
        self.assertEqual(results[0].port, "/dev/ttyACM2")
        self.assertEqual(results[1].port, "/dev/ttyUSB0")
        self.assertIn("CH340", results[0].description)

    @patch("serial.tools.list_ports.comports")
    def test_scanner_handles_exception_in_comports(self, mock_comports):
        mock_comports.side_effect = PermissionError("Permission denied accessing /dev")
        results = scan_meshtastic_ports()
        self.assertEqual(results, [])

    @patch("serial.tools.list_ports.comports")
    def test_scanner_handles_exception_on_single_port(self, mock_comports):
        broken_port = MagicMock()
        type(broken_port).device = unittest.mock.PropertyMock(side_effect=RuntimeError("Broken device"))

        good_port = MagicMock()
        good_port.device = "/dev/ttyACM0"
        good_port.vid = 0x303A
        good_port.product = "Heltec Vision Master E290"
        good_port.description = "Heltec Vision Master E290 - TinyUSB CDC"
        good_port.manufacturer = "Espressif"
        good_port.hwid = "USB VID:PID=303A:0002"

        mock_comports.return_value = [broken_port, good_port]
        results = scan_meshtastic_ports()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].port, "/dev/ttyACM0")


class TestNodeStore(unittest.TestCase):
    """Test NodeStore caching, edge cases, Haversine bounds, search, and sorting."""

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

    def test_haversine_distance_valid_and_invalid(self):
        # Milan to Rome ~ 476.88 km
        d = NodeStore.haversine_distance(45.4642, 9.1900, 41.9028, 12.4964)
        self.assertIsNotNone(d)
        self.assertAlmostEqual(d, 476.88, delta=1.0)

        # Same location
        self.assertEqual(NodeStore.haversine_distance(45.0, 9.0, 45.0, 9.0), 0.0)

        # Invalid latitude (> 90)
        self.assertIsNone(NodeStore.haversine_distance(95.0, 9.0, 41.0, 12.0))
        self.assertIsNone(NodeStore.haversine_distance(45.0, 9.0, -95.0, 12.0))

        # Invalid longitude (> 180)
        self.assertIsNone(NodeStore.haversine_distance(45.0, 195.0, 41.0, 12.0))
        self.assertIsNone(NodeStore.haversine_distance(45.0, 9.0, 41.0, -195.0))

        # 0.0, 0.0 GPS null fix
        self.assertIsNone(NodeStore.haversine_distance(0.0, 0.0, 41.0, 12.0))
        self.assertIsNone(NodeStore.haversine_distance(45.0, 9.0, 0.0, 0.0))

        # None or non-numeric
        self.assertIsNone(NodeStore.haversine_distance(None, 9.0, 41.0, 12.0))
        self.assertIsNone(NodeStore.haversine_distance("invalid", 9.0, 41.0, 12.0))

    def test_calculate_distance_edge_cases(self):
        # Remote node without position
        n_no_pos = self.store.update_from_node_dict({
            "num": 2,
            "user": {"id": "!00000002", "longName": "No Pos", "shortName": "NOP"},
        })
        self.assertIsNone(self.store.calculate_distance("!00000002"))
        self.assertIsNone(n_no_pos.distance_km)

        # Distance to self
        self.assertEqual(self.store.calculate_distance("!45a466e4"), 0.0)

        # Distance between when local node has no position
        store_no_local_pos = NodeStore()
        store_no_local_pos.update_from_node_dict({
            "num": 1,
            "user": {"id": "!1", "longName": "Local No Pos"},
        }, is_local=True)
        store_no_local_pos.set_local_node_id("!1")
        target = store_no_local_pos.update_from_node_dict({
            "num": 2,
            "user": {"id": "!2"},
            "position": {"latitude": 45.0, "longitude": 9.0},
        })
        self.assertIsNone(store_no_local_pos.calculate_distance("!2"))

    def test_search_get_node_variations(self):
        # Node with unicode and emoji in name
        self.store.update_from_node_dict({
            "num": 333333333,
            "user": {
                "id": "!13e4b555",
                "longName": "Base 📡 Station [Alpine-1]",
                "shortName": "ALPN",
            },
        })

        # 1. Exact ID
        self.assertEqual(self.store.get_node("!13e4b555").short_name, "ALPN")
        # 2. ID without !
        self.assertEqual(self.store.get_node("13e4b555").short_name, "ALPN")
        # 3. ID uppercase
        self.assertEqual(self.store.get_node("13E4B555").short_name, "ALPN")
        # 4. ID with 0x
        self.assertEqual(self.store.get_node("0x13e4b555").short_name, "ALPN")
        # 5. Partial ID suffix
        self.assertEqual(self.store.get_node("b555").short_name, "ALPN")
        # 6. Exact AKA lowercase/uppercase
        self.assertEqual(self.store.get_node("alpn").id, "!13e4b555")
        self.assertEqual(self.store.get_node("ALPN").id, "!13e4b555")
        # 7. Substring long name
        self.assertEqual(self.store.get_node("station").id, "!13e4b555")
        # 8. Emoji in query
        self.assertEqual(self.store.get_node("📡").id, "!13e4b555")
        # 9. Special punctuation characters
        self.assertEqual(self.store.get_node("[Alpine-1]").id, "!13e4b555")
        # 10. Decimal num
        self.assertEqual(self.store.get_node("333333333").id, "!13e4b555")
        # 11. Empty or None queries
        self.assertIsNone(self.store.get_node(""))
        self.assertIsNone(self.store.get_node("   "))
        self.assertIsNone(self.store.get_node(None))
        self.assertIsNone(self.store.get_node("non_existent_node_xyz"))

    def test_sorting_with_none_values(self):
        # Node with None SNR, None hops, None last_heard
        self.store.update_from_node_dict({
            "num": 10,
            "user": {"id": "!10", "longName": "Zeta Node", "shortName": "ZETA"},
            "snr": None,
            "hopsAway": None,
            "lastHeard": None,
        })
        # Node with positive SNR and hops
        self.store.update_from_node_dict({
            "num": 20,
            "user": {"id": "!20", "longName": "Alpha Node", "shortName": "ALPH"},
            "snr": 15.0,
            "hopsAway": 2,
            "lastHeard": datetime.now().timestamp(),
        })
        # Node with negative SNR and 0 hops
        self.store.update_from_node_dict({
            "num": 30,
            "user": {"id": "!30", "longName": "Beta Node", "shortName": "BETA"},
            "snr": -8.5,
            "hopsAway": 0,
            "lastHeard": (datetime.now() - timedelta(hours=1)).timestamp(),
        })

        # SNR sorting: highest first, None last
        by_snr = self.store.get_all_nodes(sort_by="snr")
        self.assertEqual(by_snr[0].short_name, "ALPH")  # 15.0
        self.assertEqual(by_snr[1].short_name, "MILA")  # 12.0
        self.assertEqual(by_snr[2].short_name, "BETA")  # -8.5
        self.assertEqual(by_snr[3].short_name, "ZETA")  # None

        # Hops sorting: lowest first, None last
        by_hops = self.store.get_all_nodes(sort_by="hops")
        self.assertEqual(by_hops[0].hops_away, 0)
        self.assertEqual(by_hops[1].hops_away, 0)
        self.assertEqual(by_hops[2].hops_away, 2)
        self.assertEqual(by_hops[3].hops_away, None)

        # Name sorting: alphabetical A->Z
        by_name = self.store.get_all_nodes(sort_by="name")
        self.assertEqual(by_name[0].short_name, "ALPH")
        self.assertEqual(by_name[1].short_name, "BETA")
        self.assertEqual(by_name[2].short_name, "MILA")
        self.assertEqual(by_name[3].short_name, "ZETA")

        # Last heard sorting: recent first, None last
        by_lh = self.store.get_all_nodes(sort_by="last_heard")
        self.assertEqual(by_lh[0].short_name, "ALPH")
        self.assertEqual(by_lh[-1].short_name, "ZETA")

    def test_active_only_filtering_with_timezones(self):
        now_utc = datetime.now(timezone.utc)
        # Active timezone-aware node
        self.store.update_from_node_dict({
            "num": 50,
            "user": {"id": "!50", "shortName": "ACTV"},
            "lastHeard": now_utc - timedelta(minutes=10),
        })
        # Stale node (3 hours old)
        self.store.update_from_node_dict({
            "num": 51,
            "user": {"id": "!51", "shortName": "STAL"},
            "lastHeard": now_utc - timedelta(hours=3),
        })

        active_nodes = self.store.get_all_nodes(active_only=True, active_threshold_seconds=3600)
        active_ids = [n.short_name for n in active_nodes]
        self.assertIn("MILA", active_ids)  # Local node is always included
        self.assertIn("ACTV", active_ids)  # Active within 1 hour
        self.assertNotIn("STAL", active_ids)  # Stale excluded

    def test_telemetry_and_position_complex_updates(self):
        # Complex environmental telemetry packet
        telem_pkt = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "rxSnr": 14.2,
            "hopStart": 3,
            "hopLimit": 2,
            "rxTime": int(datetime.now().timestamp()),
            "decoded": {
                "telemetry": {
                    "deviceMetrics": {
                        "batteryLevel": 92,
                        "voltage": 4.15,
                        "channelUtilization": 11.2,
                        "airUtilTx": 1.4,
                    },
                    "environmentMetrics": {
                        "temperature": 19.8,
                        "relativeHumidity": 62.5,
                        "barometricPressure": 1018.4,
                    },
                }
            },
        }
        updated = self.store.update_from_telemetry_packet(telem_pkt)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.battery_level, 92)
        self.assertEqual(updated.voltage, 4.15)
        self.assertEqual(updated.channel_util, 11.2)
        self.assertEqual(updated.air_util_tx, 1.4)
        self.assertEqual(updated.temperature, 19.8)
        self.assertEqual(updated.relative_humidity, 62.5)
        self.assertEqual(updated.barometric_pressure, 1018.4)
        self.assertEqual(updated.snr, 14.2)
        self.assertEqual(updated.hops_away, 1)

        # Position update with 0,0 GPS glitch should NOT overwrite valid coordinates
        glitch_pos_pkt = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "decoded": {
                "position": {
                    "latitude": 0.0,
                    "longitude": 0.0,
                }
            },
        }
        self.store.update_from_position_packet(glitch_pos_pkt)
        node = self.store.get_node("!45a466e4")
        # Should still have Milan coordinates!
        self.assertAlmostEqual(node.latitude, 45.4642)
        self.assertAlmostEqual(node.longitude, 9.1900)

        # Position update with locationSource, altitude, and valid coordinates
        valid_pos_pkt = {
            "from": 1168467684,
            "fromId": "!45a466e4",
            "decoded": {
                "position": {
                    "latitude": 45.4700,
                    "longitude": 9.2000,
                    "altitude": 135.0,
                    "locationSource": "LOC_MANUAL",
                    "precisionBits": 32,
                }
            },
        }
        self.store.update_from_position_packet(valid_pos_pkt)
        updated_pos_node = self.store.get_node("!45a466e4")
        self.assertAlmostEqual(updated_pos_node.latitude, 45.4700)
        self.assertAlmostEqual(updated_pos_node.longitude, 9.2000)
        self.assertEqual(updated_pos_node.altitude, 135.0)


class TestRadioClient(unittest.TestCase):
    """Test RadioClient pubsub routing, telemetry/position/DM parsing, and connection loss."""

    def test_radio_client_direct_and_broadcast_messages(self):
        store = NodeStore()
        # Add recipient in store
        store.update_from_node_dict({
            "num": 1168467684,
            "user": {"id": "!45a466e4", "longName": "Heltec Milan", "shortName": "MILA"},
        })
        client = RadioClient(node_store=store)

        messages = []
        client.on_message_received(lambda m: messages.append(m))

        # 1. Broadcast packet
        bc_pkt = {
            "from": 3103310553,
            "fromId": "!b8f862d9",
            "to": 0xFFFFFFFF,
            "toId": "^all",
            "channel": 0,
            "rxSnr": 11.0,
            "decoded": {"text": "General Announcement"},
        }
        client._on_pubsub_text(bc_pkt)
        self.assertEqual(len(messages), 1)
        self.assertFalse(messages[0].is_dm)
        self.assertEqual(messages[0].receiver_id, "^all")
        self.assertEqual(messages[0].text, "General Announcement")

        # 2. Direct message packet
        dm_pkt = {
            "from": 3103310553,
            "fromId": "!b8f862d9",
            "to": 1168467684,
            "toId": "!45a466e4",
            "channel": 0,
            "rxSnr": 8.0,
            "decoded": {"payload": b"Direct secret ping"},
        }
        client._on_pubsub_text(dm_pkt)
        self.assertEqual(len(messages), 2)
        self.assertTrue(messages[1].is_dm)
        self.assertEqual(messages[1].receiver_id, "!45a466e4")
        self.assertEqual(messages[1].recipient_name, "Heltec Milan")
        self.assertEqual(messages[1].text, "Direct secret ping")

    def test_radio_client_telemetry_and_position_routing(self):
        store = NodeStore()
        client = RadioClient(node_store=store)

        telemetry_events = []
        node_updates = []

        client.on_telemetry_received(lambda pkt, node: telemetry_events.append((pkt, node)))
        client.on_node_updated(lambda node: node_updates.append(node))

        # Telemetry packet with power and environmental data
        telem_pkt = {
            "from": 12345,
            "fromId": "!00003039",
            "decoded": {
                "telemetry": {
                    "deviceMetrics": {"batteryLevel": 75, "voltage": 3.95},
                    "environmentMetrics": {"temperature": 25.1, "relativeHumidity": 40.0},
                }
            },
        }
        client._on_pubsub_telemetry(telem_pkt)
        self.assertEqual(len(telemetry_events), 1)
        _, node = telemetry_events[0]
        self.assertEqual(node.battery_level, 75)
        self.assertEqual(node.temperature, 25.1)

        # Position packet
        pos_pkt = {
            "from": 12345,
            "fromId": "!00003039",
            "decoded": {
                "position": {
                    "latitudeI": 450000000,
                    "longitudeI": 90000000,
                    "altitude": 100,
                }
            },
        }
        client._on_pubsub_position(pos_pkt)
        self.assertGreaterEqual(len(node_updates), 1)
        self.assertAlmostEqual(node_updates[-1].latitude, 45.0)

    def test_radio_client_connection_lost_handling(self):
        client = RadioClient()
        mock_iface = MagicMock()
        client._interface = mock_iface
        client._port = "/dev/ttyACM0"
        client._is_connected = True

        connection_events = []
        client.on_connection_change(lambda connected, port: connection_events.append((connected, port)))

        # Trigger connection lost
        client._on_pubsub_connection_lost(interface=mock_iface)

        self.assertFalse(client.is_connected)
        self.assertIsNone(client.port)
        self.assertIsNone(client.interface)
        mock_iface.close.assert_called_once()
        self.assertEqual(connection_events, [(False, "/dev/ttyACM0")])

    def test_radio_client_crosstalk_protection(self):
        client = RadioClient()
        active_iface = MagicMock()
        client._interface = active_iface
        client._is_connected = True

        messages = []
        client.on_message_received(lambda m: messages.append(m))

        # Packet from an alien interface
        alien_iface = MagicMock()
        alien_pkt = {
            "from": 999,
            "decoded": {"text": "Alien crosstalk"},
        }
        client._on_pubsub_text(alien_pkt, interface=alien_iface)
        # Must be filtered out!
        self.assertEqual(len(messages), 0)

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

    def test_state_getters_when_disconnected_and_connected(self):
        client = RadioClient()
        self.assertIsNone(client.get_local_node())
        self.assertEqual(client.get_my_info()["is_connected"], False)
        self.assertEqual(client.get_channels(), [])


if __name__ == "__main__":
    unittest.main()
