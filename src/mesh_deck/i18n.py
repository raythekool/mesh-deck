"""Internationalization (i18n) module for Mesh-Deck supporting IT and EN."""

from __future__ import annotations

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    # General / Banner
    "BANNER_TITLE": {
        "it": "📡 MESH-DECK // CONSOLE TATTICA",
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
    "COL_INDEX": {"it": "#", "en": "#"},
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
        "/info": t("CMD_DESC_INFO", lang),
        "/view": t("CMD_DESC_VIEW", lang),
        "/settings": t("CMD_DESC_SETTINGS", lang),
        "/clear": t("CMD_DESC_CLEAR", lang),
        "/restart": t("CMD_DESC_RESTART", lang),
        "/quit": t("CMD_DESC_QUIT", lang),
    }
