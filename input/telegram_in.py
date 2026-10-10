import asyncio
import io
import difflib
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from shared.contracts import IncomingRequest
from shared.config import get_settings
from input.stt import transcribe_audio
from core.tools.base import ToolError
from core.tools.docker_tools import list_names

logger = logging.getLogger(__name__)

AUDIO_DOWNLOAD_ERROR = "⚠️ No he podido descargar tu audio de Telegram. ¿Me lo reenvías?"
AUDIO_STT_ERROR = "⚠️ No he podido entender el audio. ¿Me lo repites o me lo escribes?"

async def to_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> IncomingRequest | None:
    """
    Transforms a Telegram Update into an IncomingRequest.
    Handles whitelist, voice downloading, transcription and fuzzy matching.
    """
    user = update.effective_user
    chat = update.effective_chat
    
    if not user or not chat:
        return None
        
    if user.id not in get_settings().allowed_ids:
        logger.warning(f"Unauthorized access attempt from user_id: {user.id} ({user.username})")
        return None

    text = ""
    source = "text"
    confirm_action_id = None
    
    # Handle callbacks (buttons)
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data and data.startswith("confirm:"):
            confirm_action_id = data.split(":", 1)[1]
            source = "callback"
        elif data and data.startswith("cancel:"):
            # If we want to handle cancellation here
            confirm_action_id = "CANCEL:" + data.split(":", 1)[1]
            source = "callback"
        
        return IncomingRequest(
            chat_id=chat.id,
            user_id=user.id,
            text="",
            source=source,
            confirm_action_id=confirm_action_id
        )

    # Handle messages
    message = update.message
    if not message:
        return None

    if message.voice or message.audio:
        source = "voice"
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.RECORD_VOICE)
        
        media_file = message.voice or message.audio
        
        out_bytes = None
        for attempt in range(2):
            try:
                file = await media_file.get_file(read_timeout=30, connect_timeout=30)

                # Download to memory
                out_bytes = io.BytesIO()
                await file.download_to_memory(out=out_bytes, read_timeout=60)
                break
            except Exception as e:
                logger.error(f"Error downloading voice from Telegram (attempt {attempt + 1}): {e}")
                out_bytes = None
        if out_bytes is None:
            await context.bot.send_message(chat_id=chat.id, text=AUDIO_DOWNLOAD_ERROR)
            return None

        text = await transcribe_audio(out_bytes)
        if not text.strip():
            await context.bot.send_message(chat_id=chat.id, text=AUDIO_STT_ERROR)
            return None
        
    elif message.text:
        source = "text"
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        text = message.text
    else:
        return None

    # Fuzzy match container names
    try:
        text = _fuzzy_match_containers(text, await asyncio.to_thread(list_names))
    except ToolError as e:
        logger.warning(f"Could not list containers for fuzzy matching: {e}")

    return IncomingRequest(
        chat_id=chat.id,
        user_id=user.id,
        text=text,
        source=source,
    )

def _fuzzy_match_containers(text: str, actual_names: list[str]) -> str:
    """
    Finds potential container names in the text and replaces them with the actual names.
    """
    if not actual_names:
        return text
        
    # Very basic fuzzy matching: split text and check if any word is close to a container name.
    # We might want to match pairs of words too (e.g. "post gres" -> "postgres").
    words = text.split()
    matched_text = text
    
    # check single words
    for word in words:
        if len(word) > 2:
            matches = difflib.get_close_matches(word.lower(), actual_names, n=1, cutoff=0.7)
            if matches:
                matched_text = matched_text.replace(word, matches[0])
                
    # check pairs (e.g. "post gres")
    for i in range(len(words) - 1):
        pair = f"{words[i]} {words[i+1]}"
        matches = difflib.get_close_matches(pair.lower().replace(" ", ""), actual_names, n=1, cutoff=0.8)
        if matches:
            matched_text = matched_text.replace(pair, matches[0])
            
    return matched_text
