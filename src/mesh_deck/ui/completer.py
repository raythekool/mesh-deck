"""Interactive autocompletion for Mesh-Deck REPL using prompt_toolkit.

Provides dynamic tab-completion for slash commands (/help, /nodes, /node, /dm, etc.)
and live Meshtastic node names/IDs.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from mesh_deck.models import NodeData

# Standard supported slash commands and their descriptions
SLASH_COMMANDS: dict[str, str] = {
    "/help": "Mostra la guida ai comandi e alle scorciatoie",
    "/nodes": "Elenco e tabella dei nodi rilevati nella mesh",
    "/node": "Scheda analitica di dettaglio per un nodo (/node <id|aka>)",
    "/dm": "Invia un messaggio privato diretto (/dm <id|aka> <testo>)",
    "/send": "Invia un messaggio broadcast sul canale (/send [canale] <testo>)",
    "/switch": "Cambia la radio o porta seriale attiva (/switch <porta>)",
    "/channels": "Mostra l'elenco e lo stato dei canali radio",
    "/info": "Informazioni diagnostiche e stato del nodo locale",
    "/clear": "Pulisce lo schermo della console",
    "/quit": "Disconnette ed esce dall'applicazione",
}


class MeshDeckCompleter(Completer):
    """Smart prompt_toolkit completer for Mesh-Deck.

    Autocompletes slash commands and dynamically resolves node aliases (AKA)
    and Node IDs for commands requiring a node target (/node, /dm).
    """

    def __init__(
        self,
        get_nodes: Callable[[], list[NodeData]] | list[NodeData] | None = None,
        get_ports: Callable[[], list[str]] | list[str] | None = None,
        commands: dict[str, str] | None = None,
    ) -> None:
        """Initialize completer.

        Args:
            get_nodes: Callable returning list of NodeData or static list of NodeData.
            get_ports: Optional callable or list of available serial ports for /switch.
            commands: Optional dictionary mapping slash commands to description strings.
        """
        self._get_nodes_provider = get_nodes
        self._get_ports_provider = get_ports
        self.commands = commands or SLASH_COMMANDS

    def _resolve_nodes(self) -> list[NodeData]:
        """Fetch current list of nodes from provider."""
        if self._get_nodes_provider is None:
            return []
        if callable(self._get_nodes_provider):
            return self._get_nodes_provider()
        return self._get_nodes_provider

    def _resolve_ports(self) -> list[str]:
        """Fetch current list of serial ports from provider."""
        if self._get_ports_provider is None:
            return []
        if callable(self._get_ports_provider):
            return self._get_ports_provider()
        return self._get_ports_provider

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        """Yield completions based on current input buffer."""
        text_before_cursor = document.text_before_cursor
        stripped = text_before_cursor.lstrip()

        # 1. Autocomplete slash commands when typing the command itself
        if " " not in text_before_cursor:
            prefix = stripped
            if prefix.startswith("/"):
                for cmd, desc in self.commands.items():
                    if cmd.lower().startswith(prefix.lower()):
                        yield Completion(
                            text=cmd,
                            start_position=-len(prefix),
                            display=cmd,
                            display_meta=desc,
                        )
            return

        # 2. Dynamic argument completion for commands that target nodes (/node, /dm)
        for target_cmd in ("/node", "/dm"):
            cmd_prefix = f"{target_cmd} "
            if stripped.startswith(cmd_prefix):
                remainder = stripped[len(cmd_prefix):]
                # For /node, there is only 1 argument.
                # For /dm, syntax is /dm <target> <message>. Once a space is present, stop node suggestions.
                if " " not in remainder:
                    query = remainder.strip().lower()
                    yield from self._complete_nodes(query, len(remainder))
                return

        # 3. Dynamic port completion for /switch
        if stripped.startswith("/switch "):
            remainder = stripped[len("/switch "):]
            if " " not in remainder:
                query = remainder.strip().lower()
                for port in self._resolve_ports():
                    if query in port.lower():
                        yield Completion(
                            text=port,
                            start_position=-len(remainder),
                            display=port,
                            display_meta="Porta Seriale USB",
                        )
            return

    def _complete_nodes(self, query: str, replace_len: int) -> Iterable[Completion]:
        """Generate completions for node AKA and Node ID."""
        nodes = self._resolve_nodes()
        seen: set[str] = set()

        for node in nodes:
            meta = f"{node.long_name} [{node.role}]"
            if node.snr is not None:
                meta += f" | SNR: {node.snr:+.1f}dB"

            # Suggest AKA / Short name
            short_clean = node.short_name.strip()
            if short_clean and short_clean != "????":
                if not query or query in short_clean.lower() or query in node.long_name.lower():
                    if short_clean not in seen:
                        seen.add(short_clean)
                        yield Completion(
                            text=short_clean,
                            start_position=-replace_len,
                            display=f"{short_clean:<6} (AKA)",
                            display_meta=meta,
                        )

            # Suggest Hex Node ID (e.g. "!45a466e4")
            node_id_clean = node.id.strip()
            if node_id_clean:
                if not query or query in node_id_clean.lower() or query in node_id_clean.lstrip("!").lower():
                    if node_id_clean not in seen:
                        seen.add(node_id_clean)
                        yield Completion(
                            text=node_id_clean,
                            start_position=-replace_len,
                            display=f"{node_id_clean:<11} (ID)",
                            display_meta=f"{node.long_name} [{short_clean}]",
                        )
