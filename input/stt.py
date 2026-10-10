import io
import httpx
from shared.config import get_settings

async def transcribe_audio(audio_data: io.BytesIO) -> str:
    """
    Transcribes OGG Opus audio using ElevenLabs Speech-to-Text (Scribe).
    """
    if not get_settings().elevenlabs_api_key:
        return "mock: lista los contenedores"
        
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        "xi-api-key": get_settings().elevenlabs_api_key
    }
    
    audio_data.seek(0)
    files = {
        "file": ("audio.ogg", audio_data, "audio/ogg")
    }
    data = {
        "model_id": "scribe_v1",
        "language_code": "spa"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data, files=files, timeout=60.0)
            if response.status_code != 200:
                import logging
                logging.getLogger(__name__).error(f"STT Error: {response.status_code} - {response.text}")
                return "mock: error transcribiendo el audio"
            result = response.json()
            return result.get("text", "")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Exception during STT: {e}")
        return "mock: error de conexión en stt"
