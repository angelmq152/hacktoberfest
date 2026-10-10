# Provisional text-only wiring so Part 2 can be tried from Telegram.
# Will be replaced by input/telegram_in.py (Part 1) and output/telegram_out.py (Part 3).
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from core.agent import handle
from shared.config import get_settings
from shared.contracts import BotResponse, IncomingRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("main")

MAX_MSG = 4096


async def send(bot, resp: BotResponse) -> None:
    body = resp.text or resp.speech
    if resp.error:
        body = f"{body}\n\n⚠️ {resp.error}"
    markup = None
    if resp.confirmation:
        aid = resp.confirmation.action_id
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm:{aid}"),
                                        InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel:{aid}")]])
    chunks = [body[i:i + MAX_MSG] for i in range(0, len(body), MAX_MSG)] or ["…"]
    for i, chunk in enumerate(chunks):
        await bot.send_message(resp.chat_id, chunk, reply_markup=markup if i == len(chunks) - 1 else None)
    for f in resp.files:
        with open(f.path, "rb") as fh:
            if f.mime == "image/png":
                await bot.send_photo(resp.chat_id, fh, caption=f.caption or None)
            else:
                await bot.send_document(resp.chat_id, fh, filename=f.path.name, caption=f.caption or None)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    req = IncomingRequest(chat_id=msg.chat_id, user_id=update.effective_user.id, text=msg.text, source="text")
    await send(context.bot, await handle(req))


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(None)
    action, _, aid = (query.data or "").partition(":")
    chat_id = query.message.chat_id
    if action != "confirm":
        await context.bot.send_message(chat_id, "Cancelado.")
        return
    req = IncomingRequest(chat_id=chat_id, user_id=query.from_user.id, text="", source="callback",
                          confirm_action_id=aid)
    await send(context.bot, await handle(req))


def main() -> None:
    s = get_settings()
    users = filters.User(user_id=s.allowed_ids)
    app = Application.builder().token(s.telegram_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & users, on_text))
    app.add_handler(CallbackQueryHandler(on_callback))
    log.info("bot started, allowed users: %s", sorted(s.allowed_ids))
    app.run_polling()


if __name__ == "__main__":
    main()
