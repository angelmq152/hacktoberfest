from telegram.ext import ExtBot
from shared.contracts import BotResponse
import logging

logger = logging.getLogger(__name__)

async def send(bot: ExtBot, resp: BotResponse) -> None:
    """Mock for output.telegram_out.send"""
    logger.info(f"Sending response to {resp.chat_id}: speech='{resp.speech}', text='{resp.text}'")
    
    # En un entorno real se usaría bot.send_voice y bot.send_message
    if resp.error:
        await bot.send_message(chat_id=resp.chat_id, text=f"⚠️ {resp.error}")
        return

    if resp.text:
        await bot.send_message(chat_id=resp.chat_id, text=resp.text)
        
    if resp.speech:
        from output.tts import text_to_speech
        audio_bytes = await text_to_speech(resp.speech)
        if audio_bytes:
            await bot.send_voice(chat_id=resp.chat_id, voice=audio_bytes)
        else:
            await bot.send_message(chat_id=resp.chat_id, text=f"🎤 [TTS Fallback]: {resp.speech}")
