# Mesh-Deck — User and Operations Guide

Mesh-Deck is a tactical terminal console for monitoring, managing, and communicating over [Meshtastic](https://meshtastic.org/) radio networks.

It is intended for amateur-radio operators, emergency-response teams, hikers, and off-grid communications enthusiasts using Meshtastic LoRa nodes in the field or at a base station.

![Hermes tactical banner](screenshots/banner.svg)

## 1. Design and supported hardware

### Hermes TUI

Mesh-Deck uses the Hermes TUI visual model rather than a conventional line-only CLI or a heavyweight web interface.

- **High-contrast themes:** Semantic palettes use clearly differentiated primary, success, warning, and error colours. The default is `cyberpunk`; `midnight`, `nord`, and `ember` are also available.
- **Dense operational information:** Link state, battery, voltage, SNR, hops, and channel status are presented in compact Rich panels and tables.
- **Responsive Textual UI:** The full-screen console has contextual input, scrollable output, persisted history, dynamic completion, and mouse-capable controls.
- **Non-blocking work:** Serial connection and command operations run outside the UI event loop so incoming radio events can remain visible.

`Tab` completes an input without executing it. `Enter` runs the selected command completion or submits the typed command.

### Supported devices

Detection is heuristic and supports common Meshtastic-capable USB serial hardware, including:

- Heltec Vision Master E290, WiFi LoRa 32, Wireless Stick Lite, and Capsule Sensor boards.
- LilyGo T-Beam, T-Echo, T-Motion, and T3S3 boards.
- RAK WisBlock / RAK4631, RAK11200, and RAK11310 boards.
- DIY RP2040, nRF52840, and ESP32-based nodes exposed through CH340, CP210x, FTDI, or similar serial bridges.

## 2. Installation and startup

Mesh-Deck requires Python 3.11 or later and is managed with [uv](https://github.com/astral-sh/uv).

### Linux serial permissions

On Debian or Ubuntu, add the current user to `dialout`; Arch Linux commonly uses `uucp`.

```bash
# Add the current user to the serial-port group.
sudo usermod -a -G dialout $USER

# Apply the membership now, or sign out and back in.
newgrp dialout
```

### Run from a checkout

```bash
git clone https://github.com/raythekool/mesh-deck.git
cd mesh-deck
uv run mesh-deck
```

### Install the `mesh-deck` command

`uv run` must be executed from the repository. Install the project as a uv tool to use `mesh-deck` from any directory.

```bash
# From the repository root. This tracks the checkout, so local edits and git pulls take effect immediately.
uv tool install --editable .

# Or install directly from GitHub without cloning first.
uv tool install git+https://github.com/raythekool/mesh-deck
```

After installation:

```bash
mesh-deck
mesh-deck nodes --output json
```

Use `uv tool list` to inspect installed tools, `uv tool upgrade mesh-deck` to update a non-editable installation, and `uv tool uninstall mesh-deck` to remove it.

If the shell cannot find `mesh-deck`, run `uv tool update-shell`, open a new shell, and verify the tool bin directory with `uv tool dir --bin`.

An editable tool points at the checkout from which it was installed. If that checkout is moved or deleted, reinstall it from the new location with `uv tool install --editable .`.

To run Mesh-Deck once without installing it:

```bash
uvx --from git+https://github.com/raythekool/mesh-deck mesh-deck
```

### Device selection at startup

Interactive startup opens a Textual device selector before connecting. The saved default port is highlighted when available but is not connected automatically.

| Action | Control |
| :-- | :-- |
| Move selection | Up / Down |
| Connect selected device | `Enter` |
| Rescan serial devices | `r` |
| Retry the last failed device | `t` |
| Cancel startup | `q` or `Esc` |

Use `--port COM6` on Windows or `--port /dev/ttyACM0` on Linux/macOS to bypass the selector for a known device.

The connection handshake and NodeDB synchronization run in the background. If a connection fails, the selector remains available to choose a different device.

The selector marks the preferred port, currently active port when relevant, and the port whose most recent connection failed. It displays that error with an explicit retry action. If no device is found, it shows cable, power, serial-driver, and port-ownership recovery guidance before offering `r` to rescan.

### CLI flags

| Flag | Argument | Description |
| :-- | :-- | :-- |
| `-p`, `--port` | `<DEVICE_PORT>` | Connect directly to one serial port. |
| `-l`, `--list` | none | Scan serial USB ports, print detected Meshtastic candidates, and exit. |
| `-n`, `--nodes` | none | Connect, print the current node table, and exit. |
| `--tui` | none | Open the Node Explorer after connecting. |
| `-h`, `--help` | none | Show CLI help. |

Examples:

```bash
# List connected radios.
mesh-deck --list

# Connect to a known port.
mesh-deck --port COM6

# Save a non-interactive node snapshot.
mesh-deck --nodes > mesh_snapshot.txt
```

### Agent-friendly CLI

The non-interactive commands return human-readable output by default or a stable JSON envelope with `--output json`.

```bash
mesh-deck scan --output json
mesh-deck nodes --sort snr --active --output json
mesh-deck node TRIN --output json
mesh-deck info --output json
mesh-deck channels --output json
mesh-deck neighbors --output json
mesh-deck trace TRIN --output json
```

Successful JSON output uses this shape:

```json
{"ok":true,"command":"scan","data":{"devices":[],"count":0}}
```

Errors use `ok: false` with an `error` object containing `code`, `message`, and `details`.

| Exit code | Meaning |
| :-- | :-- |
| `0` | Completed successfully, including a non-transmitting preview. |
| `1` | Unexpected internal error. |
| `2` | Invalid input or option. |
| `3` | Node not found. |
| `4` | No device available. |
| `5` | Serial connection failed. |
| `6` | Transmission failed. |

`send` and `dm` CLI commands preview by default. Add `--confirm` to transmit.

```bash
mesh-deck send "Radio test" --output json
mesh-deck send "Radio test" --confirm --output json
mesh-deck dm TRIN "Private message" --confirm --output json
```

A broadcast preview does not need a radio connection. A direct-message preview needs an active connection because Mesh-Deck must resolve the target node in the NodeStore.

### Local MCP server

The local Model Context Protocol server uses stdio and keeps one shared radio session for its lifetime.

```bash
mesh-deck mcp --port COM6
```

Example generic MCP configuration:

```json
{
  "mcpServers": {
    "mesh-deck": {
      "command": "mesh-deck",
      "args": ["mcp", "--port", "COM6"]
    }
  }
}
```

The server exposes `scan_devices`, `get_radio_info`, `list_nodes`, `get_node`, `list_channels`, `list_neighbors`, `trace_route`, `send_broadcast`, and `send_direct_message`.

The two send tools require `confirm=true` to transmit. Channel PSKs and raw channel configuration are never returned.

## 3. Interactive console

The main console contains a tactical banner, persistent radio status strip, scrollable output, a contextual command input, and an optional live node sidebar.

The radio status strip remains visible while output scrolls. It identifies the local node and port when connected, changes to a reconnecting state with the current retry attempt after an unexpected loss, and clearly shows when no radio is connected.

Potentially slow commands show a durable progress line above the input. Mesh-Deck accepts no second command while the active worker is running. During `/trace`, press `Esc` to cancel the response wait; serial connection and `/switch` remain non-cancellable because their underlying handshake cannot be safely interrupted.

```text
mesh-deck [AKA] - message or /help
```

`[AKA]` is the short identifier of the connected local node when known. Type a slash command, or type plain text to broadcast it on channel 0.

### Console controls

| Action | Control |
| :-- | :-- |
| Send a command or message | `Enter` |
| Complete without executing | `Tab` |
| Accept a command suggestion | `Enter` |
| Select a different suggestion | Down, Up / Down, `Enter` |
| Browse command history | Up / Down while the command input is focused |
| Clear the current input | `Ctrl+C` |
| Hide suggestions or close a sidebar detail card | `Esc` |
| Toggle node sidebar | `Ctrl+B` |
| Open a sidebar node detail | Click a row or press `Enter` |

The command history retains the latest 100 entries in `~/.config/mesh-deck/settings.json`.

The node sidebar shows role, SNR, long name, and last-heard data. Its controls cycle sort order and filters; its width, visibility, sort, and filter are persisted.

![Console with node sidebar](screenshots/console.svg)

### `/help` or `/?`

- **Syntax:** `/help` or `/?`
- **Purpose:** Show every supported interactive command and its argument syntax.

### `/nodes`

- **Syntax:** `/nodes [active|snr|hops|name|last_heard]`
- **Purpose:** Print the discovered node table in the output log.
- **Arguments:** `active` limits the list to recently heard nodes; `snr`, `hops`, `name`, and `last_heard` select a sort order.

The local node is marked with a green star and a local badge.

![Mesh node table](screenshots/nodes_table.svg)

Examples:

```text
/nodes
/nodes active
/nodes snr
```

### `/view` or `/tui`

- **Syntax:** `/view` or `/tui`
- **Purpose:** Open the internal interactive Node Explorer.
- **Filter:** Type in the filter field to search name, AKA, hardware, or ID.
- **Sort:** Click a column header.
- **Refresh:** Press `r`.
- **Focus filter:** Press `/`.
- **Return:** Press `q` or `Esc`.
- **Node detail:** Click a row or press `Enter`. Wide terminals show a persistent detail pane beside the table; compact terminals push an internal detail screen.
- **Density:** Press `v` to cycle `Auto`, `Full`, and `Compact`. In `Auto`, the compact table activates below 120 terminal columns. The chosen mode is persisted locally.

### `/chat`

- **Syntax:** `/chat`
- **Purpose:** Open a mouse-capable channel and direct-message history screen.

The channel list includes configured channels and a Direct Messages section with one conversation per peer. Click a channel to view its persisted and live messages, or click a peer to view that direct conversation.

The bottom input broadcasts to the selected channel or sends an explicit reply to the selected direct-message peer. The recipient remains visible in the reply hint. Use `/dm` to start a conversation with a node that has not yet appeared in the list.

Unread message counts appear on non-selected channel or direct-message conversations. Press `r` to refresh channels and `q` or `Esc` to return.

### `/node`

- **Syntax:** `/node <id|aka|name>`
- **Purpose:** Show a full dossier for one node.

The dossier includes identity, hardware, role, radio metrics, propagation, battery, available environmental sensors, GPS location, geodesic distance, initial bearing, OpenStreetMap link, and an announced public key.

![Node detail panel](screenshots/node_detail.svg)

Examples:

```text
/node TRIN
/node !45a466e4
/node Tracker
```

### `/send`

- **Syntax:** `/send <message>` or plain text at the prompt
- **Purpose:** Broadcast text on primary channel 0.

Every line that does not begin with `/` is treated as a broadcast message.

```text
/send Network active. Evening propagation test OK.
Hello from the field station.
```

### `/dm`

- **Syntax:** `/dm <id|aka|name> <message>`
- **Purpose:** Send a direct message to a known node, or to a well-formed eight-digit hexadecimal node ID.

Unknown names are rejected before reaching the radio library. This protects the interactive console from invalid target handling in upstream libraries.

![Tactical messaging and direct messages](screenshots/messaging.svg)

```text
/dm TRIN Coordinates received. See you at waypoint two.
/dm !b8f862d9 Repeater battery is at 35%; plan a swap.
```

### `/channels`

- **Syntax:** `/channels`
- **Purpose:** List configured radio channels.

The table shows index, name, role, uplink/downlink state, and whether a PSK is configured. It never displays the key itself.

### `/info`

- **Syntax:** `/info`
- **Purpose:** Show local device and radio information.

It includes serial port, connection state, local node identity, hardware model, role, GPS position, RF region, modem preset, firmware version, and active-channel count.

### `/neighbors` or `/vicini`

- **Syntax:** `/neighbors [id|aka|name]`
- **Purpose:** Show received NeighborInfo tables.

Nodes with NeighborInfo enabled periodically broadcast their direct neighbours and their observed SNR. If no node broadcasts NeighborInfo, an empty result is normal and does not indicate a Mesh-Deck error.

### `/mesh`

- **Syntax:** `/mesh`
- **Purpose:** Summarize mesh topology.

The table combines node role, hops, SNR, estimated distance, and the number of reporting nodes that list each node as a direct neighbour.

### `/trace` or `/traceroute`

- **Syntax:** `/trace <id|aka|name>`
- **Purpose:** Run a Meshtastic traceroute to one node.

The result shows the forward route, per-hop SNR, and return route when available. A timeout is a normal outcome on a congested or unreachable mesh.

### `/scan`

- **Syntax:** `/scan`
- **Purpose:** Rescan serial ports and display Meshtastic candidates, hardware names, descriptions, and current connection state.

### `/switch`

- **Syntax:** `/switch [port|index]`
- **Purpose:** Switch the active radio without leaving Mesh-Deck.

With no argument, Mesh-Deck selects the first different detected port. With an index, it uses the one-based index shown by `/scan`.

```text
/switch COM7
/switch 2
/switch
```

### `/settings` or `/config`

- **Syntax:** `/settings` or `/settings <lang|theme|sort|port|mode|notifications|history> <value>`
- **Purpose:** View or update local Mesh-Deck preferences.

Open `/settings` without arguments for the native dialog. Use arguments for direct changes, for example `/settings lang en`, `/settings theme nord`, `/settings sort snr`, `/settings notifications off`, or `/settings history off`.

Preferences are saved in `~/.config/mesh-deck/settings.json`. Language, theme, sidebar labels, prompt, autocomplete, and the mounted Node Explorer update without a restart.

#### Available themes

| Theme | Appearance |
| :-- | :-- |
| `cyberpunk` | Neon cyan and green on deep black. Default. |
| `midnight` | Low-glare indigo with soft blue and violet. |
| `nord` | Cool arctic palette for long sessions. |
| `ember` | Warm amber and coral on charcoal. |

An unknown theme value is rejected by `/settings` and falls back to `cyberpunk` during startup.

### `/restart`

- **Syntax:** `/restart`
- **Purpose:** Reload saved preferences, redraw the console, clear output, and print the banner without disconnecting the radio.

### `/banner`

- **Syntax:** `/banner`
- **Purpose:** Redraw the tactical status banner with local node, port, RF profile, battery, channel utilization, and active channels.

### `/clear`

- **Syntax:** `/clear`
- **Purpose:** Clear the output log while preserving the connection and command history.

### `/quit`, `/exit`, or `/q`

- **Syntax:** `/quit`, `/exit`, or `/q`
- **Purpose:** Disconnect cleanly and leave Mesh-Deck.

## 4. Key operational concepts

### USB discovery and hot switching

Mesh-Deck scans serial ports through `pyserial`, combining USB VID/PID information and descriptor keywords to find plausible Meshtastic devices.

When `/switch` changes radio, `RadioClient` closes the old serial interface, opens the new interface, reloads its NodeDB, keeps PubSub listeners wired, and updates the active local-node context.

An unexpected serial loss is reported in the console and retried automatically with exponential backoff. An explicit `/quit`, `/switch`, or direct connection request cancels automatic retry activity.

### Node Explorer and geodesic calculations

`NodeStore` maintains the synchronized in-memory state of every node heard over radio.

#### Haversine distance

When both the local and remote nodes publish valid coordinates, Mesh-Deck calculates great-circle distance with the Haversine formula using the mean Earth radius, `R = 6371.0088 km`.

$$\Delta\sigma = 2 \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)} \right)$$

