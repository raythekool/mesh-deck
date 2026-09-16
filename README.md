# 📡 Mesh-Deck

**Mesh-Deck** è una console interattiva (CLI/TUI) in stile *Hermes* per esplorare, gestire e comunicare con dispositivi radio e reti **Meshtastic**.

Progettata per scenari multi-nodo (es. Heltec Vision Master, LilyGo T-Beam/T3S3, RAK Wireless), offre una comoda interfaccia terminale con tabelle ricche di dettagli, autocompletamento dei comandi, streaming di messaggi in tempo reale e passaggio rapido (*hot-switching*) tra dispositivi USB collegati.

---

## 📚 Documentazione del Progetto

* 📋 **[Requisiti di Dettaglio (REQUIREMENTS.md)](REQUIREMENTS.md)**: Specifica completa dei requisiti funzionali, non funzionali, di interfaccia e architettura.
* 🚀 **[Piano di Implementazione (IMPLEMENTATION_PLAN.md)](IMPLEMENTATION_PLAN.md)**: Roadmap suddivisa in 7 fasi operative di sviluppo, dall'auto-discovery USB al packaging finale.

---

## ⚡ Caratteristiche Principali

- **Multi-Device Auto-Discovery**: Individuazione automatica delle radio connesse su USB (`/dev/ttyACM*`, `/dev/ttyUSB*`) e selezione interattiva o via comando (`/switch`).
- **Hermes-Style REPL**: Prompt moderno (`mesh-deck > `) potenziato da `prompt_toolkit` con autocompletamento di comandi (`/nodes`, `/dm`, `/trace`, `/info`) e ID nodi.
- **Node Explorer ad Alta Definizione**: Tabelle Rich con visualizzazione di SNR, Hops, livello batteria, distanza stimata dal nodo locale e timestamp dell'ultimo contatto.
- **Messaggistica Integrata**: Ricezione in background senza interruzione del prompt e invio sia in broadcast (sui canali configurati) sia in messaggi diretti privati (DM).
- **Diagnostica Mesh**: Richieste traceroute, visualizzazione canali radio, potenza TX e metriche di utilizzo aereo (Air Utilization).

---

## 🛠️ Stack Tecnologico

- **Runtime & Gestione Pacchetti**: [Python 3.11+](https://www.python.org/) & [uv](https://github.com/astral-sh/uv)
- **Protocollo Radio**: [meshtastic-python](https://pypi.org/project/meshtastic/) (interfaccia seriale e bridge di eventi PubSub)
- **Terminal UI & REPL**: [Rich](https://rich.readthedocs.io/) & [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) (con supporto opzionale [Textual](https://textual.textualize.io/))
- **Comunicazione Seriale**: [pyserial](https://pyserial.readthedocs.io/)

---

## 🚀 Quickstart

```bash
# Clona il repository
git clone https://github.com/raythekool/mesh-deck.git
cd mesh-deck

# Avvia l'applicazione con uv
uv run mesh-deck
```

---

## 📄 Licenza

Distribuito sotto licenza [MIT](LICENSE).
