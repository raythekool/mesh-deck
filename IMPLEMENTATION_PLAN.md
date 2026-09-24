# 🚀 Piano di Implementazione - Mesh-Deck

Questo documento definisce la roadmap tecnica e il piano operativo per lo sviluppo modulare di **Mesh-Deck**.

> **Stato verificato il 24 settembre 2026**
>
> - **✅ Integrato in `main`**: Fasi 1–10, inclusi automazione CLI/MCP,
>   cronologia, chat, riconnessione, topologia testuale, traceroute e temi.
> - **✅ Completato nel branch `feat/ui-node-explorer-foundation`**: Fase 11,
>   con tutti i dieci incrementi UI descritti in fondo al documento. Il branch
>   contiene 18 commit propri ed è indietro di 3 commit rispetto a `main`:
>   prima del merge va riallineato e rieseguita la suite.
> - **📄 Proposte visuali**: [`docs/UI_DEVELOPMENT.md`](docs/UI_DEVELOPMENT.md)
>   è la matrice di tracciabilità fra ogni wireframe e il relativo incremento
>   implementato.
>
> L'audit del codice, dei commit e dei test sul branch UI ha confermato
> **240 test `unittest` superati** e `ruff` pulito. Il piano usa **✅** per il
> lavoro consegnato e **🟡** per ciò che rimane intenzionalmente fuori ambito.
>
> **Validazione hardware del 24 settembre 2026**: una LilyGo TLora-T3S3-V1
> su `/dev/ttyACM0` ha confermato identificazione radio, canali, NodeDB,
> traceroute diretto verso un peer LoRa autorizzato e invio di un DM diretto
> marcato come test. La prova ha anche rilevato un join seriale senza timeout
> in `meshtastic-python`; `RadioClient` ora limita il teardown a tre secondi
> e rilascia la porta forzando l'interruzione della read bloccante.

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

### ✅ Fase 1: Setup Strutturale & Auto-Discovery USB — Integrata in `main`
* **Obiettivo**: Identificare e presentare all'utente i nodi Meshtastic collegati al PC.
* **Attività**:
  1. Configurare la struttura di package in `src/mesh_deck`.
  2. Implementare `scanner.py`: scansione seriale (`pyserial` / `serial.tools.list_ports`) con filtro per VID/PID noti (Espressif, Silicon Labs, CH340, WCH) e descrittori seriali (`Heltec Vision Master`, `LilyGo`, `RAK`, `TBeam`).
  3. Creare una routine di test iniziale che elenca le porte e consente all'utente di selezionare quella desiderata se sono presenti più device.
* **Criterio di Accettazione — soddisfatto**: `scan_meshtastic_ports()` è
  coperto da test con porte simulate; la selezione Textual gestisce più
  periferiche, refresh e porta preferita. La scansione reale ha rilevato una
  radio T-Beam su `COM6` durante la validazione hardware.

---

### ✅ Fase 2: Radio Engine & Event Bridge (PubSub -> Asincrono) — Integrata in `main`
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
* **Criterio di Accettazione — soddisfatto**: `RadioClient` instrada testo,
  telemetria, posizione, aggiornamenti nodo, NeighborInfo e traceroute verso
  callback strutturati. Il bridge UI usa `call_from_thread()` e tollera il
  teardown dell'app; i percorsi critici sono testati e quelli radio principali
  sono stati verificati su hardware. La chiusura seriale è bounded anche se
  il reader thread della libreria non si risveglia spontaneamente.

---

### ✅ Fase 3: NodeStore & Gestione Dati della Mesh — Integrata in `main`
* **Obiettivo**: Mantenere in memoria lo stato coerente della rete mesh.
* **Attività**:
  1. Implementare `node_store.py`: memorizzazione e indicizzazione per `node_id`, `hex_id` (es. `!45a466e4`), alias e short name.
  2. Arricchimento dei nodi: calcolo del tempo trascorso dall'ultimo contatto (*last heard*), SNR, livello batteria, hop count.
  3. Calcolo geografico: implementare formula Haversine per calcolare distanza in chilometri e direzione (bearing) rispetto alle coordinate fisse o GPS del nodo locale.