$$d = R \cdot \Delta\sigma$$

Distances display in metres below 1 km, with two decimals from 1 to 10 km, and with one decimal above 10 km.

#### Initial bearing

The `/node` dossier also shows the initial bearing from the local node to the selected remote node, useful for orienting a directional antenna.

$$\theta = \operatorname{atan2}\big(\sin(\Delta\lambda)\cos(\phi_2),\; \cos(\phi_1)\sin(\phi_2) - \sin(\phi_1)\cos(\phi_2)\cos(\Delta\lambda)\big)$$

The result is normalized to `[0°, 360°)` where 0° is true north and is accompanied by a sixteen-point compass abbreviation such as `127° SE`.

On long routes the bearing changes over the path; Mesh-Deck reports the initial bearing only.

### Channels and tactical messaging

Mesh-Deck distinguishes channel broadcasts from direct messages.

1. **Channel broadcast:** A message is sent to all listeners on the selected channel. The interactive `/send` command and plain input use primary channel 0.
2. **Direct message:** A message is addressed to one node. Meshtastic provides protocol-level encryption where the radio configuration supports it.

Broadcasts render as compact timeline entries. Direct messages render as high-visibility panels.

### Real-time notifications

When `notifications_enabled` is on, incoming broadcasts and direct messages raise a Textual toast.

