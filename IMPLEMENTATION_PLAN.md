# 🚀 Piano di Implementazione - Mesh-Deck

Questo documento definisce la roadmap tecnica e il piano operativo per lo sviluppo modulare di **Mesh-Deck**.

---

## 1. Architettura del Progetto e Struttura Directory

La struttura del progetto seguirà i principi di separazione delle responsabilità (Clean Architecture / Layered Design):

```text
mesh-deck/
├── pyproject.toml              # Definizione progetto e dipendenze (uv)
├── uv.lock                     # Lockfile deterministico delle dipendenze
├── README.md                   # Panoramica generale e quickstart
├── REQUIREMENTS.md             # Requisiti funzionali e di interfaccia
├── IMPLEMENTATION_PLAN.md      # Questo piano di sviluppo
├── src/
│   └── mesh_deck/
│       ├── __init__.py
│       ├── __main__.py         # Entrypoint per CLI/TUI (`mesh-deck`)
│       ├── core/               # Logica di dominio e gestione hardware
│       │   ├── __init__.py
│       │   ├── scanner.py      # Auto-discovery porte USB / seriali
│       │   ├── radio_client.py # Wrapper meshtastic.serial_interface & PubSub
│       │   ├── node_store.py   # Cache e gestione modello NodeDB
│       │   └── events.py       # Tipi di eventi interni e code asincrone
│       ├── ui/                 # Presentazione e interfaccia grafica
│       │   ├── __init__.py
│       │   ├── theme.py        # Stili, palette colori e simboli Rich
│       │   ├── banner.py       # Header status bar e riepiloghi
│       │   ├── tables.py       # Generatori tabelle nodi, canali e diagnostica
│       │   ├── repl.py         # Console Textual, input e log asincrono
│       │   └── completer.py    # Auto-completamento dinamico per slash-commands
│       └── commands/           # Dispatcher dei comandi utente
│           ├── __init__.py
│           ├── dispatcher.py   # Router dei comandi (/nodes, /dm, /switch...)
│           └── handlers.py     # Logica di esecuzione dei singoli comandi
└── tests/                      # Suite di test unitari e di integrazione
```

---

## 2. Fasi Operative di Sviluppo

### Fase 1: Setup Strutturale & Auto-Discovery USB
* **Obiettivo**: Identificare e presentare all'utente i nodi Meshtastic collegati al PC.
* **Attività**:
  1. Configurare la struttura di package in `src/mesh_deck`.
  2. Implementare `scanner.py`: scansione seriale (`pyserial` / `serial.tools.list_ports`) con filtro per VID/PID noti (Espressif, Silicon Labs, CH340, WCH) e descrittori seriali (`Heltec Vision Master`, `LilyGo`, `RAK`, `TBeam`).
  3. Creare una routine di test iniziale che elenca le porte e consente all'utente di selezionare quella desiderata se sono presenti più device.
* **Criterio di Accettazione**: Eseguendo `python -m mesh_deck.core.scanner` vengono rilevati immediatamente sia `/dev/ttyACM0` (Heltec) sia `/dev/ttyACM1` (LilyGo) con le relative descrizioni hardware.

---

### Fase 2: Radio Engine & Event Bridge (PubSub -> Asincrono)
* **Obiettivo**: Connettersi alla radio Meshtastic e instradare i pacchetti in arrivo senza bloccare l'interfaccia.
* **Attività**:
  1. Implementare `radio_client.py` con incapsulamento sicuro di `meshtastic.serial_interface.SerialInterface`.
  2. Sottoscrizione ai canali `pypubsub`:
     * `meshtastic.receive.text`: messaggi broadcast e DM.
     * `meshtastic.receive.telemetry`: telemetria dispositivo ed ambiente.
     * `meshtastic.receive.position`: coordinate GPS e quote.
     * `meshtastic.node.updated`: aggiornamenti sui nodi della mesh.
  3. Creare un bridge per convertire i messaggi grezzi in eventi strutturati `MeshEvent` inviati su una coda `asyncio.Queue` o processati in modo thread-safe.