* **Criterio di Accettazione — soddisfatto**: `NodeStore` indicizza per ID,
  numero e short name, calcola distanza Haversine e bearing, e alimenta filtri
  attivi/preferiti, storico JSONL e viste topologiche.

---

### ✅ Fase 4: Sviluppo TUI Hermes-Style (Rich + Textual) — Integrata in `main`
* **Obiettivo**: Realizzare l'identità visiva e il loop interattivo principale.
* **Attività**:
  1. Implementare `theme.py`: palette semantiche multiple (`cyberpunk`, `midnight`, `nord`, `ember`), palette attiva mutata sul posto da `set_theme()` ed esposta a Textual come variabili `$mesh-*`.
  2. Implementare `banner.py`: rendering del banner d'avvio (Nome nodo locale, ID, frequenza/regione, canali attivi, stato batteria).
  3. Implementare `repl.py`: app Textual con input contestuale, log Rich e bridge thread-safe per i messaggi in arrivo.
  4. Implementare `completer.py`: autocompletamento per comandi (`/nodes`, `/dm`, `/switch`, ecc.) e nomi dei nodi.
* **Criterio di Accettazione — soddisfatto**: banner, console Textual,
  autocompletamento, cronologia comandi, temi runtime e rendering Rich sono
  disponibili. Il comando globale `mesh-deck` può essere installato con
  `uv tool install --editable .`.

---

### ✅ Fase 5: Implementazione dei Comandi Utente — Integrata in `main`
* **Obiettivo**: Rendere operativa ogni funzionalità da tastiera.
* **Attività**:
  1. `/nodes`: Generazione tabella Rich con indicatori grafici (badge colorati per SNR, barre di batteria, formato compatto e leggibile).
  2. `/node <id>`: Scheda analitica dettagliata del singolo nodo.
  3. `/send <testo>`: Invio pacchetti broadcast sul canale primario.
  4. `/dm <target> <testo>`: Invio messaggio privato al nodo specificato.
  5. `/info` e `/channels`: Riepilogo configurazione modem e canali radio.
* **Criterio di Accettazione — soddisfatto**: `/nodes`, `/node`, `/send`,
  `/dm`, `/info`, `/channels`, `/neighbors`, `/mesh` e `/trace` sono
  implementati. I contratti `/info`, `/channels`, `/trace` e la gestione
  dell'errore DM sono stati verificati con una radio reale; un DM diretto
  verso il peer autorizzato ha restituito un `MeshPacket` ed è stato scritto
  nello storico temporaneo. Il dispatcher rifiuta target DM non risolvibili
  prima di invocare la libreria radio.

---

### ✅ Fase 6: Multi-Device Hot-Switching — Integrata in `main`
* **Obiettivo**: Gestione fluida di più radio connesse contemporaneamente.
* **Attività**:
  1. Implementare il comando `/switch [porta|indice]`: rilascio pulito dell'interfaccia seriale corrente e connessione immediata al secondo dispositivo senza uscire dall'applicazione.
  2. Aggiornamento in tempo reale del banner di stato col nuovo nodo attivo.
* **Criterio di Accettazione — soddisfatto funzionalmente**: `/switch`
  seleziona porta o indice, chiude l'interfaccia precedente e connette la
  successiva; errori e riconnessione automatica usano callback espliciti.
  🟡 Il vincolo quantitativo di due secondi richiede una prova con due radio
  fisiche e resta da misurare, non da implementare.

---

