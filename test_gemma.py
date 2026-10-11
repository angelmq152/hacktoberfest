import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from telegram.ext import ExtBot
from shared.contracts import BotResponse, Confirmation, OutFile
from output.telegram_out import send
from pathlib import Path

async def main():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = int(os.getenv("TEST_CHAT_ID"))
    
    bot = ExtBot(token)
    
    dummy_file = Path("test_doc.txt")
    dummy_file.write_text("Hola, soy un documento de prueba.")
    
    # Creamos un "BotResponse" falso (Mock) con un texto muy técnico (Markdown y tablas)
    mock_response = BotResponse(
        chat_id=chat_id,
        speech="", # Dejamos el speech vacío para forzar a Gemma a generarlo
        text="""**Reporte de Estado (Producción)**:
| Contenedor | Estado | CPU | RAM |
|---|---|---|---|
| `nginx_proxy` | 🟢 UP (45d) | 2.1% | 150MB |
| `postgres_db` | 🟢 UP (45d) | 15.4% | 2.5GB |
| `worker_node_1` | 🔴 EXITED (code 137) | 0% | 0MB |

**Últimos logs (`worker_node_1`)**:
```
FATAL: OutOfMemoryError. Killed by OOM killer.
```""",
        files=[OutFile(path=dummy_file, mime="text/plain", caption="Reporte detallado")],
        confirmation=Confirmation(action_id="12345", prompt="¿Quieres que reinicie el contenedor worker_node_1?")
    )
    
    print("Enviando reporte hiper-técnico a Telegram (esperando a Gemma y TTS)...")
    await send(bot, mock_response)
    print("¡Enviado con éxito!")
    
    if dummy_file.exists():
        dummy_file.unlink()

if __name__ == "__main__":
    asyncio.run(main())
