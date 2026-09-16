# 📡 Mesh-Deck — Manuale Utente & Guida Operativa

Benvenuto nel manuale operativo ufficiale di **Mesh-Deck**, la console interattiva terminale (CLI/TUI) in stile tattico *Hermes* concepita per il monitoraggio, l'amministrazione e la messaggistica su reti radio **[Meshtastic](https://meshtastic.org/)**.

---

## 📑 Indice dei Contenuti

1. [Introduzione & Filosofia di Progetto](#-1-introduzione--filosofia-di-progetto)
2. [Installazione & Avvio Rapido](#-2-installazione--avvio-rapido)
3. [Manuale Completo dei Comandi Slash](#-3-manuale-completo-dei-comandi-slash)
4. [Approfondimento delle Funzionalità Chiave](#-4-approfondimento-delle-funzionalità-chiave)
   - [Auto-Discovery USB & Hot-Switching](#auto-discovery-usb--hot-switching)
   - [Node Explorer & Calcolo Distanze Geodetiche](#node-explorer--calcolo-distanze-geodetiche)
   - [Gestione Canali e Messaggistica Tattica](#gestione-canali-e-messaggistica-tattica)
  - [Streaming Asincrono in Background (Textual)](#streaming-asincrono-in-background-textual)
   - [Interpretazione Visiva dei Badge e Indicatori](#interpretazione-visiva-dei-badge-e-indicatori)
5. [Troubleshooting & Risoluzione Problemi](#-5-troubleshooting--risoluzione-problemi)

---

## 🛸 1. Introduzione & Filosofia di Progetto

**Mesh-Deck** è stato progettato per rispondere alle esigenze di operatori radioamatoriali, team di protezione civile, escursionisti e appassionati di telecomunicazioni off-grid che impiegano nodi LoRa Meshtastic sul campo o in stazioni base.

![Banner Tattico Hermes](screenshots/banner.svg)

### L'Estetica Tattica Hermes TUI
A differenza delle utility CLI tradizionali a riga di comando o delle interfacce web pesanti, Mesh-Deck adotta il paradigma visivo **Hermes TUI**:
- **Palette Cyberpunk High-Contrast**: Uso mirato di tonalità neon ad alta visibilità (`#00f3ff` ciano elettrico, `#00ff66` verde matrice, `#ff007f` fucsia per allarmi/DM, `#ffb800` ambra per avvisi), studiata per garantire massima leggibilità anche all'aperto su display opachi o terminali a basso consumo.
- **Densità Informativa Senza Sovraccarico**: I dati essenziali (stato del link, livello batteria, tensione cella, SNR, hop count e canali) sono aggregati in pannelli compatti e tabelle responsive realizzate con la libreria [Rich](https://rich.readthedocs.io/).
- **Esperienza TUI Fluida**: Console [Textual](https://textual.textualize.io/) con input contestuale, log scorrevole e cronologia persistente. I suggerimenti dinamici per comandi, porte seriali e nomi dei nodi si applicano con `Tab`, oppure si navigano con freccia Giù e `Invio`.

### Supporto Multi-Device
Mesh-Deck riconosce automaticamente un'ampia varietà di dispositivi e chipset LoRa commerciali:
- **Heltec Automation**: Vision Master E290 (display e-paper), WiFi LoRa 32 (V2, V3), Wireless Stick Lite, Capsule Sensor.
- **LilyGo**: T-Beam (v1.1, v1.2 con AXP192/AXP2101), T-Echo (nRF52840), T-Motion, T3S3 (ESP32-S3 + SX1262).
- **RAK Wireless**: WisBlock Core RAK4631 (nRF52840 + SX1262), RAK11200, RAK11310 (RP2040).
- **Dispositivi Custom & DIY**: Stazioni basate su Raspberry Pi Pico / RP2040, nRF52840 Dongle USB e moduli ESP32 con controller seriali CH340, CP210x o FTDI.

---

## ⚡ 2. Installazione & Avvio Rapido

Mesh-Deck richiede **Python 3.11 o superiore** ed è ottimizzato per essere eseguito con il package manager ultrarapido **[`uv`](https://github.com/astral-sh/uv)**.

### Prerequisiti su Sistemi Linux
Assicurati che il tuo utente abbia i permessi di accesso alle periferiche seriali USB (gruppo `dialout` su Debian/Ubuntu o `uucp` su Arch Linux):

```bash
# Aggiungi l'utente corrente al gruppo delle porte seriali
sudo usermod -a -G dialout $USER

# Applica i permessi (o effettua un logout/login)
newgrp dialout
```

### Avvio Immediato con `uv`
Non è necessario installare manualmente i pacchetti nell'ambiente globale:

```bash
# Clona il repository
git clone https://github.com/raythekool/mesh-deck.git
cd mesh-deck

# Avvio interattivo della console
uv run mesh-deck
```

### Flag CLI Disponibili

Mesh-Deck mette a disposizione diversi argomenti a riga di comando per automatizzare l'uso o selezionare porte specifiche:

| Flag            | Argomento       | Descrizione                                                                                                                                                     |
| :-------------- | :-------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-p`, `--port`  | `<DEVICE_PORT>` | Connette direttamente Mesh-Deck a una porta seriale specifica (es. `-p /dev/ttyACM0` o `-p /dev/ttyUSB1`).                                                      |
| `-l`, `--list`  | *(nessuno)*     | Esegue la scansione delle porte USB seriali, elenca tutti i dispositivi Meshtastic rilevati con il relativo modello hardware ed esce.                           |
| `-n`, `--nodes` | *(nessuno)*     | Modalità non-interattiva: si connette alla prima radio disponibile, scarica il NodeDB, stampa la tabella completa dei nodi ed esce. Utile per script e cronjob. |
| `--tui`         | *(nessuno)*     | Avvia direttamente il Node Explorer Textual con filtro e ordinamento, senza mostrare la console comandi.                                                        |
| `-h`, `--help`  | *(nessuno)*     | Mostra il riepilogo della sintassi CLI e dei flag utilizzabili.                                                                                                 |

#### Esempi di Uso da Riga di Comando:

```bash
# 1. Scansiona e visualizza le radio LoRa connesse via USB
uv run mesh-deck --list

# 2. Connettiti forzatamente al secondo dispositivo su ttyUSB0
uv run mesh-deck --port /dev/ttyUSB0

# 3. Estrai istantaneamente la tabella nodi per esportazione o logging
uv run mesh-deck --nodes > mesh_snapshot.txt
```

---

## ⌨️ 3. Manuale Completo dei Comandi Slash

Una volta avviato Mesh-Deck, viene visualizzato il banner tattico sopra un log
scorrevole e un campo comando. Il placeholder mostra il nodo locale, quando
disponibile:

```text
mesh-deck [AKA] - messaggio o /help
```

Dove `[AKA]` rappresenta l'identificativo breve (4 caratteri) del tuo nodo locale collegato via USB. Digita i comandi preceduti da una barra (`/`) oppure digita direttamente del testo libero per trasmettere in broadcast.

### Controlli della Console

| Azione                                     | Controllo                           |
| :----------------------------------------- | :---------------------------------- |
| Eseguire un comando o inviare un messaggio | `Invio`                             |
| Applicare il primo suggerimento            | `Tab`                               |
| Selezionare un suggerimento alternativo    | freccia Giù, frecce Su/Giù, `Invio` |
| Richiamare un comando precedente           | frecce Su/Giù nel campo comando     |
| Cancellare il testo corrente               | `Ctrl+C`                            |
| Nascondere i suggerimenti                  | `Esc`                               |

La cronologia conserva gli ultimi 100 comandi in
`~/.config/mesh-deck/settings.json`. I messaggi ricevuti vengono aggiunti al log
senza interrompere il testo in digitazione.

---

### `/help` (o `/?`)
* **Sintassi**: `/help` oppure `/?`
* **Parametri**: Nessuno.
* **Descrizione**: Visualizza la tabella di consultazione rapida con l'elenco completo dei comandi slash supportati, la relativa sintassi degli argomenti e una breve spiegazione operativa.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /help
  ```

---

### `/nodes`
* **Sintassi**: `/nodes [active|snr|hops|name|last_heard]`
* **Parametri**:
  - `active` *(opzionale)*: Filtra la vista mostrando esclusivamente i nodi "attivi", ovvero quelli ricevuti negli ultimi 15 minuti.
  - `snr` *(opzionale)*: Ordina la tabella in ordine decrescente di Signal-to-Noise Ratio (i nodi con ricezione migliore in cima).
  - `hops` *(opzionale)*: Ordina i nodi per numero crescente di hop (i nodi diretti a 0 hop in cima).
  - `name` *(opzionale)*: Ordina alfabeticamente i nodi per nome completo.
  - `last_heard` *(predefinito)*: Ordina i nodi dal più recente al più vecchio.
* **Descrizione**: Interroga il database nodi in memoria locale e genera una tabella riccamente formattata in standard Rich. La riga del **nodo locale** è contraddistinta da una stella verde brillante `★`, testo ciano e l'etichetta `(LOCALE)`.
* **Screenshot Dimostrativo**:
  ![Tabella Nodi Mesh](screenshots/nodes_table.svg)
* **Esempi d'uso**:
  ```text
  # Mostra tutti i nodi ordinati per ultimo contatto
  mesh-deck [VM290] ❯ /nodes

  # Mostra solo i nodi ascoltati di recente
  mesh-deck [VM290] ❯ /nodes active

  # Ordina i nodi per intensità di segnale radio
  mesh-deck [VM290] ❯ /nodes snr
  ```

---

### `/view` (o `/tui`)
* **Sintassi**: `/view` oppure `/tui`.
* **Parametri**: Nessuno.
* **Descrizione**: Apre il Node Explorer come schermata Textual interna. La
  tabella supporta filtro istantaneo per nome, AKA, hardware e ID; click sulle
  intestazioni per l'ordinamento; `r` per aggiornare; `/` per focalizzare il
  filtro; `q` o `Esc` per tornare alla console.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /view
  ```

---

### `/node`
* **Sintassi**: `/node <id|aka|nome>`
* **Parametri**:
  - `<id|aka|nome>` *(obbligatorio)*: Identificativo del nodo da ispezionare. Può essere:
    - ID esadecimale (es. `!45a466e4`)
    - Numero decimale del nodo (es. `1168467684`)
    - Alias breve AKA (es. `CIMO` o `TB01`)
    - Substring del nome completo (es. `Monte-Cimone`)
* **Descrizione**: Genera un **dossier analitico completo** del nodo selezionato all'interno di un pannello a doppia colonna:
  - **Identità & Hardware**: Nome esteso, AKA, Node ID, modello hardware, ruolo del dispositivo e stato licenza radioamatoriale.
  - **Telemetria Radio & Propagazione**: SNR (in dB), hop count, timestamp dell'ultimo pacchetto ricevuto, utilizzo aereo del canale (Channel Utilization) e preset del modem LoRa.
  - **Energia & Sensori Ambientali**: Percentuale batteria, tensione della cella, temperatura (°C), umidità relativa (%) e pressione barometrica (hPa).
  - **Posizione Geografica**: Coordinate GPS, altitudine slm, distanza geodetica stimata dal nodo locale (calcolata con formula Haversine) e link cliccabile verso [OpenStreetMap](https://www.openstreetmap.org/).
  - **Sicurezza PKI**: Chiave crittografica pubblica del nodo (se annunciata).
* **Screenshot Dimostrativo**:
  ![Scheda Analitica Nodo](screenshots/node_detail.svg)
* **Esempi d'uso**:
  ```text
  # Ispezione tramite alias AKA
  mesh-deck [VM290] ❯ /node CIMO

  # Ispezione tramite Node ID esadecimale
  mesh-deck [VM290] ❯ /node !45a466e4

  # Ispezione tramite porzione del nome
  mesh-deck [VM290] ❯ /node Tracker
  ```

---

### `/send`
* **Sintassi**: `/send <testo del messaggio>` oppure digitazione diretta `<testo>`
* **Parametri**:
  - `<testo>` *(obbligatorio)*: Contenuto testuale da trasmettere.
* **Descrizione**: Invia un messaggio broadcast in chiaro su tutta la mesh attraverso il canale radio primario (canale `0`). Tutti i nodi in ascolto sul canale riceveranno il messaggio.
  > [!TIP]
  > In Mesh-Deck non è obbligatorio anteporre `/send`: qualsiasi riga immessa nel prompt che non inizia con uno slash `/` viene automaticamente interpretata come messaggio broadcast e trasmessa sul canale 0.
* **Esempi d'uso**:
  ```text
  # Metodo con comando esplicito
  mesh-deck [VM290] ❯ /send Rete attiva. Test propagazione serale OK.

  # Metodo rapido (senza slash)
  mesh-deck [VM290] ❯ Ciao a tutti da Bologna centro!
  ```

---

### `/dm`
* **Sintassi**: `/dm <id|aka|nome> <testo del messaggio>`
* **Parametri**:
  - `<id|aka|nome>` *(obbligatorio)*: Destinatario del messaggio (risolto automaticamente tramite ID, AKA o nome).
  - `<testo>` *(obbligatorio)*: Contenuto confidenziale del messaggio privato.
* **Descrizione**: Invia un messaggio diretto punto-a-punto (*Direct Message / Private Message*) al nodo specificato. A livello di protocollo Meshtastic, il pacchetto viene indirizzato all'ID numerico univoco del destinatario e cifrato end-to-end con le chiavi negoziate. Nel terminale, i DM sia inviati che ricevuti sono evidenziati con un elegante riquadro neon fucsia/magenta (`#ff007f`).
* **Screenshot Dimostrativo**:
  ![Messaggistica Tattica & DM](screenshots/messaging.svg)
* **Esempi d'uso**:
  ```text
  # Invio DM a un nodo specificando il suo alias
  mesh-deck [VM290] ❯ /dm CIMO Coordinate ricevute, ci vediamo al waypoint 2.

  # Invio DM specificando l'ID esadecimale
  mesh-deck [VM290] ❯ /dm !b8f862d9 Batteria del ripetitore al 35%, procedere con swap.
  ```

---

### `/channels`
* **Sintassi**: `/channels`
* **Parametri**: Nessuno.
* **Descrizione**: Interroga la radio locale ed elenca la configurazione completa di tutti i canali radio memorizzati nel dispositivo. La tabella mostra:
  - **Index**: Numero progressivo del canale (`0` per il canale primario, `1..7` per i secondari).
  - **Nome Canale**: Nome assegnato (es. `LongFast`, `Ops-Emergency`, `Admin`).
  - **Ruolo**: `PRIMARY` o `SECONDARY`.
  - **Uplink / Downlink**: Flag che indicano se il canale inoltra pacchetti verso uplink/downlink MQTT.
  - **Crittografia (PSK)**: Indica se il canale impiega una chiave crittografica personalizzata AES (`Attiva`) oppure la chiave predefinita pubblica di Meshtastic (`Predefinita`).
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /channels
  ```

---

### `/info`
* **Sintassi**: `/info`
* **Parametri**: Nessuno.
* **Descrizione**: Mostra una scheda di diagnostica hardware e radio del dispositivo locale connesso via USB:
  - Porta seriale e stato connessione
  - Nome del nodo locale, Node ID e modello hardware
  - Ruolo operativo (es. `CLIENT`, `ROUTER`) e coordinate GPS (se dotata di ricevitore)
  - Regione RF attiva (es. `EU_868`, `US_915`)
  - Preset modem attivo (es. `LONG_FAST`, `MEDIUM_FAST`, `SHORT_TURBO`)
  - Versione del firmware Meshtastic installato a bordo del microcontrollore
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /info
  ```

---

### `/scan`
* **Sintassi**: `/scan`
* **Parametri**: Nessuno.
* **Descrizione**: Esegue una scansione euristica delle porte USB seriali del sistema operativo per rilevare tutti i dispositivi LoRa Meshtastic attualmente collegati. Mostra la porta (`/dev/ttyACM*`, `/dev/ttyUSB*`), l'hardware identificato, la descrizione del kernel e lo stato: `★ ATTIVO` per il dispositivo attualmente controllato da Mesh-Deck, oppure `Disponibile` per le altre radio collegate.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /scan
  ```

---

### `/switch`
* **Sintassi**: `/switch [porta|indice]`
* **Parametri**:
  - `[porta|indice]` *(opzionale)*: Il percorso della nuova porta seriale (es. `/dev/ttyUSB0`) oppure l'indice numerico progressivo risultante da `/scan` (es. `1`, `2`). Se omesso, Mesh-Deck commuta automaticamente sulla prima porta alternativa rilevata.
* **Descrizione**: Esegue un **hot-switching** a caldo della connessione radio senza richiedere il riavvio di Mesh-Deck. La sessione precedente viene terminata in sicurezza, viene stabilito il collegamento con la nuova radio e l'intero NodeDB viene aggiornato, ridisegnando istantaneamente il banner di stato.
* **Esempi d'uso**:
  ```text
  # Commuta specificando l'indice della lista /scan
  mesh-deck [VM290] ❯ /switch 2

  # Commuta specificando il device path
  mesh-deck [VM290] ❯ /switch /dev/ttyACM1

  # Commuta automaticamente all'altra radio disponibile
  mesh-deck [VM290] ❯ /switch
  ```

---

### `/settings` (o `/config`)
* **Sintassi**: `/settings` oppure `/settings <lang|theme|sort|port> <valore>`.
* **Parametri**:
  - Senza argomenti apre una finestra Textual con selettori per lingua, tema,
    ordinamento dei nodi e porta seriale predefinita.
  - Con argomenti aggiorna direttamente l'impostazione, ad esempio
    `/settings lang en` o `/settings sort snr`.
* **Descrizione**: Le preferenze vengono salvate in
  `~/.config/mesh-deck/settings.json`. La lingua aggiorna subito etichette,
  placeholder e descrizioni dell'autocomplete nella console attiva.

---

### `/banner`
* **Sintassi**: `/banner`
* **Parametri**: Nessuno.
* **Descrizione**: Ristampa il banner tattico di stato Hermes in cima allo schermo. Mostra il nodo locale, la radio port, la regione RF, l'utilizzo aereo del canale e l'elenco dei canali attivi.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /banner
  ```

---

### `/clear`
* **Sintassi**: `/clear`
* **Parametri**: Nessuno.
* **Descrizione**: Pulisce l'intero schermo del terminale per eliminare l'output precedente, mantenendo la cronologia dei comandi e lo stato della connessione attivo.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /clear
  ```

---

### `/quit` (o `/exit`, `/q`)
* **Sintassi**: `/quit`, `/exit`, oppure `/q`
* **Parametri**: Nessuno.
* **Descrizione**: Chiude ordinatamente la sessione seriale, disconnette i thread in background di ascolto radio ed esce da Mesh-Deck salutando con il tradizionale codice radio *"73!"*.
* **Esempio d'uso**:
  ```text
  mesh-deck [VM290] ❯ /quit
  ```

---

## 🔬 4. Approfondimento delle Funzionalità Chiave

### Auto-Discovery USB & Hot-Switching

In scenari reali è frequente collegare al PC contemporaneamente due o più radio LoRa (ad esempio una radio Heltec di test a 868 MHz e un nodo LilyGo o RAK di monitoraggio o relay). 

Mesh-Deck implementa un sottosistema di rilevamento hardware automatico:
1. **Scansione Euristica VID/PID**: Interroga le periferiche seriali attraverso `pyserial` analizzando identificativi dei chip USB-to-UART (Silicon Labs CP210x, WCH CH340/CH341, FTDI, Raspberry Pi RP2040, Espressif JTAG/Serial, Nordic Semiconductor TinyUSB).
2. **Fingerprinting del Modello**: Ricava il modello hardware probabile a partire dalla descrizione di sistema e dalle stringhe del produttore.
3. **Hot-Switching Atomico**: Quando si esegue `/switch`, il modulo
  [`RadioClient`](../src/mesh_deck/core/radio_client.py):
   - Invia la disconnessione pulita alla radio precedente;
   - Chiude il descrittore seriale evitando lock o permessi pendenti;
   - Inizializza la nuova `meshtastic.serial_interface.SerialInterface`;
  - Svuota e ricarica il [`NodeStore`](../src/mesh_deck/core/node_store.py) con il NodeDB della nuova radio;
   - Ricollega i listener PubSub per i messaggi in ingresso;
   - Aggiorna il prompt del terminale con il nuovo alias AKA del nodo.

---

### Node Explorer & Calcolo Distanze Geodetiche

Il componente [`NodeStore`](../src/mesh_deck/core/node_store.py) mantiene lo
stato sincronizzato di tutti i nodi ascoltati via radio.

#### Formula Haversine per la Distanza
Se sia il nodo locale sia il nodo remoto trasmettono le proprie coordinate geografiche (latitudine e longitudine), Mesh-Deck calcola in tempo reale la distanza ortodromica geodetica tra i due punti impiegando la **formula dell'emisenoverso (Haversine)** con raggio terrestre medio $R = 6371.0088\text{ km}$:

$$\Delta\sigma = 2 \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)} \right)$$

$$d = R \cdot \Delta\sigma$$

I risultati vengono formattati in modo leggibile:
- Sotto 1 km: visualizzazione in metri (es. `450 m`).
- Tra 1 e 10 km: visualizzazione con 2 decimali (es. `6.24 km`).
- Oltre 10 km: visualizzazione con 1 decimale (es. `42.8 km`).

#### Filtro e Ordinamento Nodi
È possibile ordinare ed esplorare i nodi in modo flessibile:
- **Per Ultimo Contatto (`last_heard`)**: Permette di identificare subito i nodi attualmente attivi sul canale.
- **Per SNR (`snr`)**: Identifica i ripetitori e client con il miglior margine di segnale.
- **Per Hop Count (`hops`)**: Separa i nodi adiacenti (0 hop) da quelli raggiungibili solo tramite dorsali mesh multi-hop.

---

### Gestione Canali e Messaggistica Tattica

Mesh-Deck distingue chiaramente tra due modalità operative di comunicazione:

1. **Broadcast di Canale**:
   - Messaggi inviati a tutti i partecipanti di un canale (predefinito: `#0 Primary`).
   - Visualizzati come eleganti righe terminali singole con timestamp, tag canale (`#LongFast`), mittente, SNR e testo del messaggio.
2. **Messaggi Diretti Privati (DM)**:
   - Comunicazioni riservate punto-a-punto indirizzate a uno specifico Node ID.
   - Cifratura gestita a livello hardware dal protocollo Meshtastic.
   - Visualizzazione con **pannello di allerta tattico fucsia neon (`#ff007f`)**, garantendo che comunicazioni critiche non vadano perse tra i log di canale.

---

### Streaming Asincrono in Background (Textual)

Uno dei problemi storici delle interfacce CLI/REPL per apparati radio seriali è la corruzione dell'input: se l'utente sta digitando un comando o un messaggio lungo e la radio riceve un pacchetto in background, il testo in arrivo si sovrappone ai caratteri digitati, rendendo illeggibile il prompt.

Mesh-Deck risolve questo problema separando input e output nella stessa app Textual:
- L'ascoltatore radio riceve i pacchetti in modo asincrono tramite il bus di eventi PubSub di Meshtastic.
- Un bridge thread-safe inoltra pannelli e tabelle Rich al log scorrevole della console.
- Quando arriva un messaggio o un aggiornamento di telemetria, viene aggiunto al log; il campo di input e il testo già digitato restano intatti.

---

### Interpretazione Visiva dei Badge e Indicatori

Mesh-Deck impiega un sistema coerente di codifica cromatica e badge per interpretare lo stato della rete a colpo d'occhio:

#### 1. Livelli di Segnale (SNR - Signal-to-Noise Ratio)
| Valore SNR                   | Colore Grafico                 | Stato del Canale                                                                      |
| :--------------------------- | :----------------------------- | :------------------------------------------------------------------------------------ |
| **$\ge +5.0\text{ dB}$**     | `[bold #00ff66]` Verde Neon    | **Segnale Eccellente**: Margine ottimo, propagazione diretta priva di interferenze.   |
| **$0.0 .. +5.0\text{ dB}$**  | `[bold #00f3ff]` Ciano Neon    | **Segnale Buono**: Link LoRa pienamente stabile e affidabile.                         |
| **$-10.0 .. 0.0\text{ dB}$** | `[bold #ffb800]` Giallo Ambra  | **Segnale Marginale**: Possibile perdita occasionale di pacchetti o fading.           |
| **$< -10.0\text{ dB}$**      | `[bold #ff3366]` Rosso Allarme | **Segnale Critico**: Al limite della soglia di decodifica dello spread spectrum LoRa. |
| **`-- dB`**                  | `[dim]` Grigio Fumo            | Telemetria SNR non presente nel pacchetto (es. pacchetto generato localmente).        |

#### 2. Batteria & Alimentazione
| Indicatore          | Colore                         | Significato Operativo                                                                |
| :------------------ | :----------------------------- | :----------------------------------------------------------------------------------- |
| `⚡ USB (4.22V)`     | `[bold #00ff66]` Verde Neon    | Dispositivo alimentato da bus USB o alimentazione esterna fissa (livello $> 100\%$). |
| `> 70% (4.10V)`     | `[bold #00ff66]` Verde Neon    | Batteria a piena carica o alta autonomia.                                            |
| `30% - 70% (3.80V)` | `[bold #ffb800]` Giallo Ambra  | Carica intermedia, normale autonomia operativa.                                      |
| `< 30% (3.55V)`     | `[bold #ff3366]` Rosso Allarme | Batteria quasi scarica: rischio spegnimento imminente del nodo.                      |

#### 3. Ruoli del Dispositivo (Meshtastic Roles)
I ruoli sono formattati visivamente con badge ad alto contrasto:
- ` ROUTER ` *(testo nero su fucsia `#ff007f`)*: Nodo infrastrutturale ad alta quota per routing continuo della rete.
- ` ROUTER_CLI ` *(testo nero su viola fucsia `#d946ef`)*: Router con funzionalità client attive.
- ` REPEATER ` *(testo nero su ambra `#ffb800`)*: Ripetitore a basso consumo per estendere la copertura.
- ` CLIENT ` *(testo nero su verde brillante `#00ff66`)*: Nodo standard utente con display o interfaccia utente.
- ` CLI_MUTE ` *(testo nero su ardesia `#94a3b8`)*: Client passivo in solo ascolto (non ripete pacchetti altrui).
- ` TRACKER ` *(testo nero su ciano elettrico `#00f3ff`)*: Nodo mobile con beacon GPS periodico attivo.
- ` SENSOR ` *(testo nero su azzurro cielo `#38bdf8`)*: Stazione meteo o telemetria ambientale autonoma.
- ` TAK ` / ` TAK_TRACK ` *(testo nero su arancio `#f97316`)*: Nodo integrato con protocolli Team Awareness Kit (ATAK/WinTAK).

#### 4. Hops Away (Propagazione)
- `Diretto (0)` *(verde neon)*: Il pacchetto è stato ricevuto in linea di vista radio diretta dal nodo emittente.
- `1 hop` *(ciano neon)*: Il pacchetto è transitato attraverso un singolo ripetitore intermedio.
- `N hops` *(giallo ambra)*: Il pacchetto ha attraversato 2 o più ripetitori lungo la mesh.

---

## 🔧 5. Troubleshooting & Risoluzione Problemi

### Errore "Permission denied" su `/dev/ttyACM*` o `/dev/ttyUSB*`
- **Causa**: L'utente corrente non appartiene al gruppo che gestisce i device seriali del sistema operativo.
- **Risoluzione**:
  ```bash
  sudo usermod -a -G dialout $USER
  # Su distribuzioni Arch Linux / Manjaro:
  sudo usermod -a -G uucp $USER
  ```
  Riavvia la sessione di shell o esegui `newgrp dialout` per rendere effettive le modifiche.

### Errore "Dispositivo occupato" o "Port is busy"
- **Causa**: Un'altra applicazione ha acquisito il lock esclusivo sulla porta seriale (es. l'estensione Web Meshtastic flasher, il demone `modemmanager`, o un'altra istanza di `meshtastic` CLI).
- **Risoluzione**:
  1. Chiudi eventuali browser che utilizzano WebSerial su Meshtastic.
  2. Su distribuzioni Linux con `ModemManager`, disattiva temporaneamente il servizio che tenta di aprire modem cellulari sulle porte seriali:
     ```bash
     sudo systemctl stop ModemManager
     ```
  3. Controlla quale processo sta bloccando la porta:
     ```bash
     lsof /dev/ttyACM0
     ```

### Il nodo non mostra coordinate GPS o distanza
- **Causa**: Il dispositivo non possiede un modulo GPS integrato, oppure il ricevitore GPS si trova al chiuso e non ha ancora completato il "fix" della costellazione satellitare. Meshtastic segnala coordinate `(0.0, 0.0)` in caso di mancato fix, che Mesh-Deck ignora correttamente per evitare distanze fittizie.
- **Risoluzione**: Sposta il dispositivo vicino a una finestra o all'aperto finché il modulo GPS non aggancia i satelliti.

### Messaggi non ricevuti o radio apparentemente muta
- **Causa**: Canali o preset modem differenti.
- **Risoluzione**: Esegui `/info` e `/channels` per verificare che la regione RF (`EU_868`, `US_915`, ecc.), il preset del modem (es. `LONG_FAST`) e il nome del canale primario coincidano con quelli della rete locale Meshtastic.

---

## 📄 Riferimenti & Licenza

- **Repository Ufficiale**: [github.com/raythekool/mesh-deck](https://github.com/raythekool/mesh-deck)
- **Specifiche Tecniche**: Consulta [REQUIREMENTS.md](../REQUIREMENTS.md) per i dettagli architetturali.
- **Piano di Sviluppo**: Consulta [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) per la roadmap delle funzionalità.
- **Licenza**: Software distribuito con licenza open source [MIT](../LICENSE).
