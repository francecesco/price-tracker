# 🛒 Amazon Price Tracker

Bot Telegram self-hosted che monitora i prezzi della tua wishlist Amazon.it e ti avvisa quando è il momento di comprare.

Gira come container Docker sulla tua ZimaBoard (o qualsiasi home server con CasaOS) — nessun servizio esterno, nessun costo, dati tuoi.

---

## Come funziona

1. Colleghi la tua wishlist Amazon pubblica
2. Il bot importa tutti i prodotti usando un browser headless (Playwright)
3. Ogni 30 minuti controlla i prezzi direttamente su Amazon.it
4. Quando un prodotto scende sotto il tuo target, ricevi un alert con un pulsante per comprarlo

```
🔔 Prezzo raggiunto!
Sony WH-1000XM5
💰 Prezzo attuale: €219,00
🎯 Il tuo target: €220,00

[ 🛒 Acquista ora ]
```

---

## Funzionalità

- **Import automatico** della wishlist completa (nessun limite di prodotti)
- **Sincronizzazione** — aggiunge i nuovi prodotti, rimuove quelli che hai tolto dalla wishlist
- **Alert con pulsante** diretto alla pagina Amazon quando il prezzo raggiunge il target
- **Anti-spam** — una notifica ogni 24h se il prezzo rimane invariato, immediata se scende ulteriormente
- **Safety check** — avvisa se il prodotto a un certo link è cambiato (ASIN riutilizzato)
- **Report settimanale** ogni venerdì alle 19:00 con lo stato di tutti i prodotti
- **Storico prezzi** salvato nel database per ogni prodotto
- Accesso riservato solo a te (il tuo chat ID)

---

## Prerequisiti

