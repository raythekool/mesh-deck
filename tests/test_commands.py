"""Unit tests for Mesh-Deck CommandDispatcher with comprehensive edge cases."""

from __future__ import annotations

import io
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from rich.console import Console

from mesh_deck.agent import AgentServiceError
from mesh_deck.__main__ import parse_args
from mesh_deck.cli import run_agent_command
from mesh_deck.commands.dispatcher import CommandDispatcher
from mesh_deck.core.events import DeviceConnectionInfo, NodeData
from mesh_deck.core.settings import Settings
from mesh_deck.ui.theme import DEFAULT_THEME, THEME_COLORS, THEMES, set_theme, theme_names


class TestCommandDispatcher(unittest.TestCase):
    """Test suite for command dispatching, execution, and robust error handling."""

    def setUp(self) -> None:
        # Keep /settings out of the real ~/.config/mesh-deck/settings.json.
        self._settings_tmp = TemporaryDirectory()
        self.addCleanup(self._settings_tmp.cleanup)
        config_dir = Path(self._settings_tmp.name)
        for target in ("CONFIG_DIR", "CONFIG_FILE"):
            patcher = patch(
                f"mesh_deck.core.settings.{target}",
                config_dir if target == "CONFIG_DIR" else config_dir / "settings.json",
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(set_theme, DEFAULT_THEME)

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
        self.settings = Settings()
        self.dispatcher = CommandDispatcher(self.mock_client, console=self.console, settings=self.settings)

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

    def test_dispatch_dm_refuses_an_unresolvable_target(self) -> None:
        """A raw name would reach meshtastic as a string and exit the process."""
        self.assertTrue(self.dispatcher.dispatch("/dm NodoCheNonEsiste ciao"))
        self.mock_client.send_dm.assert_not_called()

    def test_dispatch_dm_accepts_a_well_formed_id_not_yet_heard(self) -> None:
        self.assertTrue(self.dispatcher.dispatch("/dm !deadbeef ciao"))
        self.mock_client.send_dm.assert_called_with("!deadbeef", "ciao")

        self.mock_client.send_dm.reset_mock()
        self.assertTrue(self.dispatcher.dispatch("/dm DEADBEEF ciao"))
        self.mock_client.send_dm.assert_called_with("!deadbeef", "ciao")

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

    def test_dispatch_neighbors_empty_and_populated(self) -> None:
        from mesh_deck.core.events import NeighborLink, NeighborReport

        self.mock_client.get_neighbor_reports.return_value = []
        self.assertTrue(self.dispatcher.dispatch("/neighbors"))

        self.mock_client.get_neighbor_reports.return_value = [
            NeighborReport(
                node_id="!45a466e4",
                neighbors=[NeighborLink(node_id="!62d927b8", snr=6.5)],
                broadcast_interval_secs=900,
            )
        ]
        self.assertTrue(self.dispatcher.dispatch("/neighbors"))
        self.mock_client.get_neighbor_reports.assert_called()

    def test_dispatch_neighbors_for_one_node_resolves_the_alias(self) -> None:
        self.mock_client.get_neighbors_of.return_value = None
        self.assertTrue(self.dispatcher.dispatch("/neighbors TRIN"))
        self.mock_client.get_neighbors_of.assert_called_with("!62d927b8")

    def test_dispatch_mesh_summary(self) -> None:
        self.mock_client.get_neighbor_reports.return_value = []
        self.assertTrue(self.dispatcher.dispatch("/mesh"))
        self.mock_store.get_all_nodes.assert_called()

    def test_dispatch_topology_opens_internal_viewer_when_available(self) -> None:
        console = MagicMock()
        console.open_topology = MagicMock()
        dispatcher = CommandDispatcher(self.mock_client, console=console, settings=self.settings)

        self.assertTrue(dispatcher.dispatch("/topology"))
        console.open_topology.assert_called_once_with(self.mock_client, "it")

    def test_dispatch_topology_falls_back_to_mesh_summary(self) -> None:
        self.mock_client.get_neighbor_reports.return_value = []
        self.assertTrue(self.dispatcher.dispatch("/topology"))
        self.mock_store.get_all_nodes.assert_called()

    def test_dispatch_trace_requires_a_target(self) -> None:
        self.assertTrue(self.dispatcher.dispatch("/trace"))
        self.mock_client.trace_route.assert_not_called()

    def test_dispatch_trace_renders_the_hop_path(self) -> None:
        from mesh_deck.core.events import TraceRouteResult

        self.mock_client.trace_route.return_value = TraceRouteResult(
            target_id="!62d927b8",
            route_to=["!45a466e4"],
            snr_to=[6.25],
            route_back=["!45a466e4"],
        )
        self.assertTrue(self.dispatcher.dispatch("/trace TRIN"))
        self.mock_client.trace_route.assert_called_with("!62d927b8", cancel_event=None)

    def test_dispatch_trace_forwards_a_cancellation_event(self) -> None:
        cancel_event = threading.Event()
        self.mock_client.trace_route.return_value = None
        self.assertTrue(self.dispatcher.dispatch("/trace TRIN", cancel_event=cancel_event))
        self.mock_client.trace_route.assert_called_with("!62d927b8", cancel_event=cancel_event)

    def test_dispatch_trace_reports_a_timeout(self) -> None:
        self.mock_client.trace_route.return_value = None
        self.assertTrue(self.dispatcher.dispatch("/trace TRIN"))

    def test_dispatch_trace_survives_a_disconnected_radio(self) -> None:
        self.mock_client.trace_route.side_effect = ConnectionError("no radio")
        self.assertTrue(self.dispatcher.dispatch("/trace TRIN"))
        self.assertTrue(self.dispatcher.running)

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

    @unittest.mock.patch("mesh_deck.ui.channel_chat.launch_channel_chat")
    def test_dispatch_chat(self, mock_launch) -> None:
        res = self.dispatcher.dispatch("/chat")
        self.assertTrue(res)
        mock_launch.assert_called_once_with(self.mock_client, lang="it")

    def test_dispatch_logs_opens_internal_viewer_when_available(self) -> None:
        console = MagicMock()
        console.open_logs = MagicMock()
        dispatcher = CommandDispatcher(self.mock_client, console=console, settings=self.settings)

        self.assertTrue(dispatcher.dispatch("/logs"))
        console.open_logs.assert_called_once_with()

    def test_dispatch_logs_explains_text_only_fallback(self) -> None:
        self.assertTrue(self.dispatcher.dispatch("/logs"))

    def test_dispatch_settings_view(self) -> None:
        res = self.dispatcher.dispatch("/settings")
        self.assertTrue(res)

    def test_dispatch_settings_update(self) -> None:
        self.assertTrue(self.dispatcher.dispatch("/settings lang en"))
        self.assertTrue(self.dispatcher.dispatch("/settings lang it"))
        self.assertTrue(self.dispatcher.dispatch("/settings theme midnight"))
        self.assertTrue(self.dispatcher.dispatch("/settings theme cyberpunk"))
        self.assertTrue(self.dispatcher.dispatch("/settings sort snr"))
        self.assertTrue(self.dispatcher.dispatch("/settings port /dev/ttyACM0"))

    def test_dispatch_settings_theme_applies_palette(self) -> None:
        for name in theme_names():
            self.assertTrue(self.dispatcher.dispatch(f"/settings theme {name}"))
            self.assertEqual(Settings.load().theme, name)
            self.assertEqual(THEME_COLORS, THEMES[name])

    def test_dispatch_settings_theme_rejects_unknown(self) -> None:
        self.dispatcher.dispatch("/settings theme nord")
        self.assertTrue(self.dispatcher.dispatch("/settings theme not_a_theme"))
        # Rejected values must neither persist nor repaint.
        self.assertEqual(Settings.load().theme, "nord")

    def test_dispatch_settings_theme_notifies_console(self) -> None:
        console = MagicMock()
        dispatcher = CommandDispatcher(self.mock_client, console=console, settings=Settings())
        dispatcher.dispatch("/settings theme ember")
        console.apply_theme.assert_called_once_with("ember")

    def test_send_reports_radio_failure_instead_of_raising(self) -> None:
        self.mock_client.send_broadcast.side_effect = ConnectionError("radio unplugged")
        self.assertTrue(self.dispatcher.dispatch("/send hello"))

        self.mock_client.send_dm.side_effect = ConnectionError("radio unplugged")
        self.assertTrue(self.dispatcher.dispatch("/dm TRIN hello"))

    def test_dispatch_survives_a_library_sys_exit(self) -> None:
        """meshtastic-python exits the process on some failures; the TUI must not die."""
        self.mock_client.send_dm.side_effect = SystemExit(1)
        self.assertTrue(self.dispatcher.dispatch("/dm TRIN hello"))
        self.assertTrue(self.dispatcher.running)

        self.mock_client.get_channels.side_effect = SystemExit(1)
        self.assertTrue(self.dispatcher.dispatch("/channels"))
        self.assertTrue(self.dispatcher.running)

    def test_dispatch_reports_unexpected_handler_error(self) -> None:
        self.mock_client.get_channels.side_effect = RuntimeError("boom")
        self.assertTrue(self.dispatcher.dispatch("/channels"))
        self.assertTrue(self.dispatcher.running)

    def test_dispatch_settings_notifications_and_history_toggle(self) -> None:
        from mesh_deck.core.settings import Settings

        self.assertTrue(self.dispatcher.dispatch("/settings notifications off"))
        self.assertFalse(Settings.load().notifications_enabled)
        self.assertTrue(self.dispatcher.dispatch("/settings notifications on"))
        self.assertTrue(Settings.load().notifications_enabled)

        self.assertTrue(self.dispatcher.dispatch("/settings history off"))
        self.assertFalse(Settings.load().history_enabled)
        self.assertTrue(self.dispatcher.dispatch("/settings history on"))
        self.assertTrue(Settings.load().history_enabled)

    def test_dispatch_unknown_command(self) -> None:
        console = MagicMock()
        dispatcher = CommandDispatcher(self.mock_client, console=console)

        res = dispatcher.dispatch("/not_a_valid_command")
        self.assertTrue(res)
        console.print.assert_not_called()

    def test_dispatch_restart(self) -> None:
        console = MagicMock()
        dispatcher = CommandDispatcher(self.mock_client, console=console)

        self.assertTrue(dispatcher.dispatch("/restart"))
        console.restart_console.assert_called_once()

    def test_dispatch_empty_input(self) -> None:
        self.assertTrue(self.dispatcher.dispatch(""))
        self.assertTrue(self.dispatcher.dispatch("   "))
        self.assertTrue(self.dispatcher.dispatch("\t\n"))

    def test_dispatch_quit(self) -> None:
        res = self.dispatcher.dispatch("/quit")
        self.assertFalse(res)
        self.assertFalse(self.dispatcher.running)
        self.mock_client.disconnect.assert_called()


class TestAgentCLI(unittest.TestCase):
    """Test stable CLI parsing, envelopes, and exit codes."""

    def setUp(self):
        self.service = MagicMock()
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.stdout = Console(
            file=self.stdout_buffer,
            force_terminal=False,
            color_system=None,
        )
        self.stderr = Console(
            file=self.stderr_buffer,
            force_terminal=False,
            color_system=None,
        )

    def test_nodes_json_envelope(self):
        self.service.list_nodes.return_value = {
            "nodes": [{"id": "!1"}],
            "count": 1,
            "sort": "snr",
            "active_only": True,
        }
        args = parse_args(
            ["nodes", "--sort", "snr", "--active", "--output", "json"]
        )

        exit_code = run_agent_command(
            args,
            service=self.service,
            stdout=self.stdout,
            stderr=self.stderr,
        )

        payload = json.loads(self.stdout_buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "nodes")
        self.assertEqual(payload["data"]["count"], 1)
        self.assertNotIn("\x1b", self.stdout_buffer.getvalue())
        self.service.list_nodes.assert_called_once_with(
            port=None,
            timeout=30,
            sort_by="snr",
            active_only=True,
        )

    def test_json_error_uses_stable_exit_code(self):
        self.service.get_node.side_effect = AgentServiceError(
            "node_not_found",
            "No matching node.",
            exit_code=3,
            details={"query": "missing"},
        )
        args = parse_args(["node", "missing", "--output", "json"])

        exit_code = run_agent_command(
            args,
            service=self.service,
            stdout=self.stdout,
            stderr=self.stderr,
        )

        payload = json.loads(self.stdout_buffer.getvalue())
        self.assertEqual(exit_code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "node_not_found")
        self.assertEqual(self.stderr_buffer.getvalue(), "")

    def test_help_survives_a_legacy_codepage_stdout(self) -> None:
        """--help must not die on the emoji when stdout is not UTF-8 (Windows)."""
        from mesh_deck.__main__ import _force_utf8_stdio, main

        # A byte stream whose text layer cannot encode the emoji, like a
        # Windows console defaulting to cp1252.
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", write_through=True)
        with patch("sys.stdout", stream), patch("sys.stderr", stream):
            _force_utf8_stdio()
            with self.assertRaises(SystemExit) as exit_info:
                main(["--help"])
        self.assertEqual(exit_info.exception.code, 0)
        stream.flush()
        rendered = raw.getvalue().decode("utf-8", errors="replace")
        self.assertIn("mesh-deck", rendered)
        self.assertIn("neighbors", rendered)
        self.assertIn("trace", rendered)

    def test_force_utf8_stdio_ignores_streams_without_reconfigure(self) -> None:
        from mesh_deck.__main__ import _force_utf8_stdio

        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            _force_utf8_stdio()  # must not raise

    def test_send_is_preview_without_confirm(self):
        self.service.send_broadcast.return_value = {
            "sent": False,
            "preview": True,
            "operation": "broadcast",
            "text": "hello",
            "channel_index": 0,
        }
        args = parse_args(["send", "hello", "--output", "json"])

        self.assertEqual(
            run_agent_command(args, service=self.service, stdout=self.stdout),
            0,
        )
        self.service.send_broadcast.assert_called_once_with(
            "hello",
            channel_index=0,
            confirm=False,
            port=None,
            timeout=30,
        )

    def test_legacy_flags_still_parse(self):
        args = parse_args(["--port", "/dev/ttyACM1", "--nodes"])
        self.assertIsNone(args.command)
        self.assertTrue(args.nodes)
        self.assertEqual(args.port, "/dev/ttyACM1")

    def test_port_before_subcommand_is_not_silently_dropped(self):
        """Regression test: argparse subparsers overwrite a shared `dest` with
        their own default unless subcommand connection args use distinct
        attributes. `--port` given before the subcommand must still resolve.
        """
        from mesh_deck.cli import resolve_connection_args

        before = parse_args(["--port", "/dev/ttyACM0", "nodes"])
        self.assertEqual(resolve_connection_args(before), ("/dev/ttyACM0", 30))

        after = parse_args(["nodes", "--port", "/dev/ttyACM9"])
        self.assertEqual(resolve_connection_args(after), ("/dev/ttyACM9", 30))

        # When both are given, the subcommand-local value wins.
        both = parse_args(
            ["--port", "/dev/ttyACM0", "nodes", "--port", "/dev/ttyACM9"]
        )
        self.assertEqual(resolve_connection_args(both), ("/dev/ttyACM9", 30))

    def test_mcp_command_resolves_port_given_before_subcommand(self):
        from mesh_deck.cli import resolve_connection_args

        args = parse_args(["--port", "/dev/ttyACM7", "mcp"])
        self.assertEqual(resolve_connection_args(args), ("/dev/ttyACM7", 30))


class TestMCPServer(unittest.IsolatedAsyncioTestCase):
    """Test MCP tool registration and non-mutating send defaults."""

    async def test_tools_are_registered_and_send_defaults_to_preview(self):
        from mesh_deck.mcp_server import create_server

        service = MagicMock()
        service.send_broadcast.return_value = {
            "sent": False,
            "preview": True,
        }
        server = create_server(service, default_port="/dev/ttyACM0")

        names = {tool.name for tool in await server.list_tools()}
        self.assertEqual(
            names,
            {
                "scan_devices",
                "get_radio_info",
                "list_nodes",
                "get_node",
                "list_channels",
                "list_neighbors",
                "trace_route",
                "send_broadcast",
                "send_direct_message",
            },
        )
        await server.call_tool("send_broadcast", {"text": "hello"})
        service.send_broadcast.assert_called_once_with(
            "hello",
            channel_index=0,
            confirm=False,
            port="/dev/ttyACM0",
            timeout=30,
        )

    async def test_expected_service_failure_is_an_mcp_tool_error(self):
        from mesh_deck.mcp_server import create_server
        from mcp.server.mcpserver.exceptions import ToolError

        service = MagicMock()
        service.get_node.side_effect = AgentServiceError(
            "node_not_found",
            "No matching node.",
            exit_code=3,
        )
        server = create_server(service)

        with self.assertRaises(ToolError) as context:
            await server.call_tool("get_node", {"query": "missing"})

        self.assertIn("node_not_found", str(context.exception))


if __name__ == "__main__":
    unittest.main()
