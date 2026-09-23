# 🚀 Piano di Implementazione - Mesh-Deck

Questo documento definisce la roadmap tecnica e il piano operativo per lo sviluppo modulare di **Mesh-Deck**.

---

## 1. Architettura del Progetto e Struttura Directory

La struttura del progetto segue i principi di separazione delle responsabilità (Clean Architecture / Layered Design):

```text
mesh-deck/
├── pyproject.toml              # Definizione progetto e dipendenze (uv)
├── uv.lock                     # Lockfile deterministico delle dipendenze
├── README.md                   # Panoramica generale e quickstart
├── REQUIREMENTS.md             # Requisiti funzionali e di interfaccia
├── IMPLEMENTATION_PLAN.md      # Questo piano di sviluppo
├── docs/
│   └── USER_GUIDE.md           # Guida utente e operativa
├── src/
│   └── mesh_deck/
│       ├── __init__.py
│       ├── __main__.py         # Entrypoint CLI/TUI (`mesh-deck`)
│       ├── cli.py              # Adapter sottocomandi non interattivi + envelope JSON
│       ├── agent.py            # Service layer condiviso da CLI e MCP (AgentService)
│       ├── mcp_server.py       # Server MCP locale su stdio
│       ├── models.py           # Re-export dei modelli di dominio
│       ├── i18n.py             # Catalogo stringhe IT/EN
│       ├── core/               # Logica di dominio e gestione hardware
│       │   ├── __init__.py
│       │   ├── scanner.py      # Auto-discovery porte USB / seriali
│       │   ├── radio_client.py # Wrapper meshtastic.serial_interface & PubSub
│       │   ├── node_store.py   # Cache NodeDB, ricerca e calcoli geospaziali
│       │   ├── events.py       # Modelli di dominio (NodeData, MeshMessage, ...)
│       │   ├── history.py      # Storico append-only JSONL di nodi e messaggi
│       │   └── settings.py     # Preferenze utente persistite su file
│       ├── ui/                 # Presentazione e interfaccia grafica
│       │   ├── __init__.py
│       │   ├── theme.py        # Palette temi, variabili CSS e badge Rich
│       │   ├── banner.py       # Header status bar e riepiloghi
│       │   ├── tables.py       # Tabelle nodi, schede dettaglio e messaggi
│       │   ├── repl.py         # App Textual principale, sidebar e log asincrono
│       │   ├── completer.py    # Auto-completamento dinamico per slash-commands
│       │   ├── device_selector.py   # Schermata di selezione periferica all'avvio
│       │   ├── interactive_table.py # Esploratore nodi `/view` con sort al click
│       │   └── channel_chat.py      # Visualizzatore chat canali/DM `/chat`
│       └── commands/           # Dispatcher dei comandi utente
│           ├── __init__.py
│           └── dispatcher.py   # Router dei comandi (/nodes, /dm, /switch...)
├── tests/                      # Suite unittest (test_core, test_commands, test_ui)
└── tools/
    └── make_screenshots.py     # Rigenerazione deterministica degli SVG in docs/
```
> **Invarianti architetturali**
>
> - `core/` non dipende da `ui/`; `commands/dispatcher.py` orchestra i due strati.
> - `RadioClient` è l'unico punto che normalizza i dati provenienti dalla radio
>   (canali, profilo RF, pacchetti): i consumatori leggono un contratto unico in
>   `snake_case`, mai le chiavi grezze dei protobuf.
> - CLI, MCP e TUI riutilizzano lo stesso service layer (`AgentService`,
>   `RadioClient`, `NodeStore`), come richiesto da RNF-7.
> - La palette attiva vive in `ui/theme.py::THEME_COLORS`, mutata sul posto da
>   `set_theme()` ed esposta ai fogli di stile Textual come variabili `$mesh-*`.

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
  3. Creare un bridge che converte i pacchetti grezzi in eventi strutturati
     (`MeshMessage`, `NodeData` in `core/events.py`) consegnati ai listener
     registrati su `RadioClient` in modo thread-safe; la UI Textual marshalla
     poi gli aggiornamenti sul proprio loop con `call_from_thread()`.
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
  1. Implementare `theme.py`: palette semantiche multiple (`cyberpunk`, `midnight`, `nord`, `ember`), palette attiva mutata sul posto da `set_theme()` ed esposta a Textual come variabili `$mesh-*`.
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
  5. `/info` e `/channels`: Riepilogo configurazione modem e canali radio.
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

---

### Fase 8: Automazione per Agenti (CLI strutturata & MCP)
* **Obiettivo**: Rendere ogni operazione di lettura e messaggistica utilizzabile da script e agenti.
* **Attività**:
  1. Implementare `agent.py` (`AgentService`): service layer unico con errori tipizzati (`AgentServiceError`) e codici di uscita deterministici.
  2. Implementare `cli.py`: sottocomandi `scan`, `info`, `nodes`, `node`, `channels`, `neighbors`, `trace`, `send`, `dm` con envelope JSON stabile (`--output json`).
  3. Implementare `mcp_server.py`: server MCP su stdio che espone gli stessi tool; broadcast e DM restano anteprime finché non si passa `confirm=true`.
* **Criterio di Accettazione**: `mesh-deck nodes --output json` restituisce un envelope `{"ok": true, ...}` e il server MCP registra i tool di lettura, topologia, traceroute e messaggistica previsti (RF-5.1 → RF-5.5).

---

### Fase 9: Chat Visuale, Notifiche e Storico Locale
* **Obiettivo**: Rendere leggibile e persistente il traffico della mesh.
* **Attività**:
  1. Implementare `ui/channel_chat.py` (`/chat`): schermata Textual con selezione canali a click, badge non letti e invio broadcast.
  2. Implementare `core/history.py`: storico append-only JSONL di nodi e messaggi, con deduplica delle osservazioni non significative.
  3. Notifiche toast per i messaggi in arrivo e interruttori `/settings notifications|history <on|off>`.
