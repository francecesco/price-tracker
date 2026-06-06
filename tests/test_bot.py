import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update(user_id: int, text: str = "", args: list = None):
    """Create a minimal mock Update object."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _make_context(bot_data: dict, args: list = None):
    """Create a minimal mock Context object."""
    context = MagicMock()
    context.bot_data = bot_data
    context.args = args or []
    return context


OWNER_ID = 12345


@pytest.mark.asyncio
async def test_start_responds_to_owner():
    from bot import _cmd_start
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID})
    await _cmd_start.__wrapped__(update, context) if hasattr(_cmd_start, '__wrapped__') else await _cmd_start(update, context)
    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "Price Tracker" in msg
    assert "/import" in msg


@pytest.mark.asyncio
async def test_owner_only_blocks_non_owner():
    from bot import _cmd_start
    update = _make_update(99999)  # not the owner
    context = _make_context({"chat_id": OWNER_ID})
    await _cmd_start(update, context)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_list_empty_db(tmp_db):
    from bot import _cmd_list
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db})
    await _cmd_list(update, context)
    update.message.reply_text.assert_called_once_with("Nessun prodotto in tracciamento.")


@pytest.mark.asyncio
async def test_list_shows_products(tmp_db):
    from database import add_product, update_product_target
    from bot import _cmd_list
    p = add_product(tmp_db, "B09XS7JWHH", "Sony WH-1000XM5", "https://amazon.it/dp/B09XS7JWHH", 219.99, "manual")
    update_product_target(tmp_db, p.id, 220.0)

    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db})
    await _cmd_list(update, context)
    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "Sony" in msg
    assert "219" in msg


@pytest.mark.asyncio
async def test_add_invalid_url(tmp_db):
    from bot import _cmd_add
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=["https://www.google.com/"])
    await _cmd_add(update, context)
    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "non valido" in msg


@pytest.mark.asyncio
async def test_add_no_args(tmp_db):
    from bot import _cmd_add
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=[])
    await _cmd_add(update, context)
    msg = update.message.reply_text.call_args[0][0]
    assert "/add" in msg


@pytest.mark.asyncio
async def test_remove_nonexistent_product(tmp_db):
    from bot import _cmd_remove
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=["9999"])
    await _cmd_remove(update, context)
    msg = update.message.reply_text.call_args[0][0]
    assert "non trovato" in msg


@pytest.mark.asyncio
async def test_remove_invalid_id(tmp_db):
    from bot import _cmd_remove
    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=["abc"])
    await _cmd_remove(update, context)
    msg = update.message.reply_text.call_args[0][0]
    assert "non valido" in msg


@pytest.mark.asyncio
async def test_target_sets_price(tmp_db):
    from database import add_product, get_product_by_id
    from bot import _cmd_target
    p = add_product(tmp_db, "B09XS7JWHH", "Sony", "https://amazon.it/dp/B09XS7JWHH", 219.99, "manual")

    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=[str(p.id), "200"])
    await _cmd_target(update, context)

    updated = get_product_by_id(tmp_db, p.id)
    assert updated.target_price == 200.0
    msg = update.message.reply_text.call_args[0][0]
    assert "200" in msg


@pytest.mark.asyncio
async def test_target_comma_decimal(tmp_db):
    from database import add_product, get_product_by_id
    from bot import _cmd_target
    p = add_product(tmp_db, "B09XS7JWHH", "Sony", "https://amazon.it/dp/B09XS7JWHH", 219.99, "manual")

    update = _make_update(OWNER_ID)
    context = _make_context({"chat_id": OWNER_ID, "db_path": tmp_db}, args=[str(p.id), "199,99"])
    await _cmd_target(update, context)

    updated = get_product_by_id(tmp_db, p.id)
    assert updated.target_price == pytest.approx(199.99)
