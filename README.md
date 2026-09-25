# Mesh-Deck

Mesh-Deck is a terminal-first console for exploring, managing, and communicating with Meshtastic radios and mesh networks.

It combines a full-screen Textual interface, Rich tactical panels, non-blocking serial work, local history, and automation-friendly CLI/MCP commands. It is intended for field operators, radio experimenters, emergency-response teams, and developers who need a dense but readable view of a Meshtastic network.

## Get started

Mesh-Deck requires Python 3.11 or later and is managed with [uv](https://github.com/astral-sh/uv).

### Run from a checkout

```bash
git clone https://github.com/raythekool/mesh-deck.git
cd mesh-deck
uv run mesh-deck
```

### Install the `mesh-deck` command

Install the project as a uv tool when you want to run `mesh-deck` from any directory.

```bash
# From a local checkout. Local edits and git pulls take effect immediately.
uv tool install --editable .

# Or install directly from GitHub.
uv tool install git+https://github.com/raythekool/mesh-deck
```

Then run:

```bash
mesh-deck
mesh-deck scan
mesh-deck nodes --output json
```

If the shell cannot find `mesh-deck`, run `uv tool update-shell`, open a new shell, and verify the tool bin directory with `uv tool dir --bin`.

To run Mesh-Deck once without installing it:

```bash
uvx --from git+https://github.com/raythekool/mesh-deck mesh-deck
```

### Connect to a specific radio

Interactive startup opens a device selector. Use `--port` to skip selection when the serial device is known.

```bash
mesh-deck --port COM6
mesh-deck --port /dev/ttyACM0
```

On Linux, make sure your user can access serial ports. Debian and Ubuntu commonly require membership in `dialout`; Arch Linux commonly uses `uucp`.

```bash
sudo usermod -a -G dialout $USER
newgrp dialout
```

## What Mesh-Deck does

- **Finds and switches radios**: auto-detects common Meshtastic USB serial devices and hot-switches with `/switch`.
- **Keeps the UI responsive**: serial connection, NodeDB synchronization, traceroute, and command work run outside the Textual event loop.
- **Monitors nodes**: shows node identity, role, SNR, hops, battery, position, last-heard age, and distance from the local node.
- **Explores the mesh**: `/neighbors`, `/mesh`, `/topology`, and `/trace` expose NeighborInfo, topology quality, and hop paths.
- **Supports messaging**: `/send`, `/dm`, and `/chat` handle broadcasts, per-peer direct-message conversations, unread badges, and explicit reply targets.
- **Persists useful history**: optional JSONL node and message history powers chat preload and on-demand telemetry views.
- **Surfaces diagnostics**: `/logs` separates Mesh-Deck application events from connected-device log lines with filters, pause, copy, and export.
- **Protects risky device writes**: `/device-settings` currently supports a safe identity-editing slice with draft validation, semantic diff, confirmation, and radio acknowledgement.
- **Supports automation**: non-interactive CLI commands and the local MCP server expose scan, node, channel, neighbor, trace, and transmission-preview workflows.
- **Keeps visual state accessible**: four themes (`cyberpunk`, `midnight`, `nord`, `ember`) share semantic colour roles, contrast checks, and visible keyboard focus.

## Interface preview

The screenshots below are deterministic SVG renderings generated from sample data; no physical radio is required to regenerate them.

```bash
uv run python tools/make_screenshots.py
uv run python tools/make_screenshots.py --theme nord
```

### Hermes banner and local system status

The banner gives an at-a-glance view of radio state, local node status, active channels, modem preset, and RF saturation.

![Hermes tactical banner](docs/screenshots/banner.svg)

### Mesh node explorer and telemetry

The node table highlights the local node, SNR, hop count, power state, and distance estimate.

![Mesh node table](docs/screenshots/nodes_table.svg)

### Detailed node dossier

`/node` and the node explorer expose hardware details, RF metrics, environmental telemetry, GPS coordinates, and map links.

![Node detail panel](docs/screenshots/node_detail.svg)

### Tactical messaging and direct messages

Incoming traffic remains visible while the command input keeps focus. Direct messages are highlighted separately from channel broadcasts.

![Messaging and DM view](docs/screenshots/messaging.svg)

### Main console with node sidebar

The full-screen console includes the tactical banner, streaming log, command input, and a resizable node sidebar.

![Console with node sidebar](docs/screenshots/console.svg)

### Channel and DM chat viewer

`/chat` provides a mouse-usable channel and direct-message view with per-peer conversations and explicit recipients.

![Channel and DM chat viewer](docs/screenshots/chat.svg)

## Documentation map

| Document | Use it for |
| :-- | :-- |
| [User and Operations Guide](docs/USER_GUIDE.md) | Day-to-day usage, startup behavior, slash commands, controls, operational concepts, and troubleshooting. |
| [CLI and Automation Reference](docs/CLI_REFERENCE.md) | Non-interactive commands, JSON envelopes, exit codes, transmission previews, deprecated launch flags, and MCP setup. |
| [UI Development Proposals](docs/UI_DEVELOPMENT.md) | Implemented UI roadmap, wireframes, safe slices, and non-goals. |
| [Requirements](REQUIREMENTS.md) | Functional, non-functional, UI, and architecture requirements. |
| [Implementation Plan](IMPLEMENTATION_PLAN.md) | Development roadmap, delivered phases, validation notes, and future work. |

## Development snapshot

Mesh-Deck is a Python 3.11+ project using Rich, Textual, pyserial, meshtastic-python, and uv.

Run the full test suite with:

```bash
uv run python -m unittest discover -s tests
```

See [AGENTS.md](AGENTS.md) for repository-specific development rules and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for architecture and validation history.

## License

Distributed under the [MIT](LICENSE) license.
