import hashlib
import asyncio
import logging
from pathlib import Path
from elevenlabs.client import AsyncElevenLabs
from shared.config import get_settings

# Configuración básica (lee el .env igual que el resto del bot)
_settings = get_settings()
API_KEY = _settings.elevenlabs_api_key
client = AsyncElevenLabs(api_key=API_KEY) if API_KEY else None

# Sarah (premade): las voces de la biblioteca, como Rachel, dan 402 en cuentas gratuitas
VOICE_ID = _settings.elevenlabs_voice_id or "EXAVITQu4vr4xnSDxMaL"
MODEL_ID = _settings.elevenlabs_tts_model
CACHE_DIR = Path("/tmp/tts_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

async def convert_mp3_to_ogg(mp3_path: Path, ogg_path: Path) -> bool:
    """Convierte MP3 a OGG/Opus usando ffmpeg asíncrono."""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(mp3_path), "-c:a", "libopus", "-b:a", "48k", str(ogg_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
        return process.returncode == 0
    except FileNotFoundError:
        logger.error("ffmpeg no está instalado o no se encuentra en el PATH.")
        return False

async def get_voice_note(text: str) -> Path | None:
    """Obtiene la nota de voz en OGG, usando caché si es posible."""
    if not text or not client:
        return None
        
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ogg_path = CACHE_DIR / f"{text_hash}.ogg"
    mp3_path = CACHE_DIR / f"{text_hash}.mp3"
    
    if ogg_path.exists():
        return ogg_path
        
    try:
        # Petición a ElevenLabs
        audio = client.text_to_speech.convert(
            voice_id=VOICE_ID,
            output_format="mp3_44100_128",
            text=text,
            model_id=MODEL_ID,
        )
        # Guardar mp3
        with open(mp3_path, "wb") as f:
            async for chunk in audio:
                f.write(chunk)
                
        # Convertir a ogg
        success = await convert_mp3_to_ogg(mp3_path, ogg_path)
        if success:
            return ogg_path
        return None
    except Exception as e:
        logger.error(f"Error en TTS (ElevenLabs): {e}")
        return None
