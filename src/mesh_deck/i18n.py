"""Internationalization (i18n) module for Mesh-Deck supporting IT and EN."""

from __future__ import annotations

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    # General / Banner
    "BANNER_TITLE": {
        "it": "📡 MESH-DECK // TACTICAL CONSOLE",
        "en": "📡 MESH-DECK // TACTICAL CONSOLE",
    },
    "LOCAL_NODE": {
        "it": "NODO LOCALE",
        "en": "LOCAL NODE",
    },
    "RADIO_PORT": {
        "it": "PORTA RADIO",
        "en": "RADIO PORT",
    },
    "REGION": {
        "it": "Regione",
        "en": "Region",
    },
    "PRESET": {
        "it": "Preset",
        "en": "Preset",
    },
    "CH_UTIL": {
        "it": "Ch. Util",
        "en": "Ch. Util",
    },
    "BATTERY": {
        "it": "Batteria",
        "en": "Battery",
    },
    "ACTIVE_CHANNELS": {
        "it": "CANALI ATTIVI",
        "en": "ACTIVE CHANNELS",
    },
    "COMMANDS_SHORTCUTS": {
        "it": "COMANDI: /help • /nodes • /view (interattiva) • /dm • /switch • /settings • /quit",
        "en": "COMMANDS: /help • /nodes • /view (interactive) • /dm • /switch • /settings • /quit",
    },
    "DISCONNECTED": {
        "it": "DISCONNESSO",
        "en": "DISCONNECTED",
    },

    # Tables headers
    "NODES_TABLE_TITLE": {
        "it": "📡 NODI NELLA MESH ({count} rilevati)",
        "en": "📡 MESH NODES ({count} detected)",
    },
    "LABEL_BEARING": {"it": "Direzione", "en": "Bearing"},
    "COL_NAME": {"it": "Nome Nodo", "en": "Node Name"},
    "COL_AKA": {"it": "AKA", "en": "AKA"},
    "COL_ID": {"it": "ID", "en": "ID"},
    "COL_HARDWARE": {"it": "Hardware", "en": "Hardware"},
    "COL_ROLE": {"it": "Ruolo", "en": "Role"},
    "COL_SNR": {"it": "SNR", "en": "SNR"},
    "COL_HOPS": {"it": "Hops", "en": "Hops"},
    "COL_BATTERY": {"it": "Batteria", "en": "Battery"},
    "COL_DISTANCE": {"it": "Distanza", "en": "Distance"},
    "COL_LAST_HEARD": {"it": "Ultimo Contatto", "en": "Last Heard"},
    "LOCAL_BADGE": {"it": "LOCALE", "en": "LOCAL"},

    # Commands / Help
    "HELP_TITLE": {
        "it": "⚡ MESH-DECK // COMANDI DISPONIBILI",
        "en": "⚡ MESH-DECK // AVAILABLE COMMANDS",
    },
    "COL_COMMAND": {"it": "Comando", "en": "Command"},
    "COL_ARGS": {"it": "Argomenti", "en": "Arguments"},
    "COL_DESCRIPTION": {"it": "Descrizione", "en": "Description"},

    "CMD_DESC_NODES": {
        "it": "Elenca i nodi visibili nella mesh con telemetria",
        "en": "List visible nodes in the mesh with telemetry",
    },
    "CMD_DESC_VIEW": {
        "it": "Apre la tabella a schermo intero con ordinamento al click del mouse su ogni colonna",
        "en": "Open full-screen table with mouse click column sorting",
    },
    "CMD_DESC_NODE": {
        "it": "Visualizza la scheda analitica dettagliata di un nodo",
        "en": "View detailed analytical dossier for a node",
    },
    "CMD_DESC_SEND": {
        "it": "Invia un messaggio broadcast sul canale primario (anche solo digitando il testo)",
        "en": "Send a broadcast message on primary channel (or just type text)",
    },
    "CMD_DESC_DM": {
        "it": "Invia un messaggio diretto privato a un nodo",
        "en": "Send a private direct message to a node",
    },
    "CMD_DESC_CHANNELS": {
        "it": "Mostra l'elenco dei canali radio configurati",
        "en": "Display configured radio channels",
    },
    "CMD_DESC_INFO": {
        "it": "Visualizza lo stato della radio, frequenze, modem e preset",
        "en": "Display radio status, frequencies, modem and preset",
    },
    "CMD_DESC_SWITCH": {
        "it": "Passa a un altro dispositivo LoRa USB connesso",
        "en": "Switch to another connected USB LoRa device",
    },
    "CMD_DESC_SCAN": {
        "it": "Rileva e mostra tutte le radio LoRa USB collegate al PC",
        "en": "Detect and show all USB LoRa radios connected to PC",
    },
    "CMD_DESC_SETTINGS": {
        "it": "Visualizza o modifica le impostazioni (lingua, tema, porta predefinita)",
        "en": "View or modify settings (language, theme, default port)",
    },
    "CMD_DESC_BANNER": {
        "it": "Ristampa il banner di stato Hermes",
        "en": "Reprint the Hermes status banner",
    },
    "CMD_DESC_CLEAR": {
        "it": "Pulisce la schermata del terminale",
        "en": "Clear the terminal screen",
    },
    "CMD_DESC_QUIT": {
        "it": "Chiude l'applicazione (73!)",
        "en": "Exit the application (73!)",
    },
    "CMD_DESC_RESTART": {
        "it": "Ricarica impostazioni e aggiorna la console",
        "en": "Reload settings and refresh the console",
    },

    # Settings strings
    "SETTINGS_TITLE": {
        "it": "⚙️ IMPOSTAZIONI MESH-DECK",
        "en": "⚙️ MESH-DECK SETTINGS",
    },
    "SETTING_KEY": {"it": "Parametro", "en": "Setting"},
    "SETTING_VAL": {"it": "Valore Attuale", "en": "Current Value"},
    "SETTING_OPTS": {"it": "Opzioni Disponibili", "en": "Available Options"},
    "APP_SUBTITLE": {"it": "Console comandi Meshtastic", "en": "Meshtastic command console"},
    "COMMAND_PLACEHOLDER": {
        "it": "mesh-deck [{name}] - messaggio o /help",
        "en": "mesh-deck [{name}] - message or /help",
    },
    "SETTINGS_DIALOG_TITLE": {"it": "Impostazioni Mesh-Deck", "en": "Mesh-Deck settings"},
    "SETTINGS_LANGUAGE": {"it": "Lingua", "en": "Language"},
    "SETTINGS_THEME": {"it": "Tema", "en": "Theme"},
    "SETTINGS_SORT": {"it": "Ordinamento nodi", "en": "Node sorting"},
    "SETTINGS_PORT": {"it": "Porta predefinita", "en": "Default port"},
    "SETTINGS_AUTO_PORT": {"it": "Rilevamento automatico", "en": "Automatic detection"},
    "SETTINGS_CANCEL": {"it": "Annulla", "en": "Cancel"},
    "SETTINGS_SAVE": {"it": "Salva", "en": "Save"},
    "SETTINGS_NOTIFICATIONS": {"it": "Notifiche messaggi", "en": "Message notifications"},
    "SETTINGS_HISTORY": {"it": "Storico locale su file", "en": "Local file history"},
    "SETTINGS_ON": {"it": "Attive", "en": "On"},
    "SETTINGS_OFF": {"it": "Disattivate", "en": "Off"},
    "SIDEBAR_TITLE": {"it": "📡 NODI", "en": "📡 NODES"},
    "SIDEBAR_EMPTY": {"it": "Nessun nodo rilevato", "en": "No nodes detected"},
    "SIDEBAR_TOGGLE": {"it": "Mostra/nascondi barra laterale", "en": "Toggle sidebar"},
    "CMD_DESC_CHAT": {
        "it": "Apre la chat interattiva dei canali e dei messaggi diretti (click del mouse)",
        "en": "Open the interactive channel and direct-message chat viewer (mouse click)",
    },

    # Shared formatters (theme.py)
    "TIME_AGO_NEVER": {"it": "mai", "en": "never"},
    "TIME_AGO_SUFFIX_SEC": {"it": "s fa", "en": "s ago"},
    "TIME_AGO_SUFFIX_MIN": {"it": "m fa", "en": "m ago"},
    "TIME_AGO_SUFFIX_HOUR": {"it": "h fa", "en": "h ago"},
    "TIME_AGO_SUFFIX_DAY": {"it": "d fa", "en": "d ago"},
    "HOPS_DIRECT": {"it": "Diretto", "en": "Direct"},

    # Node table (tables.py: render_nodes_table)
    "NODE_UNKNOWN_NAME": {"it": "Sconosciuto", "en": "Unknown"},

    # Node detail dossier (tables.py: render_node_detail)
    "NODE_DETAIL_TITLE": {
        "it": "◈ SCHEDA ANALITICA // {name} ({id})",
        "en": "◈ NODE DOSSIER // {name} ({id})",
    },
    "NODE_DETAIL_SUBTITLE": {"it": "Dossier Nodo Meshtastic", "en": "Meshtastic Node Dossier"},
    "SECTION_IDENTITY": {"it": "◈ IDENTITÀ & HARDWARE", "en": "◈ IDENTITY & HARDWARE"},
    "SECTION_RADIO": {"it": "⚡ TELEMETRIA RADIO & PROPAGAZIONE", "en": "⚡ RADIO TELEMETRY & PROPAGATION"},
    "SECTION_POWER": {"it": "🔋 ENERGIA & SENSORI AMBIENTALI", "en": "🔋 POWER & ENVIRONMENTAL SENSORS"},
    "SECTION_GEO": {"it": "📍 POSIZIONE GEOGRAFICA", "en": "📍 GEOGRAPHIC POSITION"},
    "LABEL_FULL_NAME": {"it": "Nome Completo", "en": "Full Name"},
    "LABEL_AKA": {"it": "Alias (AKA)", "en": "Alias (AKA)"},
    "LABEL_NODE_ID": {"it": "Node ID", "en": "Node ID"},
    "LABEL_DEC": {"it": "(Dec: {num})", "en": "(Dec: {num})"},
    "LABEL_HW_MODEL": {"it": "Modello HW", "en": "HW Model"},
    "LABEL_DEVICE_ROLE": {"it": "Ruolo Dispositivo", "en": "Device Role"},
    "LABEL_RADIO_LICENSE": {"it": "Licenza Radio", "en": "Radio License"},
    "LICENSED_YES": {"it": "Sì (Amateur Radio)", "en": "Yes (Amateur Radio)"},
    "LICENSED_NO": {"it": "No / ISM", "en": "No / ISM"},
    "LABEL_SNR": {"it": "Segnale (SNR)", "en": "Signal (SNR)"},
    "LABEL_HOPS_AWAY": {"it": "Hops Away", "en": "Hops Away"},
    "LABEL_LAST_HEARD": {"it": "Ultimo Contatto", "en": "Last Heard"},
    "LABEL_CH_UTIL": {"it": "Ch. Utilization", "en": "Ch. Utilization"},
    "LABEL_AIR_UTIL": {"it": "Air Util TX", "en": "Air Util TX"},
    "LABEL_MODEM_PRESET": {"it": "Preset Modem", "en": "Modem Preset"},
    "LABEL_BATTERY_FULL": {"it": "Batteria", "en": "Battery"},
    "LABEL_CELL_VOLTAGE": {"it": "Tensione Cella", "en": "Cell Voltage"},
    "LABEL_TEMPERATURE": {"it": "Temperatura", "en": "Temperature"},
    "LABEL_HUMIDITY": {"it": "Umidità Relativa", "en": "Relative Humidity"},
    "LABEL_PRESSURE": {"it": "Pressione", "en": "Pressure"},
    "LABEL_GPS_COORDS": {"it": "Coordinate GPS", "en": "GPS Coordinates"},
    "LABEL_ALTITUDE": {"it": "Altitudine", "en": "Altitude"},
    "ALTITUDE_SUFFIX": {"it": "m s.l.m.", "en": "m a.s.l."},
    "LABEL_DISTANCE_EST": {"it": "Distanza Stima", "en": "Estimated Distance"},
    "LABEL_OSM": {"it": "OpenStreetMap", "en": "OpenStreetMap"},
    "OSM_LINK_TEXT": {"it": "Apri mappa ↗", "en": "Open map ↗"},
    "NO_COORDS": {"it": "Non disponibili / GPS assente", "en": "Not available / No GPS"},
    "NO_COORDS_MAP": {
        "it": "Nessuna coordinata per il rendering mappa",
        "en": "No coordinates available for map rendering",
    },
    "LABEL_PUBKEY": {"it": "Chiave Pubblica PKI", "en": "PKI Public Key"},
    "PUBKEY_NONE": {
        "it": "Non trasmessa o crittografia standard",
        "en": "Not broadcast or standard encryption",
    },

    # Messages (tables.py: render_message)
    "MSG_SENDER_UNKNOWN": {"it": "Sconosciuto", "en": "Unknown"},
    "MSG_DM_TITLE": {
        "it": "🔒 MESSAGGIO DIRETTO PRIVATO // DM",
        "en": "🔒 PRIVATE DIRECT MESSAGE // DM",
    },

    # Status banner (banner.py: render_banner)
    "BANNER_CONNECTING": {"it": "IN CONNESSIONE / RICERCA...", "en": "CONNECTING / SEARCHING..."},
    "BANNER_UNKNOWN": {"it": "Sconosciuto", "en": "Unknown"},
    "BANNER_ALIAS": {"it": "Alias / AKA", "en": "Alias / AKA"},
    "BANNER_HW_LABEL": {"it": "HW", "en": "HW"},
    "BANNER_SUBTITLE": {"it": "Interfaccia Hermes Meshtastic", "en": "Hermes Meshtastic Interface"},

    # Command dispatcher (commands/dispatcher.py)
    "WARN_INVALID_SORT": {
        "it": "Opzione non valida: {opt}. Uso sort predefinito: last_heard.",
        "en": "Invalid option: {opt}. Using default sort: last_heard.",
    },
    "NODES_EMPTY": {"it": "Nessun nodo trovato nel NodeDB corrente.", "en": "No nodes found in the current NodeDB."},
    "NODES_HINT": {
        "it": "💡 Suggerimento: usa {cmd} per aprire la tabella interattiva con ordinamento al click del mouse su ogni colonna.",
        "en": "💡 Tip: use {cmd} to open the interactive table with mouse-click column sorting.",
    },
    "USAGE_NODE": {"it": "Uso: /node <id|aka|nome>", "en": "Usage: /node <id|aka|name>"},
    "NODE_NOT_FOUND": {"it": "Nodo non trovato: {query}", "en": "Node not found: {query}"},
    "USAGE_SEND": {"it": "Uso: /send <testo del messaggio>", "en": "Usage: /send <message text>"},
    "SEND_SUCCESS": {"it": "📢 Inviato (Broadcast #0): {text}", "en": "📢 Sent (Broadcast #0): {text}"},
    "SEND_ERROR": {"it": "Errore durante l'invio del messaggio broadcast.", "en": "Error sending broadcast message."},
    "COMMAND_FAILED": {
        "it": "Comando non riuscito: {error}",
        "en": "Command failed: {error}",
    },
    "CONN_LOST": {
        "it": "⚠ Connessione persa su {port}. Riconnessione automatica in corso...",
        "en": "⚠ Connection lost on {port}. Reconnecting automatically...",
    },
    "CONN_RETRYING": {
        "it": "↻ Tentativo di riconnessione #{attempt} su {port}...",
        "en": "↻ Reconnection attempt #{attempt} on {port}...",
    },
    "CONN_RESTORED": {
        "it": "✓ Connessione ristabilita su {port}.",
        "en": "✓ Connection restored on {port}.",
    },
    "CMD_DESC_NEIGHBORS": {
        "it": "Mostra le tabelle dei vicini (NeighborInfo) ricevute",
        "en": "Show received neighbor tables (NeighborInfo)",
    },
    "CMD_DESC_MESH": {
        "it": "Riepilogo topologia della mesh",
        "en": "Mesh topology summary",
    },
    "CMD_DESC_TOPOLOGY": {
        "it": "Esplora i link NeighborInfo della mesh",
        "en": "Explore mesh NeighborInfo links",
    },
    "CMD_DESC_TRACE": {
        "it": "Traceroute verso un nodo: percorso a salti",
        "en": "Traceroute to a node: hop path",
    },
    "CMD_DESC_LOGS": {
        "it": "Mostra log diagnostici applicazione e dispositivo",
        "en": "Show application and device diagnostic logs",
    },
    "CMD_DESC_HISTORY": {
        "it": "Mostra lo storico telemetrico locale di un nodo",
        "en": "Show a node's local telemetry history",
    },
    "NEIGHBORS_EMPTY": {
        "it": "Nessuna informazione sui vicini ricevuta finora. I nodi la trasmettono periodicamente se NeighborInfo è abilitato.",
        "en": "No neighbor information received yet. Nodes broadcast it periodically when NeighborInfo is enabled.",
    },
    "NEIGHBORS_TABLE_TITLE": {
        "it": "🛰 VICINI DI {node}",
        "en": "🛰 NEIGHBORS OF {node}",
    },
    "COL_NEIGHBOR": {"it": "Nodo vicino", "en": "Neighbor node"},
    "COL_NEIGHBOR_OF": {"it": "Sentito da", "en": "Heard by"},
    "MESH_TABLE_TITLE": {
        "it": "🕸 TOPOLOGIA MESH ({nodes} nodi, {reports} tabelle vicini)",
        "en": "🕸 MESH TOPOLOGY ({nodes} nodes, {reports} neighbor tables)",
    },
    "MESH_NO_NEIGHBOR_DATA": {
        "it": "Nessuna tabella NeighborInfo ricevuta: la colonna \"Sentito da\" resta vuota finché i nodi non la trasmettono.",
        "en": "No NeighborInfo tables received: the \"Heard by\" column stays empty until nodes broadcast one.",
    },
    "USAGE_TRACE": {"it": "Uso: /trace <id|aka>", "en": "Usage: /trace <id|aka>"},
    "TRACE_IN_PROGRESS": {
        "it": "Traceroute verso {name} in corso, attendo la risposta...",
        "en": "Tracing route to {name}, waiting for the reply...",
    },
    "TRACE_TIMEOUT": {
        "it": "Nessuna risposta al traceroute verso {name}.",
        "en": "No traceroute reply from {name}.",
    },
    "TRACE_TITLE": {
        "it": "◈ TRACEROUTE // {name} ({hops} hop)",
        "en": "◈ TRACEROUTE // {name} ({hops} hops)",
    },
    "TRACE_SNR_TOWARDS": {"it": "SNR andata", "en": "SNR towards"},
    "TRACE_ROUTE_BACK": {"it": "Percorso di ritorno", "en": "Return path"},
    "USAGE_DM": {"it": "Uso: /dm <target_id_o_aka> <testo>", "en": "Usage: /dm <target_id_or_aka> <text>"},
    "DM_SUCCESS": {"it": "🔒 DM inviato a {name}: {text}", "en": "🔒 DM sent to {name}: {text}"},
    "DM_ERROR": {"it": "Errore durante l'invio del DM a {name}.", "en": "Error sending DM to {name}."},
    "CHANNELS_EMPTY": {
        "it": "Nessun canale disponibile o radio non connessa.",
        "en": "No channels available or radio not connected.",
    },
    "CHANNELS_TABLE_TITLE": {"it": "📡 CANALI RADIO CONFIGURATI", "en": "📡 CONFIGURED RADIO CHANNELS"},
    "COL_CH_INDEX": {"it": "Index", "en": "Index"},
    "COL_CH_NAME": {"it": "Nome Canale", "en": "Channel Name"},
    "COL_CH_ROLE": {"it": "Ruolo / Tipo", "en": "Role / Type"},
    "COL_CH_UPDOWN": {"it": "Uplink / Downlink", "en": "Uplink / Downlink"},
    "COL_CH_PSK": {"it": "Crittografia (PSK)", "en": "Encryption (PSK)"},
    "CH_PRIMARY_DEFAULT": {"it": "(Primary)", "en": "(Primary)"},
    "PSK_ACTIVE": {"it": "Attiva", "en": "Active"},
    "PSK_DEFAULT": {"it": "Predefinita", "en": "Default"},
    "INFO_EMPTY": {"it": "Nessuna informazione radio disponibile.", "en": "No radio information available."},
    "INFO_TABLE_TITLE": {"it": "📻 STATO HARDWARE & PARAMETRI RADIO", "en": "📻 HARDWARE STATUS & RADIO PARAMETERS"},
    "ROW_SERIAL_PORT": {"it": "Porta Seriale", "en": "Serial Port"},
    "ROW_CONN_STATUS": {"it": "Stato Connessione", "en": "Connection Status"},
    "CONN_CONNECTED": {"it": "Connesso", "en": "Connected"},
    "CONN_DISCONNECTED": {"it": "Disconnesso", "en": "Disconnected"},
    "ROW_LOCAL_NODE": {"it": "Nodo Locale", "en": "Local Node"},
    "ROW_HW_MODEL": {"it": "Modello Hardware", "en": "Hardware Model"},
    "ROW_ROLE": {"it": "Ruolo", "en": "Role"},
    "ROW_GPS": {"it": "Coordinate GPS", "en": "GPS Coordinates"},
    "ROW_RF_REGION": {"it": "Regione RF", "en": "RF Region"},
    "ROW_MODEM_PRESET": {"it": "Modem Preset", "en": "Modem Preset"},
    "ROW_FIRMWARE": {"it": "Firmware Version", "en": "Firmware Version"},
    "ROW_ACTIVE_CHANNELS": {"it": "Canali Attivi", "en": "Active Channels"},
    "COL_PARAM": {"it": "Parametro", "en": "Setting"},
    "COL_VALUE": {"it": "Valore", "en": "Value"},
    "SCAN_EMPTY": {
        "it": "Nessun dispositivo LoRa rilevato sulle porte USB.",
        "en": "No LoRa device detected on USB ports.",
    },
    "SCAN_TABLE_TITLE": {"it": "🔍 DISPOSITIVI LORA / MESHTASTIC RILEVATI", "en": "🔍 DETECTED LORA / MESHTASTIC DEVICES"},
    "COL_PORT": {"it": "Porta", "en": "Port"},
    "COL_HW_DETECTED": {"it": "Hardware Rilevato", "en": "Detected Hardware"},
    "COL_SYS_DESC": {"it": "Descrizione Sistema", "en": "System Description"},
    "COL_CURRENT_STATUS": {"it": "Stato Attuale", "en": "Current Status"},
    "STATUS_ACTIVE": {"it": "★ ATTIVO", "en": "★ ACTIVE"},
    "STATUS_AVAILABLE": {"it": "Disponibile", "en": "Available"},
    "SWITCH_EMPTY": {
        "it": "Nessun dispositivo disponibile per lo switch.",
        "en": "No device available to switch to.",
    },
    "SWITCH_NO_ALT": {"it": "Nessun'altra porta alternativa rilevata.", "en": "No alternative port detected."},
    "SWITCH_INVALID_INDEX": {"it": "Indice non valido. Usa 1..{max}", "en": "Invalid index. Use 1..{max}"},
    "SWITCH_IN_PROGRESS": {"it": "Passaggio in corso alla porta: {port}...", "en": "Switching to port: {port}..."},
    "SWITCH_SUCCESS": {
        "it": "✓ Connesso con successo a: {port} ({name})",
        "en": "✓ Successfully connected to: {port} ({name})",
    },
    "SWITCH_FAILURE": {"it": "Impossibile connettersi alla porta {port}.", "en": "Could not connect to port {port}."},
    "VIEW_LAUNCH": {
        "it": "Avvio tabella interattiva... (Fai click sulle intestazioni per ordinare, premi 'q' o 'Esc' per tornare al prompt)",
        "en": "Launching interactive table... (Click column headers to sort, press 'q' or 'Esc' to return to prompt)",
    },
    "CHAT_LAUNCH": {
        "it": "Avvio chat canali interattiva... (premi 'q' o 'Esc' per tornare al prompt)",
        "en": "Launching interactive channel chat... (press 'q' or 'Esc' to return to prompt)",
    },
    "SETTINGS_ROW_LANG": {"it": "Lingua (lang)", "en": "Language (lang)"},
    "SETTINGS_ROW_THEME": {"it": "Tema (theme)", "en": "Theme (theme)"},
    "SETTINGS_ROW_PORT": {"it": "Porta predefinita (port)", "en": "Default port (port)"},
    "SETTINGS_AUTODETECT": {"it": "(Auto-detect)", "en": "(Auto-detect)"},
    "SETTINGS_ROW_SORT": {"it": "Ordinamento (sort)", "en": "Sorting (sort)"},
    "STATE_ON": {"it": "Attivo", "en": "On"},
    "STATE_OFF": {"it": "Disattivato", "en": "Off"},
    "SETTINGS_LANG_SET": {"it": "✓ Lingua impostata su: {value}", "en": "✓ Language set to: {value}"},
    "SETTINGS_LANG_INVALID": {
        "it": "Lingua non supportata. Usa 'it' o 'en'.",
        "en": "Unsupported language. Use 'it' or 'en'.",
    },
    "SETTINGS_THEME_SET": {"it": "✓ Tema impostato su: {theme}", "en": "✓ Theme set to: {theme}"},
    "SETTINGS_THEME_INVALID": {
        "it": "Tema non valido. Disponibili: {options}.",
        "en": "Invalid theme. Available: {options}.",
    },
    "SETTINGS_SORT_SET": {"it": "✓ Ordinamento predefinito impostato su: {sort}", "en": "✓ Default sort set to: {sort}"},
    "SETTINGS_SORT_INVALID": {
        "it": "Ordinamento non valido. Usa 'last_heard', 'snr', 'hops', o 'name'.",
        "en": "Invalid sort. Use 'last_heard', 'snr', 'hops', or 'name'.",
    },
    "SETTINGS_PORT_SET": {"it": "✓ Porta predefinita impostata su: {port}", "en": "✓ Default port set to: {port}"},
    "STATE_ENABLED_F": {"it": "attivate", "en": "enabled"},
    "STATE_DISABLED_F": {"it": "disattivate", "en": "disabled"},
    "STATE_ENABLED_M": {"it": "attivato", "en": "enabled"},
    "STATE_DISABLED_M": {"it": "disattivato", "en": "disabled"},
    "SETTINGS_NOTIF_SET": {"it": "✓ Notifiche messaggi {state}.", "en": "✓ Message notifications {state}."},
    "SETTINGS_HISTORY_SET": {
        "it": "✓ Storico locale su file {state}. Effettivo dal prossimo avvio.",
        "en": "✓ Local file history {state}. Effective on next restart.",
    },
    "SETTINGS_INVALID_VALUE": {"it": "Valore non valido. Usa 'on' o 'off'.", "en": "Invalid value. Use 'on' or 'off'."},
    "SETTINGS_USAGE": {
        "it": "Uso: /settings [lang <it|en> | theme <nome> | sort <criterio> | port <porta> | notifications <on|off> | history <on|off>]",
        "en": "Usage: /settings [lang <it|en> | theme <name> | sort <criteria> | port <port> | notifications <on|off> | history <on|off>]",
    },
    "QUIT_MESSAGE": {
        "it": "Chiusura connessione radio e uscita da Mesh-Deck. 73!",
        "en": "Closing radio connection and exiting Mesh-Deck. 73!",
    },

    # Interactive node explorer screen (ui/interactive_table.py)
    "VIEW_TITLE": {"it": "📡 MESH-DECK // ESPLORATORE NODI INTERATTIVO", "en": "📡 MESH-DECK // INTERACTIVE NODE EXPLORER"},
    "VIEW_SUBTITLE": {
        "it": "Fai click su una colonna per ordinare • Premi 'q' o 'Esc' per tornare al prompt",
        "en": "Click a column to sort • Press 'q' or 'Esc' to return to prompt",
    },
    "VIEW_SORTED_BY": {
        "it": "Ordinato per: {column} {arrow} • Click su un header per cambiare ordinamento",
        "en": "Sorted by: {column} {arrow} • Click a header to change sorting",
    },
    "VIEW_NODE_DETAIL_TITLE": {
        "it": "◈ DETTAGLIO NODO // {name}",
        "en": "◈ NODE DETAIL // {name}",
    },
    "VIEW_DETAIL_HINT": {
        "it": "Invio: dettagli • v: modalità visualizzazione • /: filtra",
        "en": "Enter: details • v: view mode • /: filter",
    },
    "VIEW_MODE_LABEL": {"it": "{mode} ({effective})", "en": "{mode} ({effective})"},
    "VIEW_MODE_AUTO": {"it": "Auto", "en": "Auto"},
    "VIEW_MODE_FULL": {"it": "Completa", "en": "Full"},
    "VIEW_MODE_COMPACT": {"it": "Compatta", "en": "Compact"},
    "RADIO_STATUS_CONNECTED": {
        "it": "Connesso · {node} · {port}",
        "en": "Connected · {node} · {port}",
    },
    "RADIO_STATUS_RECONNECTING": {
        "it": "Riconnessione · {port} · tentativo {attempt}",
        "en": "Reconnecting · {port} · attempt {attempt}",
    },
    "RADIO_STATUS_DISCONNECTED": {"it": "Radio disconnessa", "en": "Radio disconnected"},
    "RADIO_STATUS_NO_PORT": {"it": "nessuna porta", "en": "no port"},
    "COMMAND_BUSY": {
        "it": "Un comando è già in esecuzione.",
        "en": "A command is already running.",
    },
    "COMMAND_PROGRESS_RUNNING": {
        "it": "⏳ In esecuzione: {command}",
        "en": "⏳ Running: {command}",
    },
    "COMMAND_PROGRESS_CANCELLABLE": {
        "it": "⏳ In esecuzione: {command} · Esc per annullare",
        "en": "⏳ Running: {command} · Esc to cancel",
    },
    "COMMAND_CANCELLING": {
        "it": "↻ Annullamento richiesto: {command}",
        "en": "↻ Cancellation requested: {command}",
    },
    "TRACE_CANCELLED": {
        "it": "Traceroute verso {name} annullato.",
        "en": "Traceroute to {name} cancelled.",
    },
    "HISTORY_TITLE": {"it": "📈 STORICO NODO // {name}", "en": "📈 NODE HISTORY // {name}"},
    "HISTORY_SUBTITLE": {"it": "Snapshot telemetrici locali su file", "en": "Local telemetry snapshots from file"},
    "HISTORY_RANGE_LABEL": {"it": "Intervallo", "en": "Range"},
    "HISTORY_RANGE_6H": {"it": "Ultime 6 ore", "en": "Last 6 hours"},
    "HISTORY_RANGE_24H": {"it": "Ultime 24 ore", "en": "Last 24 hours"},
    "HISTORY_RANGE_7D": {"it": "Ultimi 7 giorni", "en": "Last 7 days"},
    "HISTORY_RANGE_ALL": {"it": "Tutto", "en": "All time"},
    "HISTORY_SUMMARY": {"it": "{count} snapshot per {node}", "en": "{count} snapshots for {node}"},
    "HISTORY_EMPTY": {"it": "Nessuno snapshot locale disponibile per {node}.", "en": "No local snapshots are available for {node}."},
    "HISTORY_METRIC_BATTERY": {"it": "BATTERIA", "en": "BATTERY"},
    "HISTORY_METRIC_SNR": {"it": "SNR", "en": "SNR"},
    "HISTORY_METRIC_TEMPERATURE": {"it": "TEMPERATURA", "en": "TEMPERATURE"},
    "HISTORY_METRIC_CHANNEL_UTIL": {"it": "UTILIZZO CANALE", "en": "CHANNEL UTILIZATION"},
    "HISTORY_METRIC_EMPTY": {"it": "Nessun campione", "en": "No samples"},
    "HISTORY_DISABLED": {"it": "Lo storico locale è disattivato. Attivalo con /settings history on.", "en": "Local history is disabled. Enable it with /settings history on."},
    "HISTORY_TUI_ONLY": {"it": "{count} snapshot disponibili. Apri /history nella console Textual per visualizzarli.", "en": "{count} snapshots available. Open /history in the Textual console to view them."},
    "USAGE_HISTORY": {"it": "Uso: /history <id|aka|nome>", "en": "Usage: /history <id|aka|name>"},
    "BINDING_HISTORY": {"it": "Storico", "en": "History"},
    "BINDING_CLOSE": {"it": "Chiudi / Esci", "en": "Close / Exit"},
    "BINDING_BACK": {"it": "Torna al prompt", "en": "Back to prompt"},
    "BINDING_REFRESH": {"it": "Aggiorna", "en": "Refresh"},
    "BINDING_FILTER": {"it": "Cerca / Filtra", "en": "Search / Filter"},
    "BINDING_VIEW_MODE": {"it": "Vista", "en": "View"},
    "FILTER_LABEL": {"it": "🔍 Filtra:", "en": "🔍 Filter:"},
    "FILTER_PLACEHOLDER": {"it": "Cerca per nome, AKA, hardware o ID...", "en": "Search by name, AKA, hardware or ID..."},
    "COL_NODE_NAME": {"it": "Nome Nodo", "en": "Node Name"},
    "LOCAL_SUFFIX": {"it": "LOCALE", "en": "LOCAL"},

    # Channel chat screen (ui/channel_chat.py)
    "CHAT_TITLE": {"it": "💬 MESH-DECK // CHAT CANALI", "en": "💬 MESH-DECK // CHANNEL CHAT"},
    "CHAT_SUBTITLE": {
        "it": "Fai click su un canale per aprirlo • Invia dal campo in basso • 'q'/'Esc' per uscire",
        "en": "Click a channel to open it • Send from the field below • 'q'/'Esc' to exit",
    },
    "BINDING_UPDATE_CHANNELS": {"it": "Aggiorna canali", "en": "Refresh channels"},
    "CHAT_DM_SECTION": {"it": "MESSAGGI DIRETTI", "en": "DIRECT MESSAGES"},
    "CHAT_CHANNEL_FALLBACK": {"it": "Canale {index}", "en": "Channel {index}"},
    "CHAT_INPUT_PLACEHOLDER": {"it": "Scrivi un messaggio e premi invio...", "en": "Type a message and press enter..."},
    "CHAT_DM_HINT": {
        "it": "Risposta diretta a {name} ({peer_id}).",
        "en": "Direct reply to {name} ({peer_id}).",
    },
    "CHAT_DM_REPLY_PLACEHOLDER": {"it": "Rispondi a {name}...", "en": "Reply to {name}..."},
    "CHAT_DM_SUBTITLE": {"it": "DM con {name}", "en": "DM with {name}"},
    "LOGS_TITLE": {"it": "📋 MESH-DECK // LOG DIAGNOSTICI", "en": "📋 MESH-DECK // DIAGNOSTIC LOGS"},
    "LOGS_SUBTITLE": {"it": "Log applicazione e dispositivo in memoria", "en": "In-memory application and device logs"},
    "LOGS_SOURCE_LABEL": {"it": "Sorgente", "en": "Source"},
    "LOGS_SOURCE_ALL": {"it": "Tutti", "en": "All"},
    "LOGS_SOURCE_APP": {"it": "Applicazione", "en": "Application"},
    "LOGS_SOURCE_DEVICE": {"it": "Dispositivo", "en": "Device"},
    "LOGS_LEVEL_LABEL": {"it": "Livello", "en": "Level"},
    "LOGS_LEVEL_DEBUG": {"it": "Debug", "en": "Debug"},
    "LOGS_LEVEL_INFO": {"it": "Info", "en": "Info"},
    "LOGS_LEVEL_WARNING": {"it": "Warning", "en": "Warning"},
    "LOGS_LEVEL_ERROR": {"it": "Errore", "en": "Error"},
    "LOGS_QUERY_PLACEHOLDER": {"it": "Cerca testo, porta o comando...", "en": "Search text, port, or command..."},
    "LOGS_COL_TIME": {"it": "Ora", "en": "Time"},
    "LOGS_COL_SOURCE": {"it": "Sorgente", "en": "Source"},
    "LOGS_COL_LEVEL": {"it": "Livello", "en": "Level"},
    "LOGS_COL_MESSAGE": {"it": "Messaggio", "en": "Message"},
    "LOGS_STATUS_LIVE": {"it": "{count} righe · live", "en": "{count} entries · live"},
    "LOGS_STATUS_PAUSED": {"it": "{count} righe · in pausa · {pending} nuove", "en": "{count} entries · paused · {pending} new"},
    "LOGS_COPIED": {"it": "Riga copiata negli appunti.", "en": "Log line copied to clipboard."},
    "LOGS_NOTHING_SELECTED": {"it": "Seleziona una riga da copiare.", "en": "Select a log row to copy."},
    "LOGS_EXPORTED": {"it": "Log esportato in {path}", "en": "Log exported to {path}"},
    "LOGS_EXPORT_FAILED": {"it": "Impossibile esportare il log: {error}", "en": "Could not export log: {error}"},
    "LOGS_TUI_ONLY": {"it": "/logs è disponibile nella console Textual.", "en": "/logs is available in the Textual console."},
    "BINDING_LOG_PAUSE": {"it": "Pausa", "en": "Pause"},
    "BINDING_LOG_COPY": {"it": "Copia", "en": "Copy"},
    "BINDING_LOG_EXPORT": {"it": "Esporta", "en": "Export"},
    "TOPOLOGY_TITLE": {"it": "🕸 MESH-DECK // TOPOLOGIA", "en": "🕸 MESH-DECK // TOPOLOGY"},
    "TOPOLOGY_SUBTITLE": {"it": "Link NeighborInfo ricevuti dalla mesh", "en": "NeighborInfo links received from the mesh"},
    "TOPOLOGY_FILTER_PLACEHOLDER": {"it": "Cerca reporter, vicino o ID...", "en": "Search reporter, neighbor, or ID..."},
    "TOPOLOGY_COL_REPORTER": {"it": "Reporter", "en": "Reporter"},
    "TOPOLOGY_COL_NEIGHBOR": {"it": "Nodo vicino", "en": "Neighbor"},
    "TOPOLOGY_QUALITY_TITLE": {"it": "QUALITÀ DATI", "en": "DATA QUALITY"},
    "TOPOLOGY_QUALITY_REPORTS": {"it": "{count} tabelle NeighborInfo ricevute", "en": "{count} NeighborInfo reports received"},
    "TOPOLOGY_QUALITY_NEWEST": {"it": "Report più recente: {age}", "en": "Newest report: {age}"},
    "TOPOLOGY_QUALITY_HINT": {"it": "Un link assente significa dati sconosciuti, non una disconnessione.", "en": "A missing link means unknown data, not a disconnection."},
    "TOPOLOGY_EMPTY_HINT": {"it": "Nessun nodo ha ancora trasmesso NeighborInfo. Abilita il modulo sul firmware e attendi il suo intervallo di broadcast.", "en": "No node has broadcast NeighborInfo yet. Enable the firmware module and wait for its broadcast interval."},
    "CHAT_SEND_FAILED_TITLE": {"it": "Invio fallito", "en": "Send failed"},

    # Device selector startup screen (ui/device_selector.py)
    "DEVICE_SELECTOR_SUBTITLE": {"it": "Seleziona una periferica Meshtastic", "en": "Select a Meshtastic device"},
    "DEVICE_SELECTOR_HEADING": {"it": "Periferiche Meshtastic rilevate", "en": "Detected Meshtastic devices"},
    "DEVICE_SELECTOR_HELP": {
        "it": "Usa freccia Su/Giù e Invio per selezionare",
        "en": "Use Up/Down arrows and Enter to select",
    },
    "DEVICE_SELECTOR_ACTIVE": {"it": "ATTIVA", "en": "ACTIVE"},
    "DEVICE_SELECTOR_PREFERRED": {"it": "PREFERITA", "en": "PREFERRED"},
    "DEVICE_SELECTOR_RETRY": {"it": "RIPROVA", "en": "RETRY"},
    "DEVICE_SELECTOR_FAILURE": {
        "it": "Ultima connessione a {port} non riuscita: {reason}",
        "en": "Last connection to {port} failed: {reason}",
    },
    "DEVICE_SELECTOR_FAILURE_UNKNOWN": {"it": "errore non specificato", "en": "unspecified error"},
    "DEVICE_SELECTOR_EMPTY_HELP": {
        "it": "Nessuna radio Meshtastic rilevata. Verifica cavo USB, alimentazione, driver seriale e che nessun'altra app stia usando la porta; poi premi r per aggiornare.",
        "en": "No Meshtastic radio was detected. Check the USB cable, power, serial driver, and that no other app owns the port; then press r to rescan.",
    },
    "BINDING_CANCEL": {"it": "Annulla", "en": "Cancel"},
    "BINDING_RETRY": {"it": "Riprova", "en": "Retry"},
    "CONNECTION_HEADING": {"it": "Connessione alla periferica", "en": "Connecting to device"},
    "CONNECTION_STATUS": {
        "it": "Apertura di {port} e sincronizzazione del NodeDB...",
        "en": "Opening {port} and syncing the NodeDB...",
    },
    "CONNECTION_BACK": {"it": "Torna all'elenco", "en": "Back to list"},
    "CONNECTION_FAILED": {"it": "Connessione a {port} non riuscita.", "en": "Failed to connect to {port}."},

    # Command sub-argument autocomplete (e.g. /settings <sub>, /switch <port>)
    "COMPLETE_PORT_DESC": {"it": "Porta seriale USB", "en": "USB serial port"},
    "COMPLETE_LANG_DESC": {"it": "Imposta lingua (it, en)", "en": "Set language (it, en)"},
    "COMPLETE_THEME_DESC": {
        "it": "Imposta tema (cyberpunk, midnight, nord, ember)",
        "en": "Set theme (cyberpunk, midnight, nord, ember)",
    },
    "THEME_DESC_CYBERPUNK": {
        "it": "Neon ciano/verde su nero profondo",
        "en": "Neon cyan/green on deep black",
    },
    "THEME_DESC_MIDNIGHT": {
        "it": "Indaco notturno, blu e viola tenui",
        "en": "Night indigo with soft blues and violets",
    },
    "THEME_DESC_NORD": {
        "it": "Palette artica fredda, a basso affaticamento",
        "en": "Cool arctic palette, low eye strain",
    },
    "THEME_DESC_EMBER": {
        "it": "Ambra e corallo caldi su carbone",
        "en": "Warm amber and coral on charcoal",
    },
    "COMPLETE_SORT_DESC": {"it": "Imposta ordinamento predefinito", "en": "Set default sorting"},
    "COMPLETE_PORT_SUB_DESC": {"it": "Imposta porta seriale predefinita", "en": "Set default serial port"},

    # Sidebar sort/filter controls (ui/repl.py)
    "SIDEBAR_SORT_LAST_HEARD": {"it": "Recenti", "en": "Recent"},
    "SIDEBAR_SORT_SNR": {"it": "Segnale", "en": "Signal"},
    "SIDEBAR_SORT_HOPS": {"it": "Hop", "en": "Hops"},
    "SIDEBAR_SORT_NAME": {"it": "Nome", "en": "Name"},
    "SIDEBAR_FILTER_ALL": {"it": "Tutti", "en": "All"},
    "SIDEBAR_FILTER_ACTIVE": {"it": "Attivi", "en": "Active"},
    "SIDEBAR_FILTER_FAVORITES": {"it": "Preferiti", "en": "Favorites"},
    "SIDEBAR_SORT_TOOLTIP": {
        "it": "Clic per cambiare l'ordinamento dei nodi (ultimo contatto, segnale, hop, nome)",
        "en": "Click to change node sorting (last heard, signal, hops, name)",
    },
    "SIDEBAR_FILTER_TOOLTIP": {
        "it": "Clic per filtrare i nodi (tutti, attivi, preferiti)",
        "en": "Click to filter nodes (all, active, favorites)",
    },

    # Toast notifications for incoming messages (ui/repl.py: notify_message)
    "NOTIFY_DM_TITLE": {"it": "🔒 DM da {sender}", "en": "🔒 DM from {sender}"},
    "NOTIFY_CHANNEL_TITLE": {"it": "📡 Canale {channel} — {sender}", "en": "📡 Channel {channel} — {sender}"},

    # CLI entrypoint messages (__main__.py)
    "CLI_NO_DEVICES_USB": {
        "it": "Nessun dispositivo Meshtastic rilevato sulle porte USB.",
        "en": "No Meshtastic device detected on USB ports.",
    },
    "CLI_DEVICES_FOUND": {"it": "📡 Dispositivi Meshtastic rilevati:", "en": "📡 Meshtastic devices detected:"},
    "CLI_NO_DEVICES": {"it": "Nessun dispositivo Meshtastic rilevato.", "en": "No Meshtastic device detected."},
    "CLI_CONNECT_FAILED": {
        "it": "Impossibile connettersi al dispositivo su {port}.",
        "en": "Could not connect to the device on {port}.",
    },
    "CLI_NO_DEVICES_HINT": {
        "it": "Verifica il cavo USB o specifica manualmente la porta con --port /dev/...",
        "en": "Check the USB cable or specify the port manually with --port /dev/...",
    },
    "CLI_DEPRECATED_OPTION": {
        "it": "⚠ {option} è deprecata e sarà rimossa in v0.4.0; usa `mesh-deck {replacement}`.",
        "en": "⚠ {option} is deprecated and will be removed in v0.4.0; use `mesh-deck {replacement}`.",
    },
}


