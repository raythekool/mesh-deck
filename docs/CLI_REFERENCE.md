# Mesh-Deck CLI and Automation Reference

This reference describes the non-interactive `mesh-deck` command surface for scripts, operators, and automation agents. For interactive slash commands and TUI controls, use the [User and Operations Guide](USER_GUIDE.md).

## Invocation modes

Run from a checkout:

```bash
uv run mesh-deck
```

Run an installed command:

```bash
mesh-deck
```

Run once without installing:

```bash
uvx --from git+https://github.com/raythekool/mesh-deck mesh-deck
```

All subcommands accept the installed `mesh-deck` form. When working inside the repository, prefix examples with `uv run`.

## Global interactive options

| Option | Description |
| :-- | :-- |
| `-p`, `--port <DEVICE_PORT>` | Connect the interactive console directly to a serial port instead of opening the device selector. |
| `--tui` | Open the Node Explorer immediately after connecting. |
| `-h`, `--help` | Show command help. |

`--list` and `--nodes` remain temporarily compatible, but are deprecated and will be removed in v0.4.0. Use `scan` and `nodes` instead.

## Non-interactive subcommands

| Command | Purpose |
| :-- | :-- |
| `scan` | List detected Meshtastic USB serial devices. |
| `info` | Show connected radio information. |
| `channels` | List configured channels without returning secret keys or raw channel configuration. |
| `nodes` | List nodes in the mesh. |
| `node <query>` | Show one node by ID, number, alias, or name. |
| `neighbors [query]` | Show NeighborInfo tables, optionally limited to one reporter. |
| `trace <target>` | Trace the hop path toward a node. |
| `send <text>` | Preview or send a broadcast message. |
| `dm <target> <text>` | Preview or send a direct message. |
| `mcp` | Run the local MCP server over stdio. |

Connection-aware subcommands support:

| Option | Description |
| :-- | :-- |
| `--port <DEVICE_PORT>` | Meshtastic serial port; defaults to saved settings or auto-detection. |
| `--timeout <SECONDS>` | Connection timeout; defaults to `30`. |
| `--output human|json` | Output format for commands that support machine-readable responses. |

## Common examples

```bash
# List connected radios.
mesh-deck scan

# List active nodes as JSON, sorted by signal strength.
mesh-deck nodes --sort snr --active --output json

# Read one node by alias, name, ID, or number.
mesh-deck node TRIN --port /dev/ttyACM0 --output json

# Inspect channel metadata without exposing PSKs.
mesh-deck channels --output json

# Trace a route using a specific hop limit.
mesh-deck trace TRIN --hop-limit 5 --output json
```

## JSON envelope

Successful responses use a stable `ok: true` envelope:

```json
{"ok": true, "command": "scan", "data": {"devices": [], "count": 0}}
```

Failures use `ok: false` and a stable `error` object:

```json
{
  "ok": false,
  "command": "node",
  "error": {
    "code": "node_not_found",
    "message": "No node matched the query.",
    "details": {"query": "TRIN"}
  }
}
```

## Exit codes

| Exit code | Meaning |
| :-- | :-- |
| `0` | Command completed successfully. |
| `2` | Invalid input. |
| `3` | Missing node. |
| `4` | No device is available. |
| `5` | Connection failed. |
| `6` | Transmission failed. |

## Message previews and confirmed transmission

Message commands are previews unless `--confirm` is explicitly provided.

```bash
mesh-deck send "Weather check" --output json
mesh-deck send "Weather check" --channel 1 --confirm --output json
mesh-deck dm TRIN "Return to base" --confirm --output json
```

This prevents scripts and agents from transmitting accidentally while still allowing them to inspect the intended operation.

## MCP server

Run the local Model Context Protocol server over stdio:

```bash
mesh-deck mcp
mesh-deck mcp --port /dev/ttyACM0
```

Generic MCP client configuration:

```json
{
  "mcpServers": {
    "mesh-deck": {
      "command": "uv",
      "args": ["run", "mesh-deck", "mcp", "--port", "/dev/ttyACM0"]
    }
  }
}
```

The server exposes:

- `scan_devices`
- `get_radio_info`
- `list_nodes`
- `get_node`
- `list_channels`
- `list_neighbors`
- `trace_route`
- `send_broadcast`
- `send_direct_message`

The send tools return a preview by default and transmit only when called with `confirm=true`. Channel keys and raw channel configuration are never returned.
