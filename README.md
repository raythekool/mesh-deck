# 📡 Mesh-Deck

**Mesh-Deck** is an interactive, Hermes-style Terminal User Interface (TUI) and Command-Line Interface (CLI) for exploring, managing, and interacting with Meshtastic devices. 

## Features (Planned)
- **Multi-Device Support:** Seamlessly connect and switch between multiple local Meshtastic devices via USB (e.g., Heltec, LilyGo).
- **Hermes-style TUI:** Interactive REPL and dashboard with rich terminal styling.
- **Node Explorer:** Live views of nodes, SNR, hops, battery, and telemetry.
- **Messaging:** Broadcast and Direct Message support directly from the terminal.
- **Diagnostics:** Traceroutes, channel utilization, and mesh state analysis.

## Tech Stack
- [Python 3.11+](https://www.python.org/)
- [uv](https://github.com/astral-sh/uv) (for dependency management and fast execution)
- [Meshtastic Python API](https://pypi.org/project/meshtastic/)
- [Rich](https://rich.readthedocs.io/) & [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) (or [Textual](https://textual.textualize.io/))

## License
MIT License
