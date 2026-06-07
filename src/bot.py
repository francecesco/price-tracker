import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


def _owner_only(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        if update.effective_user.id != context.bot_data["chat_id"]:
            logger.warning("Accesso negato a user_id=%s", update.effective_user.id)
            return
        return await handler(update, context)
    return wrapper


@_owner_only
async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Amazon Price Tracker*\n\n"
        "Comandi disponibili:\n"
        "/import — importa dalla wishlist Amazon\n"
        "/sync — sincronizza wishlist (aggiunge nuovi, rimuove rimossi)\n"
        "/add <url> — aggiungi prodotto manualmente\n"
        "/list — mostra tutti i prodotti\n"
        "/remove <id> — rimuovi prodotto\n"
        "/target <id> <prezzo> — imposta target\n"
        "/targetall <sconto%> — imposta target per tutti (-X%)\n"
        "/check — controlla prezzi ora\n"
        "/clear conferma — svuota il database\n"
        "/status — stato del bot"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@_owner_only
async def _cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_all_products
    products = get_all_products(context.bot_data["db_path"])

    if not products:
        await update.message.reply_text("Nessun prodotto in tracciamento.")
        return

    lines = []
    for p in products:
        price_str = f"€{p.current_price:.2f}" if p.current_price else "N/D"
        target_str = f"🎯 €{p.target_price:.2f}" if p.target_price else "nessun target"
        icon = "✅" if (p.current_price and p.target_price and p.current_price <= p.target_price) else "📦"
        lines.append(f"{icon} `{p.id}` *{p.name[:40]}*\n    💰 {price_str} — {target_str}")

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@_owner_only
async def _cmd_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import scrape_wishlist
    from database import get_product_by_asin, add_product

    db_path = context.bot_data["db_path"]
    wishlist_url = context.bot_data["wishlist_url"]

    await update.message.reply_text("⏳ Importazione wishlist in corso...")

    try:
        items = await scrape_wishlist(wishlist_url)
    except Exception as e:
        await update.message.reply_text(f"❌ Errore scraping wishlist: {e}")
        return

    if not items:
        await update.message.reply_text(
            "❌ Nessun prodotto trovato nella wishlist.\n"
            "Verifica che sia impostata come *pubblica* e che l'URL nel `.env` sia corretto.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    new_items = [i for i in items if not get_product_by_asin(db_path, i["asin"])]
    if not new_items:
        await update.message.reply_text(f"Tutti i {len(items)} prodotti della wishlist sono già in tracciamento.")
        return

    for item in new_items:
        add_product(db_path, item["asin"], item["name"], item["url"], item["price"], "wishlist")

    skipped = len(items) - len(new_items)
    msg = f"✅ Importati {len(new_items)} prodotti"
    if skipped:
        msg += f", {skipped} già presenti."
    await update.message.reply_text(msg)


@_owner_only
async def _cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import fetch_product_info, _extract_asin_from_url
    from database import get_product_by_asin, add_product

    if not context.args:
        await update.message.reply_text("Uso: /add <url_amazon>")
        return

    db_path = context.bot_data["db_path"]
    url = context.args[0]

    asin = _extract_asin_from_url(url)
    if not asin:
        await update.message.reply_text("URL non valido. Deve contenere /dp/ASIN.")
        return

    if get_product_by_asin(db_path, asin):
        await update.message.reply_text("Prodotto già in tracciamento.")
        return

    await update.message.reply_text("⏳ Recupero informazioni...")
    info = fetch_product_info(url)
    if not info:
        await update.message.reply_text("Prodotto non trovato o non raggiungibile.")
        return

    product = add_product(db_path, info["asin"], info["name"], info["url"], info["price"], "manual")
    price_str = f"€{info['price']:.2f}" if info["price"] else "N/D"
    await update.message.reply_text(
        f"✅ Aggiunto: *{info['name']}*\n"
        f"💰 Prezzo attuale: {price_str}\n"
        f"Imposta target con: /target {product.id} <prezzo>",
        parse_mode=ParseMode.MARKDOWN,
    )


@_owner_only
async def _cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_product_by_id, remove_product

    if not context.args:
        await update.message.reply_text("Uso: /remove <id>")
        return

    db_path = context.bot_data["db_path"]
    try:
        product_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID non valido. Usa /list per vedere gli ID.")
        return

    product = get_product_by_id(db_path, product_id)
    if not product:
        await update.message.reply_text(f"Prodotto con ID {product_id} non trovato.")
        return

    remove_product(db_path, product_id)
    await update.message.reply_text(f"✅ Rimosso: {product.name}")


@_owner_only
async def _cmd_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_product_by_id, update_product_target

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /target <id> <prezzo>")
        return

    db_path = context.bot_data["db_path"]
    try:
        product_id = int(context.args[0])
        target = float(context.args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text("ID o prezzo non valido. Esempio: /target 3 199.99")
        return

    product = get_product_by_id(db_path, product_id)
    if not product:
        await update.message.reply_text(f"Prodotto con ID {product_id} non trovato.")
        return

    update_product_target(db_path, product_id, target)
    await update.message.reply_text(
        f"🎯 Target impostato: *{product.name}* → €{target:.2f}",
        parse_mode=ParseMode.MARKDOWN,
    )


@_owner_only
async def _cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Controllo prezzi in corso...")
    await context.bot_data["run_price_check"]()
    await update.message.reply_text("✅ Controllo completato.")


@_owner_only
async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler = context.bot_data["scheduler"]
    check_job = scheduler.get_job("price_check")
    report_job = scheduler.get_job("weekly_report")

    check_next = check_job.next_run_time.strftime("%d/%m/%Y %H:%M") if check_job else "N/D"
    report_next = report_job.next_run_time.strftime("%d/%m/%Y %H:%M") if report_job else "N/D"

    await update.message.reply_text(
        f"🤖 *Bot attivo*\n"
        f"⏰ Prossimo check: {check_next}\n"
        f"📊 Prossimo report: {report_next}",
        parse_mode=ParseMode.MARKDOWN,
    )


@_owner_only
async def _cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    from database import get_all_products

    db_path = context.bot_data["db_path"]

    if not context.args or context.args[0] != "conferma":
        count = len(get_all_products(db_path))
        await update.message.reply_text(
            f"⚠️ Stai per eliminare *{count} prodotti* e tutto lo storico prezzi.\n"
            f"Invia /clear conferma per procedere.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM price_history")
        conn.execute("DELETE FROM products")
    await update.message.reply_text("✅ Database svuotato.")


@_owner_only
async def _cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import scrape_wishlist
    from database import get_all_products, get_product_by_asin, add_product, remove_product

    db_path = context.bot_data["db_path"]
    wishlist_url = context.bot_data["wishlist_url"]

    await update.message.reply_text("⏳ Sincronizzazione wishlist in corso...")

    try:
        items = await scrape_wishlist(wishlist_url)
    except Exception as e:
        await update.message.reply_text(f"❌ Errore scraping wishlist: {e}")
        return

    if not items:
        await update.message.reply_text(
            "❌ Nessun prodotto trovato nella wishlist.\n"
            "Verifica che sia impostata come *pubblica*.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    wishlist_asins = {i["asin"] for i in items}
    current_products = get_all_products(db_path)

    added = 0
    for item in items:
        if not get_product_by_asin(db_path, item["asin"]):
            add_product(db_path, item["asin"], item["name"], item["url"], item["price"], "wishlist")
            added += 1

    removed = 0
    for p in current_products:
        if p.source == "wishlist" and p.asin not in wishlist_asins:
            remove_product(db_path, p.id)
            removed += 1

    total = len(get_all_products(db_path))
    await update.message.reply_text(
        f"✅ Sincronizzazione completata\n"
        f"➕ Aggiunti: {added}\n"
        f"➖ Rimossi dalla wishlist: {removed}\n"
        f"📦 Totale in tracciamento: {total}"
    )


@_owner_only
async def _cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import scrape_wishlist

    wishlist_url = context.bot_data["wishlist_url"]
    await update.message.reply_text("⏳ Avvio browser headless, attendi ~30 secondi...")

    try:
        items = await scrape_wishlist(wishlist_url)
        sample = ", ".join(i["asin"] for i in items[:5])
        await update.message.reply_text(
            f"🔍 *Debug Playwright*\n"
            f"📦 Prodotti trovati: *{len(items)}*\n"
            f"Esempi: `{sample}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {e}")


@_owner_only
async def _cmd_targetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_all_products, update_product_target

    if not context.args:
        await update.message.reply_text(
            "Uso: /targetall <sconto%>\n"
            "Esempio: /targetall 20 → imposta il target al 20% di sconto sul prezzo attuale"
        )
        return

    db_path = context.bot_data["db_path"]

    try:
        discount = float(context.args[0].replace(",", "."))
        if not 1 <= discount <= 99:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Sconto non valido. Inserisci un numero tra 1 e 99.")
        return

    products = get_all_products(db_path)
    updated, skipped = 0, 0

    for p in products:
        if p.current_price:
            target = round(p.current_price * (1 - discount / 100), 2)
            update_product_target(db_path, p.id, target)
            updated += 1
        else:
            skipped += 1

    msg = f"🎯 Target impostato al -{discount:.0f}% per {updated} prodotti."
    if skipped:
        msg += f"\n⚠️ {skipped} prodotti saltati (prezzo non ancora rilevato)."
    await update.message.reply_text(msg)


def build_application(token: str, bot_data: dict, post_init=None) -> Application:
    builder = Application.builder().token(token)
    if post_init:
        builder = builder.post_init(post_init)
    app = builder.build()
    app.bot_data.update(bot_data)

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("list", _cmd_list))
    app.add_handler(CommandHandler("import", _cmd_import))
    app.add_handler(CommandHandler("add", _cmd_add))
    app.add_handler(CommandHandler("remove", _cmd_remove))
    app.add_handler(CommandHandler("target", _cmd_target))
    app.add_handler(CommandHandler("check", _cmd_check))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("clear", _cmd_clear))
    app.add_handler(CommandHandler("targetall", _cmd_targetall))
    app.add_handler(CommandHandler("sync", _cmd_sync))
    app.add_handler(CommandHandler("debug", _cmd_debug))

    return app
