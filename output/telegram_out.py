from telegram.ext import ExtBot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from shared.contracts import BotResponse
from output.tts import get_voice_note
import html
import logging
import re

MAX_TEXT_LENGTH = 4096

logger = logging.getLogger(__name__)

_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_HEADING = re.compile(r"^\s*#{1,6}\s+(.*)$")


def _inline_to_html(line: str) -> str:
    """Escapa una línea de markdown y convierte `código` y **negrita** a HTML de Telegram."""
    heading = _HEADING.match(line)
    if heading:
        return "<b>" + html.escape(heading.group(1).replace("**", "").strip(), quote=False) + "</b>"
    line = html.escape(line, quote=False)
    line = _CODE.sub(r"<code>\1</code>", line)
    return _BOLD.sub(r"<b>\1</b>", line)


def _table_to_pre(rows: list[str]) -> str:
    """Telegram no pinta tablas: las alineamos en un bloque monoespaciado."""
    cells = [[c.replace("**", "").replace("`", "").strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]  # fila |---|
    if not cells:
        return ""
    widths = [max(len(r[i]) if i < len(r) else 0 for r in cells) for i in range(max(map(len, cells)))]
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip() for r in cells]
    return "<pre>" + html.escape("\n".join(lines), quote=False) + "</pre>"


def md_to_html(text: str) -> str:
    """Convierte el markdown sencillo del núcleo (tablas, ```bloques```, `código`, **negrita**) a HTML de Telegram."""
    out: list[str] = []
    table: list[str] = []
    code: list[str] | None = None
    for line in text.split("\n"):
        if code is not None:
            if line.strip().startswith("```"):
                out.append("<pre>" + html.escape("\n".join(code), quote=False) + "</pre>")
                code = None
            else:
                code.append(line)
            continue
        if line.strip().startswith("|"):
            table.append(line)
            continue
        if table:
            out.append(_table_to_pre(table))
            table = []
        if line.strip().startswith("```"):
            code = []
        else:
            out.append(_inline_to_html(line))
    if table:
        out.append(_table_to_pre(table))
    if code is not None:
        out.append("<pre>" + html.escape("\n".join(code), quote=False) + "</pre>")
    return "\n".join(out)


def _split(text: str, limit: int = MAX_TEXT_LENGTH) -> list[str]:
    """Trocea por saltos de línea para no romper etiquetas HTML; solo corta a pelo líneas gigantes."""
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


async def send(bot: ExtBot, resp: BotResponse) -> None:
    """Envía la respuesta al usuario siguiendo el flujo: Error -> Voz -> Texto -> Archivos -> Confirmación."""

    # 1. Enviar error si existe
    if resp.error:
        await bot.send_message(chat_id=resp.chat_id, text=f"⚠️ {html.escape(resp.error)}", parse_mode="HTML")

    body = md_to_html(resp.text) if resp.text else ""

    # 2. Enviar Nota de Voz (speech)
    if resp.speech:
        voice_path = await get_voice_note(resp.speech)
        if voice_path and voice_path.exists():
            with open(voice_path, "rb") as voice_file:
                await bot.send_voice(chat_id=resp.chat_id, voice=voice_file, read_timeout=60, write_timeout=60)
        else:
            # Fallback en caso de que TTS falle
            body = f"<i>(Audio no disponible)</i>\n\n{body or html.escape(resp.speech)}"

    # 3. Enviar Texto (troceado si supera 4096 caracteres)
    for chunk in _split(body):
        # No enviamos empty strings
        if chunk.strip():
            try:
                await bot.send_message(chat_id=resp.chat_id, text=chunk, parse_mode="HTML")
            except Exception as e:
                # Fallback si HTML parse mode falla (por etiquetas sin cerrar al trocear, etc)
                logger.warning(f"Error parseando HTML, enviando sin parse_mode: {e}")
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
            logger.error(f"Archivo no encontrado: {file.path}")

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
