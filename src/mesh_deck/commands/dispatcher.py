"""Command dispatcher for Mesh-Deck CLI/TUI."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.core.settings import Settings
from mesh_deck.i18n import t
from mesh_deck.ui.banner import render_banner
from mesh_deck.ui.tables import render_message, render_node_detail, render_nodes_table
from mesh_deck.ui.theme import THEME_COLORS

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient


class CommandDispatcher:
    """Dispatches user slash commands to their corresponding handlers."""

    def __init__(
        self,
        radio_client: RadioClient,
        console: Console | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.client = radio_client
        self.console = console or Console()
        self.settings = settings if settings is not None else Settings.load()
        self.running = True

        self._commands: dict[str, Callable[[list[str]], None]] = {
            "/help": self.cmd_help,
            "/?": self.cmd_help,
            "/nodes": self.cmd_nodes,
            "/node": self.cmd_node,
            "/send": self.cmd_send,
            "/dm": self.cmd_dm,
            "/channels": self.cmd_channels,
            "/info": self.cmd_info,
            "/view": self.cmd_view,
            "/tui": self.cmd_view,
            "/chat": self.cmd_chat,
            "/settings": self.cmd_settings,
            "/config": self.cmd_settings,
            "/switch": self.cmd_switch,
            "/scan": self.cmd_scan,
            "/clear": self.cmd_clear,
            "/restart": self.cmd_restart,
            "/banner": self.cmd_banner,
            "/quit": self.cmd_quit,
            "/exit": self.cmd_quit,
            "/q": self.cmd_quit,
        }

    @property
    def lang(self) -> str:
        """Current UI language, read live from the shared Settings instance."""
        return self.settings.language

    def dispatch(self, raw_input: str) -> bool:
        """Parse and execute a command string.

        Returns:
            True to continue REPL, False to quit.
        """
        line = raw_input.strip()
        if not line:
            return True

        # Check if line is a slash command
        if line.startswith("/"):
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            handler = self._commands.get(cmd)
            if handler:
                try:
                    args = shlex.split(rest)
                except ValueError:
                    args = rest.split()
                handler(args)
        else:
            # Plain text input defaults to broadcasting on channel 0
            self.cmd_send([line])

        return self.running

    def cmd_help(self, args: list[str]) -> None:
        """Display available commands."""
        lang = self.lang
        table = Table(
            title=t("HELP_TITLE", lang),
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=True,
            header_style=f"bold {THEME_COLORS['primary']}",
        )
        table.add_column(t("COL_COMMAND", lang), style="bold white", width=22)
        table.add_column(t("COL_ARGS", lang), style="dim cyan", width=22)
        table.add_column(t("COL_DESCRIPTION", lang), style="white")

        commands_info = [
            ("/nodes", "[active|snr|hops|name]", t("CMD_DESC_NODES", lang)),
            ("/view, /tui", "", t("CMD_DESC_VIEW", lang)),
            ("/chat", "", t("CMD_DESC_CHAT", lang)),
            ("/node", "<id|aka>", t("CMD_DESC_NODE", lang)),
            ("/send", "<testo>", t("CMD_DESC_SEND", lang)),
            ("/dm", "<id|aka> <testo>", t("CMD_DESC_DM", lang)),
            ("/channels", "", t("CMD_DESC_CHANNELS", lang)),
            ("/info", "", t("CMD_DESC_INFO", lang)),
            ("/settings", "[lang|theme|sort|port|notifications|history]", t("CMD_DESC_SETTINGS", lang)),
            ("/switch", "[porta|indice]", t("CMD_DESC_SWITCH", lang)),
            ("/scan", "", t("CMD_DESC_SCAN", lang)),
            ("/banner", "", t("CMD_DESC_BANNER", lang)),
            ("/clear", "", t("CMD_DESC_CLEAR", lang)),
            ("/restart", "", t("CMD_DESC_RESTART", lang)),
            ("/quit, /exit", "", t("CMD_DESC_QUIT", lang)),
        ]

        for cmd, arg, desc in commands_info:
            table.add_row(cmd, arg, desc)

        self.console.print(table)

    def cmd_nodes(self, args: list[str]) -> None:
        """Display the list of nodes in the mesh."""
        lang = self.lang
        sort_by = "last_heard"
        active_only = False

        if args:
            arg = args[0].lower()
            if arg in ("active", "attivi"):
                active_only = True
            elif arg in ("snr", "hops", "name", "last_heard"):
                sort_by = arg
            else:
                self.console.print(f"[{THEME_COLORS['warning']}]{t('WARN_INVALID_SORT', lang, opt=arg)}[/]")

        nodes = self.client.store.get_all_nodes(sort_by=sort_by, active_only=active_only)
        local_node = self.client.get_local_node()
        local_id = local_node.id if local_node else None

        if not nodes:
            self.console.print(f"[{THEME_COLORS['muted']}]{t('NODES_EMPTY', lang)}[/]")
            return

        table = render_nodes_table(nodes, local_node_id=local_id, lang=lang)
        self.console.print(table)
        cmd_colored = f"[{THEME_COLORS['primary']}]/view[/{THEME_COLORS['primary']}]"
        self.console.print(f"[dim]{t('NODES_HINT', lang, cmd=cmd_colored)}[/dim]\n")

    def cmd_node(self, args: list[str]) -> None:
        """Show detail panel for a specific node."""
        lang = self.lang
        if not args:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('USAGE_NODE', lang)}[/]")
            return

        query = args[0]
        node = self.client.store.get_node(query)
        if not node:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('NODE_NOT_FOUND', lang, query=query)}[/]")
            return

        local_node = self.client.get_local_node()
        dist_km = None
        if local_node and local_node.id != node.id:
            dist_km = self.client.store.calculate_distance(local_node.id, node.id)

        panel = render_node_detail(node, distance_km=dist_km, lang=lang)
        self.console.print(panel)

    def cmd_send(self, args: list[str]) -> None:
        """Send a broadcast message."""
        lang = self.lang
        text = " ".join(args).strip()
        if not text:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('USAGE_SEND', lang)}[/]")
            return

        success = self.client.send_broadcast(text)
        if success:
            self.console.print(
                f"[{THEME_COLORS['secondary']}]{t('SEND_SUCCESS', lang, text=text)}[/]"
            )
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('SEND_ERROR', lang)}[/]")

    def cmd_dm(self, args: list[str]) -> None:
        """Send a direct message."""
        lang = self.lang
        if len(args) < 2:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('USAGE_DM', lang)}[/]")
            return

        target_query = args[0]
        text = " ".join(args[1:]).strip()

        # Resolve target query to node
        target_node = self.client.store.get_node(target_query)
        target_id = target_node.id if target_node else target_query

        success = self.client.send_dm(target_id, text)
        target_name = target_node.display_name if target_node else target_id
        if success:
            self.console.print(
                f"[{THEME_COLORS['magenta']}]{t('DM_SUCCESS', lang, name=target_name, text=text)}[/]"
            )
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('DM_ERROR', lang, name=target_name)}[/]")

    def cmd_channels(self, args: list[str]) -> None:
        """Display configured channels."""
        lang = self.lang
        channels = self.client.get_channels()
        if not channels:
            self.console.print(f"[{THEME_COLORS['muted']}]{t('CHANNELS_EMPTY', lang)}[/]")
            return

        table = Table(
            title=t("CHANNELS_TABLE_TITLE", lang),
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=True,
            header_style=f"bold {THEME_COLORS['accent']}",
        )
        table.add_column(t("COL_CH_INDEX", lang), justify="center", width=8)
        table.add_column(t("COL_CH_NAME", lang), style="bold white", width=20)
        table.add_column(t("COL_CH_ROLE", lang), width=14)
        table.add_column(t("COL_CH_UPDOWN", lang), width=18)
        table.add_column(t("COL_CH_PSK", lang), width=18)

        for ch in channels:
            idx = str(ch.get("index", "?"))
            name = ch.get("name") or t("CH_PRIMARY_DEFAULT", lang)
            role = ch.get("role", "PRIMARY" if idx == "0" else "SECONDARY")
            up = "✓" if ch.get("uplink_enabled") else "✗"
            down = "✓" if ch.get("downlink_enabled") else "✗"
            psk_set = f"[green]{t('PSK_ACTIVE', lang)}[/green]" if ch.get("has_psk") else f"[dim]{t('PSK_DEFAULT', lang)}[/dim]"
            table.add_row(idx, name, role, f"Up: {up} | Down: {down}", psk_set)

        self.console.print(table)

    def cmd_info(self, args: list[str]) -> None:
        """Display radio and system info."""
        lang = self.lang
        info = self.client.get_my_info()
        local = self.client.get_local_node()
        if not info and not local:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('INFO_EMPTY', lang)}[/]")
            return

        table = Table(
            title=t("INFO_TABLE_TITLE", lang),
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=False,
        )
        table.add_column(t("COL_PARAM", lang), style=f"bold {THEME_COLORS['secondary']}", width=25)
        table.add_column(t("COL_VALUE", lang), style="white")

        table.add_row(t("ROW_SERIAL_PORT", lang), self.client.port or "N/A")
        table.add_row(
            t("ROW_CONN_STATUS", lang),
            f"[green]{t('CONN_CONNECTED', lang)}[/green]" if self.client.is_connected else f"[red]{t('CONN_DISCONNECTED', lang)}[/red]",
        )
        if local:
            table.add_row(t("ROW_LOCAL_NODE", lang), f"{local.display_name} ({local.id})")
            table.add_row(t("ROW_HW_MODEL", lang), local.hw_model)
            table.add_row(t("ROW_ROLE", lang), local.role)
            if local.has_position:
                table.add_row(t("ROW_GPS", lang), local.coords_str)
        if info:
            table.add_row(t("ROW_RF_REGION", lang), info.get("region", "EU_868"))
            table.add_row(t("ROW_MODEM_PRESET", lang), info.get("modem_preset", "MEDIUM_FAST"))
            table.add_row(t("ROW_FIRMWARE", lang), info.get("firmware_version", "N/A"))
            table.add_row(t("ROW_ACTIVE_CHANNELS", lang), str(len(self.client.get_channels())))

        self.console.print(table)

    def cmd_scan(self, args: list[str]) -> None:
        """Scan and display detected USB serial ports."""
        lang = self.lang
        ports = scan_meshtastic_ports()
        if not ports:
            self.console.print(f"[{THEME_COLORS['warning']}]{t('SCAN_EMPTY', lang)}[/]")
            return

        table = Table(
            title=t("SCAN_TABLE_TITLE", lang),
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
        )
        table.add_column("#", justify="center", width=4)
        table.add_column(t("COL_PORT", lang), style="bold cyan", width=16)
        table.add_column(t("COL_HW_DETECTED", lang), style="bold white", width=28)
        table.add_column(t("COL_SYS_DESC", lang), style="dim white")
        table.add_column(t("COL_CURRENT_STATUS", lang), justify="center", width=14)

        for i, p in enumerate(ports, start=1):
            is_cur = p.port == self.client.port
            status = f"[green]{t('STATUS_ACTIVE', lang)}[/green]" if is_cur else f"[dim]{t('STATUS_AVAILABLE', lang)}[/dim]"
            table.add_row(str(i), p.port, p.hw_name, p.description, status)

        self.console.print(table)

    def cmd_switch(self, args: list[str]) -> None:
        """Switch connection to another serial port."""
        lang = self.lang
        ports = scan_meshtastic_ports()
        if not ports:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('SWITCH_EMPTY', lang)}[/]")
            return

        target_port: str | None = None

        if not args:
            # If no arg given, find the other port
            for p in ports:
                if p.port != self.client.port:
                    target_port = p.port
                    break
            if not target_port:
                self.console.print(f"[{THEME_COLORS['warning']}]{t('SWITCH_NO_ALT', lang)}[/]")
                return
        else:
            arg = args[0]
            # Check if arg is an index (1-based)
            if arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(ports):
                    target_port = ports[idx].port
                else:
                    self.console.print(f"[{THEME_COLORS['alert']}]{t('SWITCH_INVALID_INDEX', lang, max=len(ports))}[/]")
                    return
            else:
                target_port = arg

        self.console.print(f"[{THEME_COLORS['accent']}]{t('SWITCH_IN_PROGRESS', lang, port=target_port)}[/]")
        success = self.client.connect(target_port, blocking=True)
        if success:
            local = self.client.get_local_node()
            name = local.display_name if local else t("NODE_UNKNOWN_NAME", lang)
            self.console.print(f"[{THEME_COLORS['secondary']}]{t('SWITCH_SUCCESS', lang, port=target_port, name=name)}[/]")
            self.cmd_banner([])
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]{t('SWITCH_FAILURE', lang, port=target_port)}[/]")

    def cmd_banner(self, args: list[str]) -> None:
        """Render status banner."""
        local = self.client.get_local_node()
        channels = self.client.get_channels()
        banner = render_banner(
            local_node=local,
            port=self.client.port or "N/A",
            channel_util=local.channel_util if local else None,
            channels=channels,
            lang=self.lang,
        )
        self.console.print(banner)

    def cmd_view(self, args: list[str]) -> None:
        """Launch interactive full-screen table with mouse-click column sorting."""
        lang = self.lang
        local_node = self.client.get_local_node()
        opener = getattr(self.console, "open_node_explorer", None)
        if callable(opener):
            opener(self.client.store, local_node, lang)
            return

        from mesh_deck.ui.interactive_table import launch_interactive_nodes
        self.console.print(f"[{THEME_COLORS['primary']}]{t('VIEW_LAUNCH', lang)}[/]")
        launch_interactive_nodes(self.client.store, local_node=local_node, lang=lang)

    def cmd_chat(self, args: list[str]) -> None:
        """Launch interactive mouse-usable chat viewer for channels and DMs."""
        lang = self.lang
        opener = getattr(self.console, "open_channel_chat", None)
        if callable(opener):
            opener(self.client, lang)
            return

        from mesh_deck.ui.channel_chat import launch_channel_chat
        self.console.print(f"[{THEME_COLORS['primary']}]{t('CHAT_LAUNCH', lang)}[/]")
        launch_channel_chat(self.client, lang=lang)

    def cmd_settings(self, args: list[str]) -> None:
        """View or update user preferences (language, theme, port, sort)."""
        settings = self.settings
        lang = settings.language

        if not args:
            opener = getattr(self.console, "open_settings", None)
            if callable(opener):
                opener()
                return
            table = Table(
                title=t("SETTINGS_TITLE", lang),
                title_style=f"bold {THEME_COLORS['primary']}",
                border_style=THEME_COLORS["border"],
                show_header=True,
                header_style=f"bold {THEME_COLORS['primary']}",
            )
            table.add_column(t("SETTING_KEY", lang), style="bold white", width=24)
            table.add_column(t("SETTING_VAL", lang), style="bold green", width=18)
            table.add_column(t("SETTING_OPTS", lang), style="dim cyan")

            table.add_row(t("SETTINGS_ROW_LANG", lang), settings.language, "/settings lang <it|en>")
            table.add_row(t("SETTINGS_ROW_THEME", lang), settings.theme, "/settings theme <cyberpunk|high_contrast|amber|matrix>")
            table.add_row(
                t("SETTINGS_ROW_PORT", lang),
                settings.default_port or t("SETTINGS_AUTODETECT", lang),
                "/settings port </dev/tty...>",
            )
            table.add_row(t("SETTINGS_ROW_SORT", lang), settings.default_sort, "/settings sort <last_heard|snr|hops|name>")
            table.add_row(t("SETTINGS_ROW_MODE", lang), settings.ui_mode, "/settings mode <repl|tui>")
            table.add_row(
                t("SETTINGS_NOTIFICATIONS", lang),
                t("SETTINGS_ON", lang) if settings.notifications_enabled else t("SETTINGS_OFF", lang),
                "/settings notifications <on|off>",
            )
            table.add_row(
                t("SETTINGS_HISTORY", lang),
                t("STATE_ON", lang) if settings.history_enabled else t("STATE_OFF", lang),
                "/settings history <on|off>",
            )

            self.console.print(table)
            return

        sub = args[0].lower()
        if sub in ("lang", "lingua") and len(args) > 1:
            lang_val = args[1].lower()
            if lang_val in ("it", "en"):
                settings.update(language=lang_val)
                updater = getattr(self.console, "update_language", None)
                if callable(updater):
                    updater(lang_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_LANG_SET', lang_val, value=lang_val.upper())}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_LANG_INVALID', lang)}[/]")
        elif sub in ("theme", "tema") and len(args) > 1:
            theme_val = args[1].lower()
            if theme_val in ("cyberpunk", "high_contrast", "amber", "matrix"):
                settings.update(theme=theme_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_THEME_SET', lang, theme=theme_val)}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_THEME_INVALID', lang)}[/]")
        elif sub in ("sort", "ordinamento") and len(args) > 1:
            sort_val = args[1].lower()
            if sort_val in ("last_heard", "snr", "hops", "name"):
                settings.update(default_sort=sort_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_SORT_SET', lang, sort=sort_val)}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_SORT_INVALID', lang)}[/]")
        elif sub in ("port", "porta") and len(args) > 1:
            port_val = args[1]
            settings.update(default_port=port_val)
            self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_PORT_SET', lang, port=port_val)}[/]")
        elif sub in ("mode", "modalita") and len(args) > 1:
            mode_val = args[1].lower()
            if mode_val in ("repl", "tui"):
                settings.update(ui_mode=mode_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_MODE_SET', lang, mode=mode_val)}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_MODE_INVALID', lang)}[/]")
        elif sub in ("notifications", "notifiche") and len(args) > 1:
            val = args[1].lower()
            if val in ("on", "off"):
                settings.update(notifications_enabled=(val == "on"))
                state = t("STATE_ENABLED_F", lang) if val == "on" else t("STATE_DISABLED_F", lang)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_NOTIF_SET', lang, state=state)}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_INVALID_VALUE', lang)}[/]")
        elif sub in ("history", "storico") and len(args) > 1:
            val = args[1].lower()
            if val in ("on", "off"):
                settings.update(history_enabled=(val == "on"))
                state = t("STATE_ENABLED_M", lang) if val == "on" else t("STATE_DISABLED_M", lang)
                self.console.print(f"[{THEME_COLORS['secondary']}]{t('SETTINGS_HISTORY_SET', lang, state=state)}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]{t('SETTINGS_INVALID_VALUE', lang)}[/]")
        else:
            self.console.print(f"[{THEME_COLORS['warning']}]{t('SETTINGS_USAGE', lang)}[/]")

    def cmd_clear(self, args: list[str]) -> None:
        """Clear terminal screen."""
        self.console.clear()

    def cmd_restart(self, args: list[str]) -> None:
        """Reload console settings without disconnecting the active radio."""
        restarter = getattr(self.console, "restart_console", None)
        if callable(restarter):
            restarter()

    def cmd_quit(self, args: list[str]) -> None:
        """Exit Mesh-Deck."""
        self.console.print(f"[{THEME_COLORS['primary']}]{t('QUIT_MESSAGE', self.lang)}[/]")
        self.running = False
        self.client.disconnect()