### ✅ Fase 7: Packaging, Test & Documentazione — Integrata in `main`
* **Obiettivo**: Consolidamento e rifinitura per la distribuzione.
* **Attività**:
  1. Configurazione script di avvio in `pyproject.toml` (`[project.scripts] mesh-deck = "mesh_deck.__main__:main"`).
  2. Scrittura suite di test per il parsing dei dati e l'auto-discovery.
  3. Aggiornamento documentazione e guida rapida per l'installazione con `uv` / `uvx`.
* **Criterio di Accettazione — soddisfatto**: packaging Hatchling, lockfile
  `uv`, script `mesh-deck`, documentazione utente, screenshot riproducibili e
  CI Linux con `uv sync --locked`, `ruff` e test sono presenti. Il comando
  standalone è documentato e verificato con `uv tool install --editable .`.

---

### ✅ Fase 8: Automazione per Agenti (CLI strutturata & MCP) — Integrata in `main`
* **Obiettivo**: Rendere ogni operazione di lettura e messaggistica utilizzabile da script e agenti.
* **Attività**:
  1. Implementare `agent.py` (`AgentService`): service layer unico con errori tipizzati (`AgentServiceError`) e codici di uscita deterministici.
  2. Implementare `cli.py`: sottocomandi `scan`, `info`, `nodes`, `node`, `channels`, `neighbors`, `trace`, `send`, `dm` con envelope JSON stabile (`--output json`).
  3. Implementare `mcp_server.py`: server MCP su stdio che espone gli stessi tool; broadcast e DM restano anteprime finché non si passa `confirm=true`.
* **Criterio di Accettazione — soddisfatto**: `AgentService`, sottocomandi
  CLI JSON e server MCP condividono `RadioClient`. I tool MCP coprono
  scansione, radio, nodi, canali, vicini, traceroute e messaggistica con
  anteprima esplicita; stdout MCP resta riservato al protocollo.

---

### ✅ Fase 9: Chat Visuale, Notifiche e Storico Locale — Integrata in `main`
* **Obiettivo**: Rendere leggibile e persistente il traffico della mesh.
* **Attività**:
  1. Implementare `ui/channel_chat.py` (`/chat`): schermata Textual con selezione canali a click, badge non letti e invio broadcast.
  2. Implementare `core/history.py`: storico append-only JSONL di nodi e messaggi, con deduplica delle osservazioni non significative.
  3. Notifiche toast per i messaggi in arrivo e interruttori `/settings notifications|history <on|off>`.
* **Criterio di Accettazione — soddisfatto**: `/chat` ricostruisce storico
  JSONL, mostra messaggi live, badge non letti e notifiche; la successiva
  Fase 11 estende i DM da una vista aggregata a conversazioni per peer.

---

### ✅ Fase 10: Personalizzazione dell'Interfaccia — Integrata in `main`
* **Obiettivo**: Rendere la console adattabile all'ambiente operativo.
* **Attività**:
  1. Barra laterale nodi ridimensionabile con ordinamento e filtro persistiti.
  2. Temi commutabili a runtime applicati sia alle renderable Rich sia ai fogli di stile Textual.
  3. Localizzazione IT/EN centralizzata in `i18n.py`.
* **Criterio di Accettazione — soddisfatto**: quattro temi semantici sono
  applicati runtime a Rich e Textual; sidebar, larghezza, filtri,
  ordinamento, lingua, cronologia e preferenze sono persistiti.

---

### ✅ Fase 11: Evoluzione Operativa dell'Interfaccia — Completa nel branch `feat/ui-node-explorer-foundation`
* **Obiettivo**: Trasformare le schermate esistenti in strumenti operativi adattivi, senza aggiungere una dashboard o dipendenze UI esterne.

#### Tracciabilità con le proposte visuali

La tabella collega il documento di design
[`docs/UI_DEVELOPMENT.md`](docs/UI_DEVELOPMENT.md) al lavoro consegnato.
Le proposte 10 e 13 sono complete soltanto nel perimetro sicuro dichiarato;
le estensioni radio ad alto rischio restano intenzionalmente non implementate.

