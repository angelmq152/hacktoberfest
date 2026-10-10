from telegram.ext import ExtBot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from shared.contracts import BotResponse
from output.tts import get_voice_note
import html

MAX_TEXT_LENGTH = 4096

async def send(bot: ExtBot, resp: BotResponse) -> None:
    """Envía la respuesta al usuario siguiendo el flujo: Error -> Voz -> Texto -> Archivos -> Confirmación."""
    
    # 1. Enviar error si existe
    if resp.error:
        await bot.send_message(chat_id=resp.chat_id, text=f"⚠️ {html.escape(resp.error)}", parse_mode="HTML")
        
    # 2. Enviar Nota de Voz (speech)
    if resp.speech:
        voice_path = await get_voice_note(resp.speech)
        if voice_path and voice_path.exists():
            with open(voice_path, "rb") as voice_file:
                await bot.send_voice(chat_id=resp.chat_id, voice=voice_file, read_timeout=60, write_timeout=60)
        else:
            # Fallback en caso de que TTS falle
            resp.text = f"<i>(Audio no disponible)</i>\n\n{resp.text}" if resp.text else f"<i>(Audio no disponible)</i>\n\n{resp.speech}"

    # 3. Enviar Texto (troceado si supera 4096 caracteres)
    if resp.text:
        # Trocear por MAX_TEXT_LENGTH, idealmente se haría en saltos de línea para no romper el HTML
        for i in range(0, len(resp.text), MAX_TEXT_LENGTH):
            chunk = resp.text[i:i+MAX_TEXT_LENGTH]
            # No enviamos empty strings
            if chunk.strip():
                try:
                    await bot.send_message(chat_id=resp.chat_id, text=chunk, parse_mode="HTML")
                except Exception as e:
                    # Fallback si HTML parse mode falla (por etiquetas sin cerrar al trocear, etc)
                    print(f"Error parseando HTML, enviando sin parse_mode: {e}")
                    await bot.send_message(chat_id=resp.chat_id, text=chunk)

    # 4. Enviar Archivos
    for file in resp.files:
        if file.path.exists():
            with open(file.path, "rb") as f:
                if file.mime.startswith("image/"):
                    await bot.send_photo(chat_id=resp.chat_id, photo=f, caption=file.caption, read_timeout=60, write_timeout=60)
                else:
                    await bot.send_document(chat_id=resp.chat_id, document=f, caption=file.caption, read_timeout=60, write_timeout=60)
        else:
            print(f"Archivo no encontrado: {file.path}")

    # 5. Enviar Confirmación (Botones Inline)
    if resp.confirmation:
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm:{resp.confirmation.action_id}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel:{resp.confirmation.action_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await bot.send_message(
            chat_id=resp.chat_id, 
            text=html.escape(resp.confirmation.prompt), 
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
