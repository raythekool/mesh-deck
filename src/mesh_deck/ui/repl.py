"""Interactive REPL engine using prompt_toolkit and Rich."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console

from mesh_deck.core.events import MeshMessage
from mesh_deck.ui.completer import MeshDeckCompleter
from mesh_deck.ui.tables import render_message
from mesh_deck.ui.theme import THEME_COLORS

if TYPE_CHECKING:
    from mesh_deck.commands.dispatcher import CommandDispatcher
    from mesh_deck.core.radio_client import RadioClient


class MeshDeckREPL:
    """Hermes-style interactive REPL loop for Mesh-Deck."""

    def __init__(
        self,
        radio_client: RadioClient,
        console: Console | None = None,
        dispatcher: CommandDispatcher | None = None,
    ) -> None:
        self.client = radio_client
        self.console = console or Console()
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            from mesh_deck.commands.dispatcher import CommandDispatcher
            self.dispatcher = CommandDispatcher(self.client, console=self.console)
        self.completer = MeshDeckCompleter(
            get_nodes=self._get_all_nodes,
            get_ports=self._get_available_ports,
        )
        self.history = InMemoryHistory()
        self.session: PromptSession = PromptSession(
            completer=self.completer,
            history=self.history,
            complete_while_typing=False,
        )

        # Wire up incoming message listener
        self.client.on_message_received(self._handle_incoming_message)

    def _get_all_nodes(self) -> list:
        """Helper to get current nodes for autocompletion."""
        return self.client.store.get_all_nodes()

    def _get_available_ports(self) -> list[str]:
        """Helper to get detected ports for /switch autocompletion."""
        from mesh_deck.core.scanner import scan_meshtastic_ports
        return [p.port for p in scan_meshtastic_ports()]

    def _handle_incoming_message(self, msg: MeshMessage) -> None:
        """Format and print incoming radio messages above the prompt."""
        rendered = render_message(msg)
        self.console.print(rendered)

    def _get_prompt(self) -> HTML:
        """Dynamic prompt showing active node name or port."""
        local = self.client.get_local_node()
        if local:
            name = local.short_name or local.long_name or local.id
            return HTML(
                f"<ansicyan><b>mesh-deck</b></ansicyan> "
                f"<ansigreen>[{name}]</ansigreen> "
                f"<ansicyan>❯</ansicyan> "
            )
        return HTML("<ansicyan><b>mesh-deck</b></ansicyan> <ansigreen>❯</ansigreen> ")

    def run(self) -> None:
        """Run the interactive REPL loop."""
        # Initial status banner
        self.dispatcher.cmd_banner([])

        # Ensure live output can print above the prompt without garbling input
        with patch_stdout(raw=True):
            while self.dispatcher.running:
                try:
                    user_input = self.session.prompt(self._get_prompt)
                    should_continue = self.dispatcher.dispatch(user_input)
                    if not should_continue:
                        break
                except KeyboardInterrupt:
                    # Ctrl+C clears line without exiting
                    continue
                except EOFError:
                    # Ctrl+D exits
                    self.dispatcher.cmd_quit([])
                    break
                except Exception as e:
                    self.console.print(f"[{THEME_COLORS['alert']}]Errore:[/] {e}")