- Broadcasts use the `information` severity with the channel and sender.
- Direct messages use the `warning` severity with the sender.

Disable notifications with `/settings notifications off` or the Settings dialog.

### Local node and message history

When `history_enabled` is on, Mesh-Deck writes append-only JSONL history under `~/.config/mesh-deck/history/`.

| File | Contents |
| :-- | :-- |
| `nodes.jsonl` | Materially changed node observations, including an `observed_at` timestamp. |
| `messages.jsonl` | Sent and received messages with direction and `recorded_at` timestamp. |

History is shared by CLI, TUI, and MCP usage. Disable it with `/settings history off`.

### Background streaming

Meshtastic PubSub callbacks can arrive on background threads. `RadioClient` updates the thread-safe NodeStore and invokes listeners; `TextualConsole` uses `call_from_thread()` to route UI work onto the Textual event loop.

This separation keeps input responsive while packets, telemetry, positions, connection changes, and messages arrive.

### Visual indicators

#### Signal-to-noise ratio

| SNR | Meaning |
| :-- | :-- |
| `>= +5 dB` | Strong signal. |
| `0 to +5 dB` | Good signal. |
| `-10 to 0 dB` | Marginal signal. |
| `< -10 dB` | Weak or critical signal. |

#### Battery and power

| State | Meaning |
| :-- | :-- |
| `> 70%` | Healthy battery. |
| `30–70%` | Medium battery. |
| `< 30%` | Low battery. |
| `> 100%` or high-voltage-only | External USB power or charging. |

