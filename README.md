# Amazon Price Tracker

## Descrizione

Bot Telegram self-hosted che monitora i prezzi dei prodotti Amazon.it. Legge una wishlist pubblica Amazon e/o prodotti aggiunti manualmente, controlla i prezzi a intervalli regolari e invia un'allerta su Telegram quando un prodotto raggiunge il prezzo target. Ogni venerdì alle 19:00 invia un report settimanale con lo stato di tutti i prodotti tracciati.

---

## Funzionalità

- Importa automaticamente i prodotti da una wishlist pubblica Amazon.it
- Aggiunta manuale di prodotti tramite URL Amazon
- Controllo prezzi automatico ogni 30 minuti (configurabile)
- Allerta Telegram quando il prezzo scende sotto il target impostato
- Report settimanale ogni venerdì alle 19:00 (giorno e orario configurabili)
- Scraping diretto di Amazon.it — nessuna API esterna, nessun servizio a pagamento
- Accesso riservato al solo proprietario del bot
- Gira come singolo container Docker (adatto a CasaOS / ZimaBoard)
- Database SQLite locale — i dati persistono nel volume `./data`

---

## Prerequisiti

- Docker e Docker Compose installati sull'host
- Un bot Telegram (token ottenuto da BotFather)
- Il proprio Telegram Chat ID
- L'URL di una wishlist Amazon.it pubblica (opzionale se si aggiungono prodotti solo manualmente)

---

## Configurazione

### 1. Creare il bot Telegram e ottenere il token

1. Apri Telegram e cerca `@BotFather`
2. Invia il comando `/newbot`
3. Scegli un nome e uno username per il bot (lo username deve finire in `bot`, es. `MyPriceTrackerBot`)
4. BotFather restituirà un token nel formato `123456789:AABBccDDeeFFggHH...` — copialo, è il valore di `TELEGRAM_BOT_TOKEN`

### 2. Ottenere il proprio Chat ID

1. Cerca `@userinfobot` su Telegram e invia `/start`
2. Il bot risponderà con il tuo `Id` numerico — è il valore di `TELEGRAM_CHAT_ID`

> In alternativa: avvia il tuo bot appena creato, poi visita `https://api.telegram.org/bot<TOKEN>/getUpdates` e cerca il campo `"id"` dentro `"from"` dopo aver inviato un messaggio al bot.

### 3. Ottenere l'URL della wishlist Amazon

1. Vai su Amazon.it e apri la wishlist da monitorare
2. Assicurati che sia impostata come **pubblica** (Impostazioni wishlist → Privacy → Pubblica)
3. Copia l'URL dalla barra del browser — ha il formato `https://www.amazon.it/hz/wishlist/ls/XXXXXXXXXXXXXX`

### 4. Variabili d'ambiente

| Variabile | Obbligatoria | Default | Descrizione |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Sì | — | Token del bot fornito da BotFather |
| `TELEGRAM_CHAT_ID` | Sì | — | Il tuo Telegram user ID numerico |
| `AMAZON_WISHLIST_URL` | Sì | — | URL della wishlist pubblica Amazon.it |
| `CHECK_INTERVAL_MINUTES` | No | `30` | Minuti tra un controllo prezzi e il successivo |
| `REPORT_DAY` | No | `friday` | Giorno della settimana per il report (in inglese) |
| `REPORT_TIME` | No | `19:00` | Orario del report settimanale (formato HH:MM) |
| `DB_PATH` | No | `/app/data/tracker.db` | Percorso del database SQLite (interno al container) |

---

## Deploy su CasaOS

### 1. Clonare il repository

```bash
git clone <url-repo> price-tracker
cd price-tracker
```

### 2. Creare il file `.env`

```bash
cp .env.example .env
```

### 3. Compilare il file `.env`

Apri `.env` con un editor e inserisci i valori ottenuti nella sezione Configurazione:

```env
TELEGRAM_BOT_TOKEN=123456789:AABBccDDeeFFggHH...
TELEGRAM_CHAT_ID=987654321
AMAZON_WISHLIST_URL=https://www.amazon.it/hz/wishlist/ls/XXXXXXXXXXXXXX
CHECK_INTERVAL_MINUTES=30
REPORT_DAY=friday
REPORT_TIME=19:00
```

### 4. Avviare il container

```bash
docker compose up -d
```

Il container si riavvia automaticamente in caso di crash o reboot del sistema (`restart: unless-stopped`).

### 5. Verificare i log

```bash
docker logs -f price-tracker
```

### 6. Fermare il bot

```bash
docker compose down
```

> I dati del database sono persistiti nella cartella `./data` sul host. Non vengono persi tra riavvii o aggiornamenti del container.

---

## Comandi Telegram

Tutti i comandi sono accessibili solo dall'utente il cui ID corrisponde a `TELEGRAM_CHAT_ID`.

| Comando | Descrizione |
|---|---|
| `/start` | Mostra l'elenco dei comandi disponibili |
| `/import` | Importa i prodotti dalla wishlist Amazon configurata |
| `/add <url>` | Aggiunge un singolo prodotto tramite URL Amazon |
| `/list` | Mostra tutti i prodotti in tracciamento con prezzi e target |
| `/remove <id>` | Rimuove un prodotto dal tracciamento (usa `/list` per vedere gli ID) |
| `/target <id> <prezzo>` | Imposta il prezzo target per un prodotto (es. `/target 3 199.99`) |
| `/check` | Forza un controllo immediato dei prezzi |
| `/status` | Mostra l'orario del prossimo check automatico e del prossimo report |

---

## Sviluppo locale

### Installare le dipendenze

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configurare le variabili d'ambiente

```bash
cp .env.example .env
# Compilare .env con i valori reali
```

### Eseguire i test

```bash
pytest
```

### Avviare il bot in locale (senza Docker)

```bash
python src/main.py
```

---

## Architettura

Il progetto è contenuto in `src/` e composto da sei moduli:

| File | Responsabilità |
|---|---|
| `config.py` | Carica e valida le variabili d'ambiente tramite dataclass `Config` |
| `database.py` | Gestisce il database SQLite: CRUD su prodotti e storico prezzi |
| `scraper.py` | Scraping HTTP di Amazon.it per estrarre prezzi dalla wishlist e dalle pagine prodotto |
| `scheduler.py` | Pianifica il job di controllo prezzi (ogni N ore) e il report settimanale (APScheduler) |
| `bot.py` | Definisce i command handler Telegram e la funzione `build_application` |
| `main.py` | Entry point: inizializza tutto, collega scheduler e bot, avvia il polling |

Il database SQLite viene salvato in `/app/data/tracker.db` all'interno del container, mappato su `./data/tracker.db` sul host tramite il volume dichiarato in `docker-compose.yml`.

---

## Note

- **Stabilità dello scraping**: il bot estrae i prezzi direttamente dall'HTML di Amazon.it senza API ufficiali. Se Amazon modifica la struttura della pagina, lo scraper potrebbe smettere di funzionare e restituire `N/D` per alcuni o tutti i prodotti. In quel caso è necessario aggiornare i selettori in `src/scraper.py`.
- **Wishlist pubblica**: la wishlist deve essere impostata come pubblica su Amazon, altrimenti lo scraping fallisce senza errori evidenti.
- **Rate limiting**: Amazon può bloccare temporaneamente le richieste se effettuate troppo frequentemente. L'intervallo di default di 4 ore è sufficiente per evitare problemi nella maggior parte dei casi.