def t(key: str, lang: str = "it", **kwargs: Any) -> str:
    """Retrieve translated string with optional formatting."""
    entry = STRINGS.get(key)
    if not entry:
        return key

    text = entry.get(lang) or entry.get("it") or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def command_descriptions(lang: str) -> dict[str, str]:
    """Return localized descriptions for the command completion catalog."""
    return {
        "/help": t("HELP_TITLE", lang),
        "/nodes": t("CMD_DESC_NODES", lang),
        "/node": t("CMD_DESC_NODE", lang),
        "/dm": t("CMD_DESC_DM", lang),
        "/send": t("CMD_DESC_SEND", lang),
        "/switch": t("CMD_DESC_SWITCH", lang),
        "/channels": t("CMD_DESC_CHANNELS", lang),
        "/neighbors": t("CMD_DESC_NEIGHBORS", lang),
        "/mesh": t("CMD_DESC_MESH", lang),
        "/trace": t("CMD_DESC_TRACE", lang),
        "/info": t("CMD_DESC_INFO", lang),
        "/view": t("CMD_DESC_VIEW", lang),
        "/chat": t("CMD_DESC_CHAT", lang),
        "/settings": t("CMD_DESC_SETTINGS", lang),
        "/clear": t("CMD_DESC_CLEAR", lang),
        "/restart": t("CMD_DESC_RESTART", lang),
        "/quit": t("CMD_DESC_QUIT", lang),
    }