| Proposta UI | Stato | Evidenza nel branch |
| :---------- | :---- | :------------------ |
| 1. Master/detail Node Explorer | ✅ | Incremento 1: dettaglio laterale su terminali larghi e screen interna compatta |
| 2. Layout responsive compatto | ✅ | Incremento 1: modalità `auto` / `full` / `compact` persistita |
| 3. Localizzazione live | ✅ | Incremento 1: refresh di colonne, binding, sidebar, filtro e screen montate |
| 4. Strip stato radio | ✅ | Incremento 1: stato, nodo, porta e retry persistenti sotto l'header |
| 5. Avanzamento e annullamento comando | ✅ | Incremento 2: progress persistente, serializzazione e annullamento cooperativo `/trace` |
| 6. Conversazioni DM | ✅ | Incremento 3: conversazioni per peer, badge e risposta diretta |
| 7. Selettore periferica recuperabile | ✅ | Incremento 4: badge, retry e stato vuoto guidato |
| 8. Modello di presentazione nodo | ✅ | Incremento 5: `NodePresentation` condiviso fra sidebar, `/nodes` e `/view` |
| 9. Topologia data-first | ✅ | Incremento 7: `/topology` filtrabile e pannello qualità dati; grafo rinviato |
| 10. Telemetria storica | ✅ *slice on-demand* | Incremento 8: JSONL, range e sparkline; nessuna dashboard continua |
| 11. Gate accessibilità/temi | ✅ | Incremento 10: contrasto automatico, focus visibile e renderer sample per palette |
| 12. Log applicazione/dispositivo | ✅ | Incremento 6: buffer limitato, filtri, pausa, copia ed export |
| 13. Impostazioni dispositivo | ✅ *slice identità* | Incremento 9: draft, diff, conferma e `setOwner`; radio/PSK/reset restano protetti |
* **✅ Incremento 1 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/view` adotta il modello master/detail: click o `Invio` su una riga rende il dossier nodo nel pannello laterale sui terminali larghi oppure apre una screen interna sui terminali compatti.
  2. La densità dell'esploratore è persistita in `settings.json` con le modalità `auto`, `full` e `compact`; in auto, sotto 120 colonne restano nome, ruolo, SNR, hop, batteria e ultimo contatto.
  3. Il cambio lingua aggiorna sidebar, filtro, colonne, binding e Node Explorer già montato senza `/restart`.
  4. Una strip persistente sotto l'header espone stato radio, nodo locale, porta e tentativo di riconnessione, senza dipendere dallo scroll del log.
  5. La guida operativa in `docs/USER_GUIDE.md` descrive comportamento,
     binding e modalità del nuovo Node Explorer.
* **✅ Incremento 2 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. Il campo comando espone una riga persistente di avanzamento durante ogni comando eseguito nel worker Textual.
  2. Un secondo comando non viene accettato finché il worker precedente è attivo, evitando output e azioni concorrenti ambigui.
  3. `/trace` espone `Esc` come annullamento cooperativo: l'attesa viene interrotta, il waiter viene rimosso e il pacchetto già inviato non produce una risposta UI tardiva.
  4. `/switch` e connessione mostrano avanzamento ma non dichiarano una cancellazione che la libreria seriale non può eseguire in sicurezza.
* **✅ Incremento 3 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/chat` raggruppa i messaggi diretti per peer anziché in una entry sintetica condivisa.
  2. Ogni conversazione mostra badge non letti, storico dedicato, hint con destinatario e input abilitato per la risposta diretta.
  3. `/dm` resta il flusso esplicito per iniziare una conversazione con un nodo non ancora presente nell'elenco.
* **✅ Incremento 4 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. Il selettore startup visualizza badge per porta preferita, attiva e da ritentare.
  2. Dopo un errore di handshake conserva porta e motivazione, esponendo un retry esplicito con binding `t`.
  3. Quando non trova periferiche, presenta uno stato vuoto con indicazioni concrete su cavo, alimentazione, driver seriale e contesa della porta.
