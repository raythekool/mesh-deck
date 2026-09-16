# 📋 Requisiti di Dettaglio - Mesh-Deck

Questo documento definisce i requisiti funzionali, non funzionali, di architettura e di interfaccia per il progetto **Mesh-Deck**, una CLI/TUI interattiva ispirata all'estetica di *Hermes* per la gestione, esplorazione e monitoraggio di dispositivi e reti **Meshtastic**.

---

## 1. Obiettivi del Progetto

1. Fornire una console unificata, veloce ed esteticamente curata per interagire con uno o più nodi radio Meshtastic collegati via USB (es. Heltec Vision Master E290, LilyGo TLora-T3S3, RAK WisBlock, ecc.).
2. Offrire un'esperienza utente in stile **Hermes TUI**: prompt interattivo (REPL) con autocompletamento dei comandi (`/command`), box, tabelle stilizzate, badge dinamici e streaming di eventi in tempo reale.
3. Facilitare l'esplorazione della topologia mesh, del database nodi (NodeDB), della telemetria ambientale e radio (SNR, Hop, Batteria, Utilizzo del canale) e della messaggistica (broadcast e messaggi diretti).

---

## 2. Requisiti Funzionali (RF)

### 2.1 Gestione Hardware & Multi-Dispositivo
* **RF-1.1 Rilevamento Automatico (Auto-Discovery)**: All'avvio, l'applicazione deve scansionare le porte seriali disponibili (`/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/serial/by-id/*`) per identificare i dispositivi Meshtastic compatibili senza richiedere all'utente di specificare manualmente la porta.
* **RF-1.2 Selezione Iniziale**: Se sono presenti più dispositivi connessi (es. Heltec e LilyGo simultaneamente), l'applicazione deve mostrare un menu di selezione o agganciarsi al dispositivo primario/preferito configurato.
* **RF-1.3 Hot-Switching (`/switch`)**: Possibilità di commutare il dispositivo attivo trasmittente a runtime con un comando (es. `/switch 1` o `/switch /dev/ttyACM1`), mantenendo le informazioni di stato o riconnettendosi in modo trasparente.
* **RF-1.4 Monitoraggio Stato Connessione**: Riconnessione automatica in caso di disconnessione accidentale del cavo USB o reboot del nodo.

### 2.2 Esplorazione Nodi & Rete (Node Explorer)
* **RF-2.1 Tabella Nodi Attivi (`/nodes`)**:
  * Visualizzazione tabellare con: N. Progressivo, Nome Nodo (Long Name), Alias (Short/AKA), Node ID (es. `!45a466e4`), Hardware, Ruolo (CLIENT, ROUTER, REPEATER), SNR (dB), Hops away, Batteria/Alimentazione, Coordinate (Lat/Lon/Alt) e Ultimo Contatto (Last Heard).
  * Filtri e ordinamento rapido: per SNR decrescente, Hops crescente, attività recente o solo nodi con coordinate.
* **RF-2.2 Scheda Dettaglio Nodo (`/node <id|aka>`)**:
  * Dettagli completi del nodo selezionato: chiavi pubbliche, metriche di canale (Tx Air Utilization, Channel Utilization), storico telemetrico (tensione batteria, temperatura/sensori se disponibili).
  * Calcolo distanza in km e bearing rispetto alla posizione fissa del nodo locale (formula dell'emisenoverso).
* **RF-2.3 Analisi della Rete & Vicini (`/neighbors`, `/mesh`)**:
  * Visualizzazione delle informazioni sui vicini (Neighbor Info) e propagazione dei pacchetti.

### 2.3 Diagnostica & Strumenti Radio
* **RF-3.1 Traceroute (`/trace <id|aka>`)**:
  * Invio di richieste traceroute verso un nodo specifico e visualizzazione del percorso a salti (hops) e dei tempi di risposta.
* **RF-3.2 Info & Configurazione Radio (`/info`, `/config`)**:
  * Visualizzazione frequenza, preset modem (es. `MEDIUM_FAST`, `LONG_FAST`), potenza TX, offset frequenza e stato crittografia dei canali (Primary e canali secondari configurati).

### 2.4 Comunicazione & Messaggistica
* **RF-4.1 Messaggi Broadcast (`/send <canale> <testo>` o testo diretto)**:
  * Invio di messaggi sul canale primario predefinito o su canali secondari (es. `#Test`, `#NewsFeed`).
* **RF-4.2 Messaggi Diretti (`/dm <id|aka> <testo>`)**:
  * Invio e ricezione di messaggi privati diretti point-to-point.
* **RF-4.3 Streaming Messaggi in Tempo Reale**:
  * I messaggi ricevuti in background devono apparire in tempo reale nella console, formattati con timestamp, autore, indicatore di intensità del segnale (SNR) e canale di ricezione, senza interrompere la digitazione nel prompt.

---

## 3. Requisiti di Interfaccia & UX (RUI)

* **RUI-1 Ispirazione Hermes TUI**:
  * Utilizzo di **Rich** per la formattazione: pannelli arrotondati, tabelle ad alto contrasto, badge colorati (es. verde per SNR forte, rosso per segnali critici, blu per router).
* **RUI-2 Console Interattiva Avanzata (Textual)**:
  * Campo di comando con autocompletamento dinamico su comandi (`/`), alias e ID dei nodi noti; `Tab` applica il suggerimento principale.
  * Log scorrevole separato dal campo di input per conservare la digitazione durante gli eventi radio asincroni.
* **RUI-3 Status Header / Banner**:
  * Banner superiore visibile all'avvio con: Nome del nodo locale attivo, ID, porta seriale, preset radio (es. `EU_868 / MEDIUM_FAST`), stato alimentazione e carico canale.
* **RUI-4 Esploratore Nodi Integrato**:
  * La console Textual apre `/view` come schermata interna, con filtro e ordinamento al click, senza avviare un secondo ciclo eventi.

---

## 4. Requisiti Non Funzionali (RNF)

* **RNF-1 Efficienza & Asincronia**: La comunicazione seriale con la radio deve risiedere in thread o loop asincroni dedicati, garantendo che la UI rimanga fluida a 60 FPS senza blocchi I/O.
* **RNF-2 Compatibilità Firmware**: Compatibilità garantita con le versioni correnti di Meshtastic (firmware 2.5.x / 2.6.x / 2.7.x e protocolli Protobuf ufficiali).
* **RNF-3 Manutenibilità**: Adozione dell'API ufficiale `meshtastic-python` per evitare re-implementazioni fragili del protocollo.
* **RNF-4 Gestione Dipendenze**: Gestione interamente delegata a `uv` con lockfile deterministico (`uv.lock`). Avvio rapido tramite `uv run mesh-deck` o `uvx`.
* **RNF-5 Sicurezza dei Dati**: Nessuna condivisione non autorizzata di chiavi private dei canali; memorizzazione sicura delle preferenze locali.
