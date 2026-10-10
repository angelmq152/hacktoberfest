import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from shared.config import get_settings
from input.telegram_in import to_request
from core.agent import handle
from output.telegram_out import send

# Setup basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def master_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main entry point for handling incoming telegram updates.
    """
    # 1. Entrada (Parte 1)
    req = await to_request(update, context)
    if not req:
        # Ignore unsupported messages or unauthorized users
        return
        
    logger.info(f"Received request: {req}")
    
    # 2. Núcleo (Parte 2)
    resp = await handle(req)
    
    # 3. Salida (Parte 3)
    await send(context.bot, resp)

def main() -> None:
    """Run the bot."""
    settings = get_settings()
    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN is not set in the environment.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(settings.telegram_token).build()

    # We register the master handler for voice, audio, and text
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.TEXT, master_handler))
    
    # And for callback queries (buttons)
    application.add_handler(CallbackQueryHandler(master_handler))

    logger.info("Bot is starting...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