* **Criterio di Accettazione**: Ricezione e parsing dei messaggi e pacchetti telemetrici in background stampati a terminale senza crash o blocchi.

---

### Fase 3: NodeStore & Gestione Dati della Mesh
* **Obiettivo**: Mantenere in memoria lo stato coerente della rete mesh.
* **Attività**:
  1. Implementare `node_store.py`: memorizzazione e indicizzazione per `node_id`, `hex_id` (es. `!45a466e4`), alias e short name.
  2. Arricchimento dei nodi: calcolo del tempo trascorso dall'ultimo contatto (*last heard*), SNR, livello batteria, hop count.
  3. Calcolo geografico: implementare formula Haversine per calcolare distanza in chilometri e direzione (bearing) rispetto alle coordinate fisse o GPS del nodo locale.
* **Criterio di Accettazione**: Capacità di estrarre e filtrare l'elenco dei nodi per stato (attivi, recenti, storici) e calcolare le distanze corrette.

---

### Fase 4: Sviluppo TUI Hermes-Style (Rich + Textual)
* **Obiettivo**: Realizzare l'identità visiva e il loop interattivo principale.
* **Attività**:
  1. Implementare `theme.py`: definizione palette (Matrix green, Cyberpunk cyan, ambra per avvisi, rosso per errori) e stili per tabelle e pannelli.
  2. Implementare `banner.py`: rendering del banner d'avvio (Nome nodo locale, ID, frequenza/regione, canali attivi, stato batteria).
  3. Implementare `repl.py`: app Textual con input contestuale, log Rich e bridge thread-safe per i messaggi in arrivo.
  4. Implementare `completer.py`: autocompletamento per comandi (`/nodes`, `/dm`, `/switch`, ecc.) e nomi dei nodi.
* **Criterio di Accettazione**: Avviando la CLI appare il banner Rich, il prompt interattivo con suggerimenti e la formattazione a colori.

---

### Fase 5: Implementazione dei Comandi Utente
* **Obiettivo**: Rendere operativa ogni funzionalità da tastiera.
* **Attività**:
  1. `/nodes`: Generazione tabella Rich con indicatori grafici (badge colorati per SNR, barre di batteria, formato compatto e leggibile).
  2. `/node <id>`: Scheda analitica dettagliata del singolo nodo.
  3. `/send <testo>`: Invio pacchetti broadcast sul canale primario.
  4. `/dm <target> <testo>`: Invio messaggio privato al nodo specificato.
  5. `/trace <id>`: Invio richiesta traceroute e attesa esito.
  6. `/info` e `/channels`: Riepilogo configurazione modem e canali radio.
* **Criterio di Accettazione**: Invio e ricezione con successo di un messaggio broadcast e di un DM tra due dispositivi radio.

---

### Fase 6: Multi-Device Hot-Switching
* **Obiettivo**: Gestione fluida di più radio connesse contemporaneamente.
* **Attività**:
  1. Implementare il comando `/switch [porta|indice]`: rilascio pulito dell'interfaccia seriale corrente e connessione immediata al secondo dispositivo senza uscire dall'applicazione.
  2. Aggiornamento in tempo reale del banner di stato col nuovo nodo attivo.
* **Criterio di Accettazione**: Possibilità di passare da Heltec (`ttyACM0`) a LilyGo (`ttyACM1`) in meno di 2 secondi con comando `/switch`.

---

### Fase 7: Packaging, Test & Documentazione
* **Obiettivo**: Consolidamento e rifinitura per la distribuzione.
* **Attività**:
  1. Configurazione script di avvio in `pyproject.toml` (`[project.scripts] mesh-deck = "mesh_deck.__main__:main"`).
  2. Scrittura suite di test per il parsing dei dati e l'auto-discovery.
  3. Aggiornamento documentazione e guida rapida per l'installazione con `uv` / `uvx`.
* **Criterio di Accettazione**: L'applicazione è installabile ed eseguibile via `uv run mesh-deck` su qualsiasi macchina Linux/macOS.
