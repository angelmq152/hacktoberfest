import httpx
import logging
from shared.config import settings

logger = logging.getLogger(__name__)

async def text_to_speech(text: str) -> bytes | None:
    """
    Converts text to speech using ElevenLabs TTS and returns OGG Opus audio bytes.
    """
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        logger.warning("ElevenLabs credentials not found. Skipping TTS.")
        return None
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}?output_format=opus_48000_128"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        return None