#### Meshtastic roles

| Role | Meaning |
| :-- | :-- |
| `CLIENT` | Normal mesh endpoint. |
| `ROUTER` | Relay-oriented node. |
| `REPEATER` | Dedicated forwarding node. |
| `TRACKER` | Position-oriented mobile node. |
| `SENSOR` | Telemetry-oriented node. |

#### Hops

`0` means a direct node. Higher values indicate how many forwarding hops were needed to reach a node.

## 5. Troubleshooting

### `Permission denied` on `/dev/ttyACM*` or `/dev/ttyUSB*`

Your user is missing serial-device permission.

```bash
sudo usermod -a -G dialout $USER
newgrp dialout
```

Log out and back in if the new group does not apply immediately.

### `Access is denied`, `Device busy`, or `Port is busy`

Another process owns the serial port.

1. Close Meshtastic CLI, web flasher, serial monitor, Arduino IDE, or another Mesh-Deck instance.
2. On Linux, inspect ownership with `lsof /dev/ttyACM0` or `fuser /dev/ttyACM0`.
3. On Windows, close applications that may use the COM port and reconnect the USB cable if necessary.
4. Run `/scan` again and retry `/switch` or reconnect.

### A node has no GPS position or distance

The node may have no GPS receiver, may not have a current fix, may have disabled position sharing, or may report the unacquired `0,0` fix.

Mesh-Deck displays no distance or bearing until both the local node and the target node have valid non-zero coordinates.

### Messages are not received or the radio seems silent

Check that nodes share a compatible region, modem preset, channel configuration, and encryption material.

Run `/info` and `/channels` on the local radio, inspect SNR and hops with `/nodes`, and use `/trace <node>` for a specific reachable target.

### Neighbor tables are empty

`/neighbors` only displays NeighborInfo broadcasts received from other nodes.

Enable NeighborInfo on the relevant firmware configuration and allow enough time for the broadcast interval to elapse.

## References and license

- **Repository:** [github.com/raythekool/mesh-deck](https://github.com/raythekool/mesh-deck)
- **Supported scope:** [REQUIREMENTS.md](../REQUIREMENTS.md)
- **UI proposals:** [UI_DEVELOPMENT.md](UI_DEVELOPMENT.md)
- **License:** [MIT](../LICENSE)