- Docker e Docker Compose sull'host
- Un bot Telegram — crealo su [@BotFather](https://t.me/BotFather)
- Il tuo Telegram Chat ID — ottienilo da [@userinfobot](https://t.me/userinfobot)
- Una wishlist Amazon.it impostata come **pubblica**

---

## Setup

Il bot gira su qualsiasi macchina con Docker — ZimaBoard, Mac mini, Proxmox, VPS, Linux generico. I passi sono identici su tutti i sistemi, cambia solo come lanci il terminale.

> **Installazioni multiple:** ogni installazione è indipendente. Clona il repo in cartelle diverse (es. `~/price-tracker-casa` e `~/price-tracker-lavoro`), ognuna con il suo `.env` e il suo `./data`. Puoi usare lo stesso bot Telegram o bot diversi.

### 1. Clona il repository

```bash
git clone https://github.com/francecesco/price-tracker.git price-tracker
cd price-tracker
```

### 2. Configura le variabili d'ambiente

```bash
cp .env.example .env
nano .env          # oppure: vim .env  /  open .env (Mac)
```

Compila con i tuoi valori:

```env
TELEGRAM_BOT_TOKEN=123456789:AABBccDDeeFFggHH...
TELEGRAM_CHAT_ID=987654321
AMAZON_WISHLIST_URL=https://www.amazon.it/hz/wishlist/ls/XXXXXXXXXXXXXX
```

Variabili opzionali (i default vanno bene per iniziare):

| Variabile | Default | Descrizione |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | `30` | Minuti tra un controllo e il successivo |
| `REPORT_DAY` | `friday` | Giorno del report settimanale (in inglese) |
| `REPORT_TIME` | `19:00` | Orario del report |
| `DB_PATH` | `/app/data/tracker.db` | Percorso database (interno al container) |

### 3. Avvia

```bash
docker compose up -d
```

La prima build scarica Playwright + Chromium (~300MB) — ci vogliono qualche minuto. I riavvii successivi sono istantanei.

```bash
docker logs -f price-tracker   # verifica che sia partito
```

Dovresti vedere:
```
Database inizializzato: /app/data/tracker.db
Scheduler avviato: check ogni 30min, report friday alle 19:00
Bot avviato. In ascolto...
```

### 4. Prima configurazione su Telegram

```
/import          → importa la wishlist (~30 secondi)
/list            → verifica i prodotti importati
/targetall 20    → imposta il target al -20% per tutti
```

---

## Note per piattaforme specifiche

**CasaOS (ZimaBoard o simili)**
Puoi deployare via terminale come sopra, oppure usare l'interfaccia "Custom App" di CasaOS: incolla il contenuto di `docker-compose.yml` nell'editor e imposta le variabili d'ambiente dalla UI.

**Mac (Mac mini, MacBook)**
Docker Desktop deve essere in esecuzione. Tutto il resto è identico. I dati vengono salvati in `./data` nella cartella del progetto.

**Proxmox**
Crea un container LXC con Debian/Ubuntu, installa Docker, poi segui i passi normali. In alternativa, usa una VM con Docker.

**VPS / server remoto**
Funziona su qualsiasi distribuzione Linux con Docker installato. Per farlo girare in background anche dopo il logout usa `docker compose up -d` (già incluso nei passi).

---

## Aggiornamenti

```bash
docker compose down && git pull && docker compose up -d --build
```

> I dati nel volume `./data` non vengono mai toccati dagli aggiornamenti.

---

## Comandi Telegram

### Wishlist

| Comando | Descrizione |
|---|---|
| `/import` | Importa tutti i prodotti dalla wishlist (usa Playwright, ~30 sec) |
| `/sync` | Aggiunge i nuovi prodotti dalla wishlist, rimuove quelli eliminati. I prodotti aggiunti con `/add` vengono mantenuti. |

### Prodotti

| Comando | Descrizione |
|---|---|
| `/add <url>` | Aggiunge un prodotto manualmente tramite URL Amazon |
| `/list` | Mostra tutti i prodotti con ID, prezzo attuale e target |
| `/target <id> <prezzo>` | Imposta il target per un prodotto — es. `/target 3 199.99` o `/target 3 199,99` |
| `/targetall <sconto%>` | Imposta il target per **tutti** i prodotti al prezzo attuale meno X% — es. `/targetall 20` |
| `/remove <id>` | Rimuove un prodotto dal tracciamento |

### Controllo

| Comando | Descrizione |
|---|---|
| `/check` | Forza un controllo prezzi immediato |
| `/status` | Prossimo check automatico e prossimo report |

### Utilità

| Comando | Descrizione |
|---|---|
| `/clear` | Mostra quanti prodotti ci sono e chiede conferma |
| `/clear conferma` | Svuota completamente il database |
| `/testalert` | Simula un alert di prezzo raggiunto per il prodotto 1 — utile per testare il pulsante. Puoi specificare un ID: `/testalert 5` |
| `/debug` | Avvia Playwright e conta quanti prodotti trova nella wishlist |

---

## Notifiche automatiche

Il bot invia messaggi senza che tu faccia nulla.

**Alert prezzo raggiunto** — con pulsante diretto ad Amazon:
```
🔔 Prezzo raggiunto!
Sony WH-1000XM5
💰 Prezzo attuale: €219,00
🎯 Il tuo target: €220,00

[ 🛒 Acquista ora ]
```

**Avviso prodotto cambiato** — se il nome del prodotto cambia significativamente allo stesso URL:
```
⚠️ Prodotto cambiato?
ID 3 — il nome non corrisponde più:
Era: Sony WH-1000XM5
Ora: Logitech MX Master Mouse
```

**Report settimanale** — ogni venerdì alle 19:00:
```
📊 Report settimanale prezzi
─────────────────────────
✅ Sony WH-1000XM5     €219 / target €220
❌ iPad Air 11"        €749 / target €600
❌ Kindle Paperwhite   €159 / target €120
```

---

## Sviluppo locale

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # compila con i valori reali
pytest                 # esegui i test
python src/main.py     # avvia il bot
```

---

## Architettura

| Modulo | Responsabilità |
|---|---|
| `config.py` | Legge e valida le variabili d'ambiente |
| `database.py` | SQLite: prodotti e storico prezzi |
| `scraper.py` | Playwright per la wishlist, requests per i prezzi dei singoli prodotti |
| `scheduler.py` | APScheduler: check prezzi ogni N minuti, report settimanale |
| `bot.py` | Handler comandi Telegram |
| `main.py` | Entry point: collega tutti i moduli e avvia il polling |

---

## Note

- **Wishlist pubblica** — deve essere impostata come pubblica su Amazon, altrimenti lo scraping non trova prodotti.
- **Prodotti non disponibili** — Amazon nasconde dalle wishlist pubbliche i prodotti fuori produzione. È normale non trovarli.
- **Prezzi N/D** — i prezzi dei singoli prodotti vengono estratti con HTTP diretto. Se Amazon cambia la struttura HTML, alcuni prezzi potrebbero non essere rilevati. In quel caso aggiorna i selettori in `src/scraper.py`.
- **Dimensione immagine** — il container include Chromium (~300MB). La prima build richiede qualche minuto.
