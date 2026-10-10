# Parte 3 — Salida (Pedro)

¡Hola equipo! Aquí tenéis la documentación de la Parte 3 (Salida) ya implementada. 

Este módulo se encarga de recibir los datos generados por el Núcleo (Parte 2, Angel) a través del contrato `BotResponse` y enviarlos correctamente al usuario mediante Telegram, generando la voz con ElevenLabs si es necesario.

## ¿Qué hace exactamente?

1. **Convierte a Voz (TTS):** Si `BotResponse.speech` tiene contenido, llama a la API asíncrona de ElevenLabs. Además:
   - Cachea los audios generados usando el hash SHA-256 del texto para no gastar cuota de la API repitiendo mensajes iguales.
   - Convierte el audio MP3 a OGG/Opus mediante un subproceso de `ffmpeg` porque es el único formato que Telegram acepta como "Nota de Voz".
   - *Fallback robusto:* Si falla la clave de ElevenLabs o el servicio se cae, la ejecución no se rompe; simplemente enviará un texto diciendo `(Audio no disponible)` seguido de la información.

2. **Envía el Mensaje de Texto:** Si `BotResponse.text` supera el límite de 4096 caracteres de Telegram, este módulo lo trocea automáticamente y lo envía en varios mensajes usando el parseo HTML de Telegram.

3. **Adjunta Archivos:** Recorre la lista de `BotResponse.files` y utiliza internamente `send_photo` (si el MIME type es de imagen) o `send_document` (para PDFs, Excel, etc.), asegurándose de enviar el caption si Angel lo ha rellenado.

4. **Maneja Confirmaciones:** Si viene un objeto `BotResponse.confirmation` (por ejemplo, para confirmar el reinicio de un contenedor), construye automáticamente el teclado Inline de Telegram con los botones "✅ Confirmar" y "❌ Cancelar" listos para que los pulse el usuario (con el `callback_data` en el formato `confirm:<action_id>`).

## Cómo integrarlo en `main.py`

La única función que necesitáis importar desde `main.py` es la función `send`. Funciona así:

```python
from shared.contracts import BotResponse
from output.telegram_out import send

# Suponiendo que 'bot' es la instancia ExtBot de python-telegram-bot
# y que el núcleo (Parte 2) ha devuelto 'resp' (de tipo BotResponse):
await send(bot, resp)
```

## Dependencias a tener en cuenta (Entorno Local)

Para que esta parte no os falle al probar la integración de principio a fin en vuestros ordenadores, aseguraos de:

1. Tener **ffmpeg** instalado a nivel de sistema operativo y en el PATH:
   - Windows: Descargarlo o usar `winget install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
2. Tener las dependencias de Python de esta parte instaladas (`pip install elevenlabs python-telegram-bot`).
3. Disponer de las variables de entorno en el `.env`:
   - `ELEVENLABS_API_KEY=tu_clave_aqui` (Si no la ponéis, funcionará con el fallback, solo no enviará audio).
   - `ELEVENLABS_VOICE_ID=...` (Opcional, tiene valor por defecto).
   - `ELEVENLABS_TTS_MODEL=eleven_flash_v2_5`

¡Cualquier duda que tengáis para conectarlo me decís!
