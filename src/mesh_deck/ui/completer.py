"""Interactive autocompletion data for the Mesh-Deck Textual UI.

Provides dynamic tab-completion for slash commands (/help, /nodes, /node, /dm, etc.)
and live Meshtastic node names/IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from mesh_deck.i18n import command_descriptions
from mesh_deck.models import NodeData

# Standard supported slash commands and their descriptions
SLASH_COMMANDS = command_descriptions("it")


@dataclass(frozen=True)
class Completion:
    """A replacement candidate shown by the Textual command input."""

    value: str
    start_position: int
    description: str


class MeshDeckCompleter:
    """Smart completer for Mesh-Deck command input.

    Autocompletes slash commands and dynamically resolves node aliases (AKA)
    and Node IDs for commands requiring a node target (/node, /dm).
    """

    def __init__(
        self,
        get_nodes: Callable[[], list[NodeData]] | list[NodeData] | None = None,
        get_ports: Callable[[], list[str]] | list[str] | None = None,
        commands: dict[str, str] | None = None,
        node_getter: Callable[[], list[NodeData]] | list[NodeData] | None = None,
        port_getter: Callable[[], list[str]] | list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize completer.

        Args:
            get_nodes: Callable returning list of NodeData or static list of NodeData.
            get_ports: Optional callable or list of available serial ports for /switch.
            commands: Optional dictionary mapping slash commands to description strings.
            node_getter: Alias for get_nodes.
            port_getter: Alias for get_ports.
        """
        self._get_nodes_provider = get_nodes if get_nodes is not None else node_getter
        self._get_ports_provider = get_ports if get_ports is not None else port_getter
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

    def suggestions(self, text_before_cursor: str) -> list[Completion]:
        """Return completions based on the current input buffer."""
        stripped = text_before_cursor.lstrip()
        completions: list[Completion] = []

        if not stripped:
            return completions

        # 1. Autocomplete slash commands when typing the command itself
        if " " not in stripped:
            prefix = stripped
            if prefix.startswith("/"):
                for cmd, desc in self.commands.items():
                    if cmd.lower().startswith(prefix.lower()):
                        completions.append(Completion(
                            value=cmd,
                            start_position=-len(prefix),
                            description=desc,
                        ))
            return completions

        # 2. Dynamic argument completion for commands that target nodes (/node, /dm)
        for target_cmd in ("/node", "/dm"):
            cmd_prefix = f"{target_cmd} "
            if stripped.startswith(cmd_prefix):
                remainder = stripped[len(cmd_prefix):]
                # Check if currently inside quotes or before first argument space
                is_quoted = remainder.startswith('"') or remainder.startswith("'")
                if is_quoted:
                    q_char = remainder[0]
                    # If quote is unclosed, we are still completing the target argument
                    if remainder.count(q_char) < 2:
                        query = remainder[1:].strip().lower()
                        completions.extend(self._complete_nodes(query, len(remainder), quote=q_char))
                    return completions
                else:
                    if " " not in remainder:
                        query = remainder.strip().lower()
                        completions.extend(self._complete_nodes(query, len(remainder)))
                    return completions

        # 3. Dynamic port completion for /switch
        if stripped.startswith("/switch "):
            remainder = stripped[len("/switch "):]
            if " " not in remainder:
                query = remainder.strip().lower()
                for port in self._resolve_ports():
                    if not query or query in port.lower():
                        completions.append(Completion(
                            value=port,
                            start_position=-len(remainder),
                            description="Porta seriale USB",
                        ))
            return completions

        # 4. Dynamic settings completion for /settings
        if stripped.startswith("/settings "):
            remainder = stripped[len("/settings "):]
            parts = remainder.split()
            if len(parts) <= 1 and not remainder.endswith(" "):
                opts = [
                    ("lang", "Imposta lingua (it, en)"),
                    ("theme", "Imposta tema (cyberpunk, high_contrast, amber, matrix)"),
                    ("sort", "Imposta ordinamento predefinito"),
                    ("port", "Imposta porta seriale predefinita"),
                ]
                q = remainder.lower().strip()
                for opt, desc in opts:
                    if not q or opt.startswith(q):
                        completions.append(Completion(opt, -len(remainder), desc))
            elif len(parts) >= 1:
                sub = parts[0].lower()
                sub_rem = remainder[len(parts[0]):].strip().lower()
                if sub == "lang":
                    for l, d in [("it", "Italiano"), ("en", "English")]:
                        if not sub_rem or l.startswith(sub_rem):
                            completions.append(Completion(l, -len(sub_rem), d))
                elif sub == "theme":
                    for th, d in [("cyberpunk", "Cyberpunk Cyan/Amber"), ("high_contrast", "High Contrast"), ("amber", "Retro Amber"), ("matrix", "Phosphor Green")]:
                        if not sub_rem or th.startswith(sub_rem):
                            completions.append(Completion(th, -len(sub_rem), d))
                elif sub == "sort":
                    for s in ["last_heard", "snr", "hops", "name"]:
                        if not sub_rem or s.startswith(sub_rem):
                            completions.append(Completion(s, -len(sub_rem), s))
            return completions

        return completions

    def _complete_nodes(
        self,
        query: str,
        replace_len: int,
        quote: str | None = None,
    ) -> list[Completion]:
        """Generate completions for node AKA and Node ID."""
        nodes = self._resolve_nodes()
        seen: set[str] = set()
        completions: list[Completion] = []

        for node in nodes:
            long_name = str(node.long_name or "")
            short_clean = str(node.short_name or "").strip()
            node_id_clean = str(node.id or "").strip()
            role_str = str(node.role or "CLIENT")

            meta = f"{long_name} [{role_str}]"
            if node.snr is not None:
                meta += f" | SNR: {node.snr:+.1f}dB"

            # Suggest AKA / Short name
            if short_clean and short_clean != "????":
                if not query or query in short_clean.lower() or query in long_name.lower():
                    if short_clean not in seen:
                        seen.add(short_clean)
                        # Quote short name if it contains spaces
                        if quote:
                            insert_text = f"{quote}{short_clean}{quote}"
                        elif " " in short_clean:
                            insert_text = f'"{short_clean}"'
                        else:
                            insert_text = short_clean

                        completions.append(Completion(
                            value=insert_text,
                            start_position=-replace_len,
                            description=f"{short_clean} (AKA) - {meta}",
                        ))

            # Suggest Hex Node ID (e.g. "!45a466e4")
            if node_id_clean:
                if not query or query in node_id_clean.lower() or query in node_id_clean.lstrip("!").lower():
                    if node_id_clean not in seen:
                        seen.add(node_id_clean)
                        insert_text = f"{quote}{node_id_clean}{quote}" if quote else node_id_clean
                        completions.append(Completion(
                            value=insert_text,
                            start_position=-replace_len,
                            description=f"{node_id_clean} (ID) - {long_name} [{short_clean}]",
                        ))

        return completions
