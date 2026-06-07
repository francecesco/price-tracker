# Amazon Price Tracker

## Descrizione

Bot Telegram self-hosted che monitora i prezzi dei prodotti Amazon.it. Importa l'intera wishlist pubblica tramite browser headless (Playwright), controlla i prezzi ogni 30 minuti e invia un'allerta su Telegram quando un prodotto raggiunge il prezzo target. Ogni venerdì alle 19:00 invia un report settimanale con lo stato di tutti i prodotti.

---

## Funzionalità

- Importa automaticamente **tutti** i prodotti da una wishlist pubblica Amazon.it (browser headless, nessun limite di pagina)
- Aggiunta manuale di prodotti tramite URL Amazon
- Sincronizzazione wishlist: aggiunge i nuovi prodotti, rimuove quelli eliminati dalla lista
- Controllo prezzi automatico ogni 30 minuti con delay casuale tra le richieste
- Allerta Telegram quando il prezzo scende sotto il target impostato
- Anti-spam: una notifica ogni 24h per prodotto se il prezzo rimane invariato, immediata se scende ulteriormente
- Avviso di sicurezza se il nome di un prodotto cambia allo stesso URL (prodotto sostituito)
- Report settimanale ogni venerdì alle 19:00
- Storico prezzi salvato nel database per ogni prodotto
- Accesso riservato al solo proprietario del bot
- Gira come singolo container Docker (adatto a CasaOS / ZimaBoard)

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
git clone https://github.com/francecesco/price-tracker.git price-tracker
cd price-tracker
```

### 2. Creare il file `.env`

```bash
cp .env.example .env
```

### 3. Compilare il file `.env`

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

Il primo avvio scarica l'immagine base e installa Playwright + Chromium (~300MB, richiede qualche minuto). I successivi riavvii sono istantanei.

Il container si riavvia automaticamente in caso di crash o reboot (`restart: unless-stopped`).

### 5. Verificare i log

```bash
docker logs -f price-tracker
```

### 6. Prima importazione

Una volta avviato, su Telegram:

```
/import   ← importa tutta la wishlist
/list     ← verifica i prodotti importati
/target 1 199.99   ← imposta il target per il prodotto con ID 1
```

### 7. Aggiornamenti futuri

```bash
docker compose down && git pull && docker compose up -d
```

> I dati del database persistono nella cartella `./data` sul host e non vengono mai persi tra riavvii o aggiornamenti.

---

## Guida ai comandi Telegram

Tutti i comandi sono accessibili solo dall'utente il cui ID corrisponde a `TELEGRAM_CHAT_ID`.

### Gestione wishlist

| Comando | Descrizione |
|---|---|
| `/import` | Importa tutti i prodotti dalla wishlist Amazon (usa Playwright, ~30 secondi) |
| `/sync` | Sincronizza la wishlist: aggiunge i nuovi prodotti, rimuove quelli eliminati dalla lista. I prodotti aggiunti manualmente con `/add` vengono mantenuti. |

### Gestione prodotti

| Comando | Esempio | Descrizione |
|---|---|---|
| `/add <url>` | `/add https://www.amazon.it/dp/B09XS7JWHH` | Aggiunge un prodotto manualmente tramite URL Amazon |
| `/list` | `/list` | Mostra tutti i prodotti con ID, prezzo attuale e target |
| `/target <id> <prezzo>` | `/target 3 199.99` oppure `/target 3 199,99` | Imposta o aggiorna il prezzo target (accetta sia `.` che `,` come separatore decimale) |
| `/targetall <sconto%>` | `/targetall 20` | Imposta il target di **tutti** i prodotti al prezzo attuale meno la percentuale indicata (es. 20% → target = prezzo × 0.80) |
| `/remove <id>` | `/remove 3` | Rimuove definitivamente un prodotto dal tracciamento |

### Controllo e stato

| Comando | Descrizione |
|---|---|
| `/check` | Forza un controllo immediato dei prezzi senza aspettare il prossimo ciclo automatico |
| `/status` | Mostra la data/ora del prossimo check automatico e del prossimo report settimanale |

### Manutenzione

| Comando | Descrizione |
|---|---|
| `/clear` | Mostra un avviso con il numero di prodotti e chiede conferma |
| `/clear conferma` | Svuota completamente il database (prodotti + storico prezzi) |
| `/debug` | Avvia Playwright e conta quanti prodotti trova nella wishlist — utile per diagnosticare problemi di scraping |

### Notifiche automatiche

Il bot invia messaggi automatici senza che tu faccia nulla:

- **Alert prezzo** — quando il prezzo di un prodotto scende sotto il target:
  ```
  🔔 Prezzo raggiunto!
  Sony WH-1000XM5
  💰 Prezzo attuale: €219,00
  🎯 Il tuo target: €220,00
  🔗 Acquista ora
  ```

- **Avviso prodotto cambiato** — se il nome del prodotto a un certo URL cambia significativamente (prodotto sostituito):
  ```
  ⚠️ Prodotto cambiato?
  ID 3 — il nome non corrisponde più:
  Era: Sony WH-1000XM5
  Ora: Logitech MX Master Mouse
  ```

- **Report settimanale** — ogni venerdì alle 19:00 (o nel giorno/orario configurato):
  ```
  📊 Report settimanale prezzi
  ─────────────────────────
  ✅ Sony WH-1000XM5     €219 / target €220
  ❌ iPad Air 11"        €749 / target €600
  ```

---

## Sviluppo locale

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Compilare .env con i valori reali

pytest          # esegue i test
python src/main.py   # avvia il bot
```

---

## Architettura

| File | Responsabilità |
|---|---|
| `config.py` | Carica e valida le variabili d'ambiente |
| `database.py` | SQLite: CRUD su `products` e `price_history` |
| `scraper.py` | Playwright per la wishlist, requests per i singoli prodotti |
| `scheduler.py` | APScheduler: check prezzi ogni N minuti, report settimanale |
| `bot.py` | Handler comandi Telegram, `build_application` |
| `main.py` | Entry point: wiring config + DB + bot + scheduler |

Il database SQLite è in `/app/data/tracker.db` nel container, mappato su `./data/tracker.db` sull'host.

---

## Note

- **Wishlist pubblica**: deve essere impostata come pubblica su Amazon, altrimenti lo scraping non trova prodotti.
- **Prodotti non disponibili**: Amazon nasconde dalle wishlist pubbliche i prodotti non più disponibili — è normale non trovarli.
- **Stabilità dello scraping**: i prezzi dei singoli prodotti vengono estratti da richieste HTTP dirette senza JavaScript. Se Amazon cambia la struttura HTML, alcuni prezzi potrebbero risultare `N/D` — aggiornare i selettori in `src/scraper.py`.
- **Dimensione immagine Docker**: il container include Chromium (~300MB). La prima build richiede qualche minuto di download.
