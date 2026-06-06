# Amazon Price Tracker — Design Spec
**Data:** 2026-06-06  
**Stato:** Approvato

---

## Obiettivo

Bot Telegram self-hosted che monitora i prezzi dei prodotti di una wishlist Amazon pubblica e di prodotti aggiunti manualmente, inviando notifiche quando si raggiunge un prezzo target. Deployato come singolo container Docker su ZimaBoard con CasaOS.

---

## Architettura

Container singolo Python con:
- Telegram bot asincrono (`python-telegram-bot` v20+)
- Scheduler interno (`APScheduler`)
- Keepa API per i dati di prezzo
- Scraping HTTP per import wishlist
- SQLite per la persistenza

```
[container: price-tracker]
├── bot.py            ← handler comandi Telegram
├── scheduler.py      ← price check ogni 4h + report venerdì 19:00
├── keepa_client.py   ← wrapper Keepa API
├── scraper.py        ← scraping wishlist Amazon pubblica
├── database.py       ← operazioni SQLite
├── config.py         ← env vars
└── main.py           ← entry point (avvia bot + scheduler)

[volume: ./data]
└── tracker.db        ← SQLite persistente
```

---

## Data Model

### Tabella `products`

| campo | tipo | note |
|---|---|---|
| `id` | INTEGER PK | |
| `asin` | TEXT UNIQUE | codice prodotto Amazon |
| `name` | TEXT | nome prodotto |
| `url` | TEXT | link Amazon |
| `current_price` | REAL | ultimo prezzo rilevato |
| `target_price` | REAL | soglia alert (NULL = solo tracciamento) |
| `currency` | TEXT | default EUR |
| `source` | TEXT | `wishlist` o `manual` |
| `last_alert_at` | TEXT | ISO timestamp ultimo alert inviato |
| `added_at` | TEXT | ISO timestamp aggiunta |

### Tabella `price_history`

| campo | tipo | note |
|---|---|---|
| `id` | INTEGER PK | |
| `product_id` | INTEGER FK → products.id | |
| `price` | REAL | |
| `checked_at` | TEXT | ISO timestamp |

---

## Interfaccia Telegram

Il bot accetta comandi **solo dal `TELEGRAM_CHAT_ID` configurato** — tutti gli altri vengono ignorati silenziosamente.

| comando | descrizione |
|---|---|
| `/start` | Benvenuto + lista comandi |
| `/import` | Importa prodotti dalla wishlist Amazon pubblica |
| `/add <url>` | Aggiunge un prodotto da URL Amazon |
| `/list` | Lista prodotti con prezzo attuale vs target |
| `/remove <id>` | Rimuove un prodotto dal tracciamento |
| `/target <id> <prezzo>` | Imposta o aggiorna il prezzo target |
| `/check` | Forza un controllo prezzi immediato |
| `/status` | Ultima verifica, prossima verifica programmata |

### Formato alert

```
🔔 Prezzo raggiunto!
Sony WH-1000XM5
💰 Prezzo attuale: €219,00
🎯 Il tuo target: €220,00
🔗 Acquista ora
```

### Formato report settimanale

```
📊 Report settimanale prezzi
─────────────────────────
✅ Sony WH-1000XM5     €219 / target €220
❌ iPad Air 11"        €749 / target €600
❌ Kindle Paperwhite   €159 / target €120
```

---

## Logica Price Check

**Scheduling:**
- Price check: ogni 4 ore (`CHECK_INTERVAL_HOURS=4`)
- Report settimanale: venerdì alle 19:00 (`REPORT_DAY=friday`, `REPORT_TIME=19:00`)

**Flusso per ogni prodotto:**
1. Chiama Keepa API con ASIN
2. Salva prezzo in `price_history`
3. Aggiorna `current_price` in `products`
4. Se `target_price` impostato AND `current_price ≤ target_price`:
   - Se prezzo cambiato rispetto all'ultimo check → invia alert
   - Se prezzo invariato AND `last_alert_at` < 24h fa → salta
   - Se prezzo invariato AND `last_alert_at` ≥ 24h fa → invia alert

**Keepa API — limiti free tier:**
- 250 token/giorno, ~1 token per ASIN
- Con 4h di intervallo (6 check/giorno): supporta fino a ~40 prodotti senza superare i limiti
- Oltre 40 prodotti: considerare piano a pagamento Keepa (~€5/mese)

---

## Wishlist Import

**Flusso `/import`:**
1. HTTP GET sulla wishlist pubblica Amazon con headers browser-like
2. BeautifulSoup estrae ASIN dai link `/dp/<ASIN>/`
3. Per ogni ASIN non già presente in DB: Keepa lookup per nome + prezzo
4. Inserimento in DB con `source=wishlist`, `target_price=NULL`
5. Risposta: "Importati N prodotti, M già presenti"

**Flusso `/add <url>`:**
1. Regex estrae ASIN dall'URL
2. Keepa lookup per nome + prezzo
3. Inserimento in DB con `source=manual`
4. Risposta con prodotto aggiunto + invito a impostare target con `/target`

---

## Struttura File

```
price-tracker/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── src/
│   ├── main.py
│   ├── bot.py
│   ├── scheduler.py
│   ├── keepa_client.py
│   ├── scraper.py
│   ├── database.py
│   └── config.py
└── data/                  # volume Docker, contiene tracker.db
```

---

## Deployment (CasaOS)

**`docker-compose.yml`:**
```yaml
services:
  price-tracker:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
```

**`.env.example`:**
```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
KEEPA_API_KEY=
AMAZON_WISHLIST_URL=https://www.amazon.it/hz/wishlist/ls/XXXXXX
CHECK_INTERVAL_HOURS=4
REPORT_DAY=friday
REPORT_TIME=19:00
```

Deploy su CasaOS: "Custom App" → incolla il compose file → avvia.

---

## Evoluzioni Future (fuori scope v1)

- Web UI per gestione wishlist (FastAPI + HTML)
- Grafici storici prezzi per prodotto
- Supporto wishlist privata (login Amazon)
- Notifiche su variazioni percentuali significative
