"""Command dispatcher for Mesh-Deck CLI/TUI."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.ui.banner import render_banner
from mesh_deck.ui.tables import render_message, render_node_detail, render_nodes_table
from mesh_deck.ui.theme import THEME_COLORS

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient


class CommandDispatcher:
    """Dispatches user slash commands to their corresponding handlers."""

    def __init__(self, radio_client: RadioClient, console: Console | None = None) -> None:
        self.client = radio_client
        self.console = console or Console()
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
        table = Table(
            title="⚡ MESH-DECK // COMANDI DISPONIBILI",
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=True,
            header_style=f"bold {THEME_COLORS['primary']}",
        )
        table.add_column("Comando", style="bold white", width=22)
        table.add_column("Argomenti", style="dim cyan", width=22)
        table.add_column("Descrizione", style="white")

        commands_info = [
            ("/nodes", "[active|snr|hops|name]", "Elenca i nodi visibili nella mesh con telemetria"),
            ("/view, /tui", "", "Tabella interattiva a schermo intero con click su header per ordinare"),
            ("/node", "<id|aka>", "Visualizza la scheda analitica dettagliata di un nodo"),
            ("/send", "<testo>", "Invia un messaggio broadcast sul canale primario (anche solo digitando il testo)"),
            ("/dm", "<id|aka> <testo>", "Invia un messaggio diretto privato a un nodo"),
            ("/channels", "", "Mostra l'elenco dei canali radio configurati"),
            ("/info", "", "Visualizza lo stato della radio, frequenze, modem e preset"),
            ("/settings", "[lang|theme|sort|port]", "Visualizza o modifica le impostazioni (lingua it/en, tema, porta)"),
            ("/switch", "[porta|indice]", "Passa a un altro dispositivo LoRa USB connesso"),
            ("/scan", "", "Rileva e mostra tutte le radio LoRa USB collegate al PC"),
            ("/banner", "", "Ristampa il banner di stato Hermes"),
            ("/clear", "", "Pulisce la schermata del terminale"),
            ("/restart", "", "Ricarica impostazioni e aggiorna la console"),
            ("/quit, /exit", "", "Chiude l'applicazione"),
        ]

        for cmd, arg, desc in commands_info:
            table.add_row(cmd, arg, desc)

        self.console.print(table)

    def cmd_nodes(self, args: list[str]) -> None:
        """Display the list of nodes in the mesh."""
        sort_by = "last_heard"
        active_only = False

        if args:
            arg = args[0].lower()
            if arg in ("active", "attivi"):
                active_only = True
            elif arg in ("snr", "hops", "name", "last_heard"):
                sort_by = arg
            else:
                self.console.print(f"[{THEME_COLORS['warning']}]Opzione non valida:[/] {arg}. Uso sort predefinito: last_heard.")

        nodes = self.client.store.get_all_nodes(sort_by=sort_by, active_only=active_only)
        local_node = self.client.get_local_node()
        local_id = local_node.id if local_node else None

        if not nodes:
            self.console.print(f"[{THEME_COLORS['muted']}]Nessun nodo trovato nel NodeDB corrente.[/]")
            return

        table = render_nodes_table(nodes, local_node_id=local_id)
        self.console.print(table)
        self.console.print(
            f"[dim]💡 Suggerimento: usa [{THEME_COLORS['primary']}]/view[/dim] "
            f"[dim]per aprire la tabella interattiva con ordinamento al click del mouse su ogni colonna.[/dim]\n"
        )

    def cmd_node(self, args: list[str]) -> None:
        """Show detail panel for a specific node."""
        if not args:
            self.console.print(f"[{THEME_COLORS['alert']}]Uso:[/] /node <id|aka|nome>")
            return

        query = args[0]
        node = self.client.store.get_node(query)
        if not node:
            self.console.print(f"[{THEME_COLORS['alert']}]Nodo non trovato:[/] {query}")
            return

        local_node = self.client.get_local_node()
        dist_km = None
        if local_node and local_node.id != node.id:
            dist_km = self.client.store.calculate_distance(local_node.id, node.id)

        panel = render_node_detail(node, distance_km=dist_km)
        self.console.print(panel)

    def cmd_send(self, args: list[str]) -> None:
        """Send a broadcast message."""
        text = " ".join(args).strip()
        if not text:
            self.console.print(f"[{THEME_COLORS['alert']}]Uso:[/] /send <testo del messaggio>")
            return

        success = self.client.send_broadcast(text)
        if success:
            local = self.client.get_local_node()
            self.console.print(
                f"[{THEME_COLORS['secondary']}]📢 [bold]Inviato (Broadcast #0):[/] {text}[/]"
            )
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]Errore durante l'invio del messaggio broadcast.[/]")

    def cmd_dm(self, args: list[str]) -> None:
        """Send a direct message."""
        if len(args) < 2:
            self.console.print(f"[{THEME_COLORS['alert']}]Uso:[/] /dm <target_id_o_aka> <testo>")
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
                f"[{THEME_COLORS['magenta']}]🔒 [bold]DM inviato a {target_name}:[/] {text}[/]"
            )
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]Errore durante l'invio del DM a {target_name}.[/]")

    def cmd_channels(self, args: list[str]) -> None:
        """Display configured channels."""
        channels = self.client.get_channels()
        if not channels:
            self.console.print(f"[{THEME_COLORS['muted']}]Nessun canale disponibile o radio non connessa.[/]")
            return

        table = Table(
            title="📡 CANALI RADIO CONFIGURATI",
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=True,
            header_style=f"bold {THEME_COLORS['accent']}",
        )
        table.add_column("Index", justify="center", width=8)
        table.add_column("Nome Canale", style="bold white", width=20)
        table.add_column("Ruolo / Tipo", width=14)
        table.add_column("Uplink / Downlink", width=18)
        table.add_column("Crittografia (PSK)", width=18)

        for ch in channels:
            idx = str(ch.get("index", "?"))
            name = ch.get("name") or "(Primary)"
            role = ch.get("role", "PRIMARY" if idx == "0" else "SECONDARY")
            up = "✓" if ch.get("uplink_enabled") else "✗"
            down = "✓" if ch.get("downlink_enabled") else "✗"
            psk_set = "[green]Attiva[/green]" if ch.get("has_psk") else "[dim]Predefinita[/dim]"
            table.add_row(idx, name, role, f"Up: {up} | Down: {down}", psk_set)

        self.console.print(table)

    def cmd_info(self, args: list[str]) -> None:
        """Display radio and system info."""
        info = self.client.get_my_info()
        local = self.client.get_local_node()
        if not info and not local:
            self.console.print(f"[{THEME_COLORS['alert']}]Nessuna informazione radio disponibile.[/]")
            return

        table = Table(
            title="📻 STATO HARDWARE & PARAMETRI RADIO",
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
            show_header=False,
        )
        table.add_column("Parametro", style=f"bold {THEME_COLORS['secondary']}", width=25)
        table.add_column("Valore", style="white")

        table.add_row("Porta Seriale", self.client.port or "N/A")
        table.add_row("Stato Connessione", "[green]Connesso[/green]" if self.client.is_connected else "[red]Disconnesso[/red]")
        if local:
            table.add_row("Nodo Locale", f"{local.display_name} ({local.id})")
            table.add_row("Modello Hardware", local.hw_model)
            table.add_row("Ruolo", local.role)
            if local.has_position:
                table.add_row("Coordinate GPS", local.coords_str)
        if info:
            table.add_row("Regione RF", info.get("region", "EU_868"))
            table.add_row("Modem Preset", info.get("modem_preset", "MEDIUM_FAST"))
            table.add_row("Firmware Version", info.get("firmware_version", "N/A"))
            table.add_row("Canali Attivi", str(len(self.client.get_channels())))

        self.console.print(table)

    def cmd_scan(self, args: list[str]) -> None:
        """Scan and display detected USB serial ports."""
        ports = scan_meshtastic_ports()
        if not ports:
            self.console.print(f"[{THEME_COLORS['warning']}]Nessun dispositivo LoRa rilevato sulle porte USB.[/]")
            return

        table = Table(
            title="🔍 DISPOSITIVI LORA / MESHTASTIC RILEVATI",
            title_style=f"bold {THEME_COLORS['primary']}",
            border_style=THEME_COLORS["border"],
        )
        table.add_column("#", justify="center", width=4)
        table.add_column("Porta", style="bold cyan", width=16)
        table.add_column("Hardware Rilevato", style="bold white", width=28)
        table.add_column("Descrizione Sistema", style="dim white")
        table.add_column("Stato Attuale", justify="center", width=14)

        for i, p in enumerate(ports, start=1):
            is_cur = p.port == self.client.port
            status = "[green]★ ATTIVO[/green]" if is_cur else "[dim]Disponibile[/dim]"
            table.add_row(str(i), p.port, p.hw_name, p.description, status)

        self.console.print(table)

    def cmd_switch(self, args: list[str]) -> None:
        """Switch connection to another serial port."""
        ports = scan_meshtastic_ports()
        if not ports:
            self.console.print(f"[{THEME_COLORS['alert']}]Nessun dispositivo disponibile per lo switch.[/]")
            return

        target_port: str | None = None

        if not args:
            # If no arg given, find the other port
            for p in ports:
                if p.port != self.client.port:
                    target_port = p.port
                    break
            if not target_port:
                self.console.print(f"[{THEME_COLORS['warning']}]Nessun'altra porta alternativa rilevata.[/]")
                return
        else:
            arg = args[0]
            # Check if arg is an index (1-based)
            if arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(ports):
                    target_port = ports[idx].port
                else:
                    self.console.print(f"[{THEME_COLORS['alert']}]Indice non valido. Usa 1..{len(ports)}[/]")
                    return
            else:
                target_port = arg

        self.console.print(f"[{THEME_COLORS['accent']}]Passaggio in corso alla porta:[/] {target_port}...")
        success = self.client.connect(target_port, blocking=True)
        if success:
            local = self.client.get_local_node()
            name = local.display_name if local else "Sconosciuto"
            self.console.print(f"[{THEME_COLORS['secondary']}]✓ Connesso con successo a:[/] [bold]{target_port}[/] ({name})")
            self.cmd_banner([])
        else:
            self.console.print(f"[{THEME_COLORS['alert']}]Impossibile connettersi alla porta {target_port}.[/]")

    def cmd_banner(self, args: list[str]) -> None:
        """Render status banner."""
        local = self.client.get_local_node()
        channels = self.client.get_channels()
        banner = render_banner(
            local_node=local,
            port=self.client.port or "N/A",
            channel_util=local.channel_util if local else None,
            channels=channels,
        )
        self.console.print(banner)

    def cmd_view(self, args: list[str]) -> None:
        """Launch interactive full-screen table with mouse-click column sorting."""
        local_node = self.client.get_local_node()
        opener = getattr(self.console, "open_node_explorer", None)
        if callable(opener):
            opener(self.client.store, local_node)
            return

        from mesh_deck.ui.interactive_table import launch_interactive_nodes
        self.console.print(f"[{THEME_COLORS['primary']}]Avvio tabella interattiva... (Fai click sulle intestazioni per ordinare, premi 'q' o 'Esc' per tornare al prompt)[/]")
        launch_interactive_nodes(self.client.store, local_node=local_node)

    def cmd_settings(self, args: list[str]) -> None:
        """View or update user preferences (language, theme, port, sort)."""
        from mesh_deck.core.settings import Settings
        settings = Settings.load()

        if not args:
            opener = getattr(self.console, "open_settings", None)
            if callable(opener):
                opener()
                return
            table = Table(
                title="⚙️ IMPOSTAZIONI MESH-DECK",
                title_style=f"bold {THEME_COLORS['primary']}",
                border_style=THEME_COLORS["border"],
                show_header=True,
                header_style=f"bold {THEME_COLORS['primary']}",
            )
            table.add_column("Parametro", style="bold white", width=24)
            table.add_column("Valore Attuale", style="bold green", width=18)
            table.add_column("Opzioni / Come Modificare", style="dim cyan")

            table.add_row("Lingua (lang)", settings.language, "/settings lang <it|en>")
            table.add_row("Tema (theme)", settings.theme, "/settings theme <cyberpunk|high_contrast|amber|matrix>")
            table.add_row("Porta predefinita (port)", settings.default_port or "(Auto-detect)", "/settings port </dev/tty...>")
            table.add_row("Ordinamento (sort)", settings.default_sort, "/settings sort <last_heard|snr|hops|name>")
            table.add_row("Modalità UI (mode)", settings.ui_mode, "/settings mode <repl|tui>")

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
                self.console.print(f"[{THEME_COLORS['secondary']}]✓ Lingua impostata su:[/] [bold]{lang_val.upper()}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]Lingua non supportata. Usa 'it' o 'en'.[/]")
        elif sub in ("theme", "tema") and len(args) > 1:
            theme_val = args[1].lower()
            if theme_val in ("cyberpunk", "high_contrast", "amber", "matrix"):
                settings.update(theme=theme_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]✓ Tema impostato su:[/] [bold]{theme_val}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]Tema non valido. Usa 'cyberpunk', 'high_contrast', 'amber', o 'matrix'.[/]")
        elif sub in ("sort", "ordinamento") and len(args) > 1:
            sort_val = args[1].lower()
            if sort_val in ("last_heard", "snr", "hops", "name"):
                settings.update(default_sort=sort_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]✓ Ordinamento predefinito impostato su:[/] [bold]{sort_val}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]Ordinamento non valido. Usa 'last_heard', 'snr', 'hops', o 'name'.[/]")
        elif sub in ("port", "porta") and len(args) > 1:
            port_val = args[1]
            settings.update(default_port=port_val)
            self.console.print(f"[{THEME_COLORS['secondary']}]✓ Porta predefinita impostata su:[/] [bold]{port_val}[/]")
        elif sub in ("mode", "modalita") and len(args) > 1:
            mode_val = args[1].lower()
            if mode_val in ("repl", "tui"):
                settings.update(ui_mode=mode_val)
                self.console.print(f"[{THEME_COLORS['secondary']}]✓ Modalità UI impostata su:[/] [bold]{mode_val}[/]")
            else:
                self.console.print(f"[{THEME_COLORS['alert']}]Modalità non valida. Usa 'repl' o 'tui'.[/]")
        else:
            self.console.print(f"[{THEME_COLORS['warning']}]Uso:[/] /settings [lang <it|en> | theme <nome> | sort <criterio> | port <porta> | mode <repl|tui>]")

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
        self.console.print(f"[{THEME_COLORS['primary']}]Chiusura connessione radio e uscita da Mesh-Deck. 73![/]")
        self.running = False
        self.client.disconnect()
