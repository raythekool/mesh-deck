"""Main entrypoint for Mesh-Deck."""

from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    console.print(
        Panel.fit(
            "[bold cyan]📡 Mesh-Deck[/bold cyan] - [dim]Hermes-style Meshtastic CLI/TUI[/dim]\n"
            "[green]Inizializzazione completata.[/green] Consulta [bold]IMPLEMENTATION_PLAN.md[/bold] per la roadmap.",
            border_style="cyan",
        )
    )

if __name__ == "__main__":
    main()