* **Criterio di Accettazione**: `/chat` ricostruisce lo storico dei canali da `~/.config/mesh-deck/history/messages.jsonl` e mostra i nuovi messaggi in tempo reale (RF-6.1 → RF-6.7).

---

### Fase 10: Personalizzazione dell'Interfaccia
* **Obiettivo**: Rendere la console adattabile all'ambiente operativo.
* **Attività**:
  1. Barra laterale nodi ridimensionabile con ordinamento e filtro persistiti.
  2. Temi commutabili a runtime applicati sia alle renderable Rich sia ai fogli di stile Textual.
  3. Localizzazione IT/EN centralizzata in `i18n.py`.
* **Criterio di Accettazione**: `/settings theme <nome>` ridisegna immediatamente banner, tabelle, sidebar e schermate `/view` e `/chat` senza riavviare l'applicazione (RUI-6).

---

### Fase 11: Evoluzione Operativa dell'Interfaccia
* **Obiettivo**: Trasformare le schermate esistenti in strumenti operativi adattivi, senza aggiungere una dashboard o dipendenze UI esterne.
* **Incremento 1 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/view` adotta il modello master/detail: click o `Invio` su una riga rende il dossier nodo nel pannello laterale sui terminali larghi oppure apre una screen interna sui terminali compatti.
  2. La densità dell'esploratore è persistita in `settings.json` con le modalità `auto`, `full` e `compact`; in auto, sotto 120 colonne restano nome, ruolo, SNR, hop, batteria e ultimo contatto.
  3. Il cambio lingua aggiorna sidebar, filtro, colonne, binding e Node Explorer già montato senza `/restart`.
  4. Una strip persistente sotto l'header espone stato radio, nodo locale, porta e tentativo di riconnessione, senza dipendere dallo scroll del log.
  5. La guida operativa viene mantenuta in inglese in `docs/USER_GUIDE.md`.
* **Incremento 2 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. Il campo comando espone una riga persistente di avanzamento durante ogni comando eseguito nel worker Textual.
  2. Un secondo comando non viene accettato finché il worker precedente è attivo, evitando output e azioni concorrenti ambigui.
  3. `/trace` espone `Esc` come annullamento cooperativo: l'attesa viene interrotta, il waiter viene rimosso e il pacchetto già inviato non produce una risposta UI tardiva.
  4. `/switch` e connessione mostrano avanzamento ma non dichiarano una cancellazione che la libreria seriale non può eseguire in sicurezza.
* **Incremento 3 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/chat` raggruppa i messaggi diretti per peer anziché in una entry sintetica condivisa.
  2. Ogni conversazione mostra badge non letti, storico dedicato, hint con destinatario e input abilitato per la risposta diretta.
  3. `/dm` resta il flusso esplicito per iniziare una conversazione con un nodo non ancora presente nell'elenco.
* **Incremento 4 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. Il selettore startup visualizza badge per porta preferita, attiva e da ritentare.
  2. Dopo un errore di handshake conserva porta e motivazione, esponendo un retry esplicito con binding `t`.
  3. Quando non trova periferiche, presenta uno stato vuoto con indicazioni concrete su cavo, alimentazione, driver seriale e contesa della porta.
* **Incremento 5 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `NodePresentation` centralizza SNR, hop, batteria, distanza, ultimo contatto, ruolo e identità per sidebar, `/nodes` e `/view`.
  2. Ogni superficie sceglie solo la propria densità; unità, arrotondamenti e colori semantici sono condivisi.
  3. I nomi provenienti dai nodi sono escaped nella sidebar prima del rendering Rich.
* **Incremento 6 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/logs` visualizza stream separati applicazione e dispositivo in un buffer thread-safe limitato in memoria.
  2. Il viewer offre filtri per sorgente, livello e testo, pausa del refresh, copia della riga selezionata ed export della vista filtrata.
  3. Le righe device arrivano dal topic Meshtastic `meshtastic.log.line`; i log applicativi vengono catturati solo mentre l'app Textual è montata e non propagano su stdout MCP.
* **Incremento 7 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/topology` espone una screen filtrabile di edge Reporter → Neighbor ricevuti da NeighborInfo, con SNR e recenza.
  2. Un pannello qualità dati separa esplicitamente l'assenza di report dall'assenza di connettività.
  3. `/mesh` resta disponibile come riepilogo testuale compatibile; un grafo è rinviato fino a disponibilità di dati reali sufficienti.
* **Incremento 8 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/history <id|aka|nome>` legge on-demand gli snapshot `nodes.jsonl` già presenti.
  2. Range 6 ore, 24 ore, 7 giorni e completo mostrano sparkline per batteria, SNR, temperatura e utilizzo canale.
  3. Il dettaglio nodo compatto espone la stessa screen con binding `h`; assenza di snapshot o storico disattivato viene mostrata esplicitamente.
* **Incrementi successivi — ordinati per valore operativo**:
  1. Screen `/device-settings` transazionale: snapshot, draft locale, validazione, diff semantico, conferma esplicita e rilettura dell'ack; PSK, regione, reset e firmware restano fuori ambito.
  2. Topologia visuale soltanto dopo che i dati NeighborInfo reali dimostrano frequenza e qualità sufficienti.
* **Criterio di Accettazione Incremento 1**: la suite `unittest` copre dettaglio, densità automatica, persistenza, localizzazione e strip radio; il linter `ruff` è pulito; la nuova UI preserva tutte le funzionalità `/view` esistenti.
