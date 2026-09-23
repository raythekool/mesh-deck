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
* **RF-1.4 Monitoraggio Stato Connessione** *(parziale — vedi § 6)*: La perdita di connessione viene rilevata e notificata; la riconnessione automatica dopo scollegamento USB o reboot del nodo è pianificata.

### 2.2 Esplorazione Nodi & Rete (Node Explorer)
* **RF-2.1 Tabella Nodi Attivi (`/nodes`)**:
  * Visualizzazione tabellare con: N. Progressivo, Nome Nodo (Long Name), Alias (Short/AKA), Node ID (es. `!45a466e4`), Hardware, Ruolo (CLIENT, ROUTER, REPEATER), SNR (dB), Hops away, Batteria/Alimentazione, Distanza stimata e Ultimo Contatto (Last Heard). Le coordinate complete (Lat/Lon/Alt) sono nella scheda di dettaglio `/node`.
  * Filtri e ordinamento rapido: per SNR decrescente, Hops crescente, attività recente o nome.
* **RF-2.2 Scheda Dettaglio Nodo (`/node <id|aka>`)**:
  * Dettagli completi del nodo selezionato: chiavi pubbliche, metriche di canale (Tx Air Utilization, Channel Utilization), telemetria (tensione batteria, temperatura, umidità, pressione se disponibili).
  * Calcolo distanza in km rispetto alla posizione del nodo locale (formula dell'emisenoverso). Il bearing è pianificato (§ 6).
* **RF-2.3 Analisi della Rete & Vicini (`/neighbors`, `/mesh`)** *(pianificato — vedi § 6)*:
  * Visualizzazione delle informazioni sui vicini (Neighbor Info) e propagazione dei pacchetti.

### 2.3 Diagnostica & Strumenti Radio
* **RF-3.1 Traceroute (`/trace <id|aka>`)** *(pianificato — vedi § 6)*:
  * Invio di richieste traceroute verso un nodo specifico e visualizzazione del percorso a salti (hops) e dei tempi di risposta.
* **RF-3.2 Info & Configurazione Radio (`/info`, `/channels`)**:
  * Visualizzazione regione RF, preset modem (es. `MEDIUM_FAST`, `LONG_FAST`), versione firmware e stato di uplink/downlink e crittografia dei canali (Primary e canali secondari configurati). Le chiavi PSK non vengono mai mostrate: solo la presenza o assenza di una chiave.

### 2.4 Comunicazione & Messaggistica
* **RF-4.1 Messaggi Broadcast (`/send <canale> <testo>` o testo diretto)**:
  * Invio di messaggi sul canale primario predefinito o su canali secondari (es. `#Test`, `#NewsFeed`).
* **RF-4.2 Messaggi Diretti (`/dm <id|aka> <testo>`)**:
  * Invio e ricezione di messaggi privati diretti point-to-point.
* **RF-4.3 Streaming Messaggi in Tempo Reale**:
  * I messaggi ricevuti in background devono apparire in tempo reale nella console, formattati con timestamp, autore, indicatore di intensità del segnale (SNR) e canale di ricezione, senza interrompere la digitazione nel prompt.

### 2.5 Automazione e Integrazione con Agenti
* **RF-5.1 CLI Strutturata**: Le operazioni di scansione, diagnostica, lettura nodi/canali e messaggistica devono essere disponibili come sottocomandi non interattivi.
* **RF-5.2 Output Machine-Readable**: Ogni sottocomando deve offrire un envelope JSON stabile, errori strutturati e codici di uscita deterministici.
* **RF-5.3 Server MCP Locale**: L'applicazione deve poter avviare un server MCP su stdio che esponga tool tipizzati per scansione, info radio, nodi, canali, broadcast e messaggi diretti.
* **RF-5.4 Conferma Effetti Esterni**: Broadcast e DM via CLI o MCP devono produrre solo un'anteprima finché non viene fornita una conferma esplicita.
* **RF-5.5 Perimetro MCP**: Il server MCP iniziale non deve modificare configurazione radio, PSK o preferenze persistenti.

### 2.6 Chat Visuale, Notifiche e Storico Locale
* **RF-6.1 Chat Multi-Canale Cliccabile (`/chat`)**: Schermata Textual a tutto schermo, utilizzabile interamente con il mouse, che elenca canali e messaggi diretti in una barra laterale selezionabile con click e mostra lo storico più i messaggi live in un pannello dedicato per la voce selezionata.
* **RF-6.2 Invio Broadcast dalla Chat**: Il campo di input della schermata `/chat` invia un broadcast sul canale attualmente selezionato; l'invio è disabilitato quando è selezionata la voce "Messaggi Diretti" (i DM restano gestiti da `/dm`).
* **RF-6.3 Badge Messaggi Non Letti**: I canali/DM diversi da quello attualmente visualizzato mostrano un badge numerico con il conteggio dei nuovi messaggi ricevuti, azzerato alla selezione.
* **RF-6.4 Notifiche Toast in Tempo Reale**: Ogni messaggio ricevuto (broadcast o DM) genera una notifica toast nativa, con titolo e severità differenziati per i DM rispetto ai broadcast; disattivabile con `/settings notifications off`.
* **RF-6.5 Storico Nodi su File**: Le osservazioni di ciascun nodo (caratteristiche hardware, ruolo, telemetria, posizione) sono registrate in modo append-only su file JSONL quando cambiano in modo sostanziale rispetto all'ultima osservazione, con timestamp di rilevazione.
* **RF-6.6 Storico Messaggi su File**: I messaggi inviati e ricevuti su ciascun canale (e i DM) sono registrati in modo append-only su file JSONL, con direzione (`in`/`out`) e timestamp di registrazione, condivisi da CLI, TUI e MCP.
* **RF-6.7 Persistenza Opt-In**: Storico nodi/messaggi e notifiche sono attivi per default ma disattivabili singolarmente via `/settings history <on|off>` e `/settings notifications <on|off>`; nessun file di storico viene creato se la funzione è disabilitata.

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
* **RUI-5 Chat Canali Integrata**:
  * La console Textual apre `/chat` come schermata interna, con selezione a click dei canali/DM nella barra laterale e invio broadcast dal campo di input, senza avviare un secondo ciclo eventi.
* **RUI-6 Temi Commutabili a Runtime**:
  * Sono disponibili almeno tre palette (`cyberpunk`, `midnight`, `nord`, `ember`) selezionabili con `/settings theme <nome>`.
  * Il cambio tema si applica immediatamente sia alle renderable **Rich** (banner, tabelle, schede nodo, messaggi) sia ai fogli di stile **Textual** (console, sidebar, `/view`, `/chat`, dialoghi), senza riavviare l'applicazione.
  * Ogni palette definisce il medesimo insieme di chiavi semantiche; un valore non riconosciuto ricade sul tema predefinito senza generare errori.

---

## 4. Requisiti Non Funzionali (RNF)

* **RNF-1 Efficienza & Asincronia**: La comunicazione seriale con la radio deve risiedere in thread o loop asincroni dedicati, garantendo che la UI rimanga fluida a 60 FPS senza blocchi I/O.
* **RNF-2 Compatibilità Firmware**: Compatibilità garantita con le versioni correnti di Meshtastic (firmware 2.5.x / 2.6.x / 2.7.x e protocolli Protobuf ufficiali).
* **RNF-3 Manutenibilità**: Adozione dell'API ufficiale `meshtastic-python` per evitare re-implementazioni fragili del protocollo.
* **RNF-4 Gestione Dipendenze**: Gestione interamente delegata a `uv` con lockfile deterministico (`uv.lock`). Avvio rapido tramite `uv run mesh-deck` o `uvx`.
* **RNF-5 Sicurezza dei Dati**: Nessuna condivisione non autorizzata di chiavi private dei canali; memorizzazione sicura delle preferenze locali.
* **RNF-6 Integrità stdio**: In modalità MCP nessun output applicativo o log deve essere scritto su stdout al di fuori del protocollo; i log devono usare stderr.
* **RNF-7 Riutilizzo della Logica**: CLI, MCP e interfacce interattive devono riutilizzare il medesimo service layer per selezione porta, validazione e accesso alla radio.
* **RNF-8 Concorrenza MCP**: Gli accessi alla sessione radio persistente del server MCP devono essere serializzati e la connessione deve essere chiusa all'arresto.
* **RNF-9 Robustezza dei Comandi**: Un errore della radio (cavo scollegato, timeout, invio fallito) deve produrre un messaggio diagnostico nella console e non deve mai propagarsi fino a terminare il worker della UI o la sessione interattiva.
* **RNF-10 Contratto Dati Unico**: I dati provenienti dai protobuf Meshtastic devono essere normalizzati in un unico punto (`RadioClient`) e consumati in `snake_case` da CLI, MCP, TUI e banner, così da evitare divergenze fra i diversi adapter.

---

## 5. Portata dei Test

* La suite `tests/` usa `unittest` della libreria standard e non richiede hardware radio: seriale e PubSub sono simulati.
* I test non devono produrre effetti collaterali sul file system dell'utente: impostazioni e storico vanno isolati in directory temporanee.

---

## 6. Roadmap (non ancora implementato)

Requisiti già approvati ma rinviati a iterazioni successive:

| Requisito | Descrizione | Stato |
| :-------- | :---------- | :---- |
| RF-1.4 | Riconnessione automatica dopo scollegamento USB o reboot del nodo | Rilevamento presente, riconnessione da implementare |
| RF-2.2 | Bearing (azimut) verso il nodo remoto oltre alla distanza | Da implementare |
| RF-2.3 | `/neighbors` e `/mesh`: Neighbor Info e propagazione pacchetti | Da implementare |
| RF-3.1 | `/trace`: traceroute verso un nodo con percorso a salti | Da implementare |