* **✅ Incremento 5 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `NodePresentation` centralizza SNR, hop, batteria, distanza, ultimo contatto, ruolo e identità per sidebar, `/nodes` e `/view`.
  2. Ogni superficie sceglie solo la propria densità; unità, arrotondamenti e colori semantici sono condivisi.
  3. I nomi provenienti dai nodi sono escaped nella sidebar prima del rendering Rich.
* **✅ Incremento 6 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/logs` visualizza stream separati applicazione e dispositivo in un buffer thread-safe limitato in memoria.
  2. Il viewer offre filtri per sorgente, livello e testo, pausa del refresh, copia della riga selezionata ed export della vista filtrata.
  3. Le righe device arrivano dal topic Meshtastic `meshtastic.log.line`; i log applicativi vengono catturati solo mentre l'app Textual è montata e non propagano su stdout MCP.
* **✅ Incremento 7 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/topology` espone una screen filtrabile di edge Reporter → Neighbor ricevuti da NeighborInfo, con SNR e recenza.
  2. Un pannello qualità dati separa esplicitamente l'assenza di report dall'assenza di connettività.
  3. `/mesh` resta disponibile come riepilogo testuale compatibile; un grafo è rinviato fino a disponibilità di dati reali sufficienti.
* **✅ Incremento 8 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/history <id|aka|nome>` legge on-demand gli snapshot `nodes.jsonl` già presenti.
  2. Range 6 ore, 24 ore, 7 giorni e completo mostrano sparkline per batteria, SNR, temperatura e utilizzo canale.
  3. Il dettaglio nodo compatto espone la stessa screen con binding `h`; assenza di snapshot o storico disattivato viene mostrata esplicitamente.
* **✅ Incremento 9 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. `/device-settings` implementa il primo gruppo scrivibile sicuro: identità locale (long/short name).
  2. Il flusso è snapshot → draft validato → diff semantico → conferma modale → `setOwner` ufficiale → snapshot aggiornato.
  3. Limiti nome sono validati prima dell'API per evitare truncation/output della libreria; PSK, regione, reset, firmware, canali, posizione e configurazioni radio restano non modificabili fino a validazione hardware dedicata.
* **✅ Incremento 10 — completato sul branch `feat/ui-node-explorer-foundation`**:
  1. Quality gate automatico verifica il contrasto delle palette per ruoli testuali semanticamente attivi su fondo standard e panel.
  2. Focus visibile usa bordo double primario su input, select, liste, tabelle e button delle screen principali.
  3. Il renderer sample screenshot è esercitato per tutte le palette; il colore alert Nord è corretto per il contrasto.
* **Semplificazione avvio CLI — completata sul branch `feat/ui-node-explorer-foundation`**:
  1. `scan` e `nodes` sono i comandi canonici non interattivi; offrono JSON, timeout, ordinamento e filtri che i flag legacy non supportano.
  2. `--list` e `--nodes` restano compatibili con warning su stderr fino alla rimozione pianificata in v0.4.0.
  3. L'impostazione persistita `ui_mode` e `/settings mode` sono rimossi; `--tui` resta la scelta one-shot esplicita per aprire direttamente l'esploratore.
* **Incrementi successivi — ordinati per valore operativo**:
  1. Estendere `/device-settings` a radio, posizione e metadati canale solo dopo API, side effect e acknowledgement verificati su hardware; PSK, regione, reset e firmware restano fuori ambito.
  2. Topologia visuale soltanto dopo che i dati NeighborInfo reali dimostrano frequenza e qualità sufficienti.
* **Criterio di Accettazione Incremento 1**: la suite `unittest` copre dettaglio, densità automatica, persistenza, localizzazione e strip radio; il linter `ruff` è pulito; la nuova UI preserva tutte le funzionalità `/view` esistenti.
