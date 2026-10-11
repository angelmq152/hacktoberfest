import os
from openai import AsyncOpenAI

GEMMA_BASE_URL = "https://bubbly-vermilion.netbird.apps.buildinmadrid.dev/v1"
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "dummy-key")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-3-27b-it")

client = AsyncOpenAI(
    base_url=GEMMA_BASE_URL,
    api_key=GEMMA_API_KEY,
)

async def optimize_for_speech(text: str, original_speech: str) -> str:
    """Usa Gemma para adaptar un reporte técnico a formato de síntesis de voz (TTS)."""
    if not text:
        return original_speech

    prompt = f"""
Eres un ingeniero DevOps experto en Docker (DockerOps).
Tu tarea es tomar el siguiente reporte técnico y redactar UNA respuesta corta y precisa para ser leída por un sistema de voz (TTS) al usuario.
- Mantén todo el rigor técnico (nombres de contenedores, estados, consumo de CPU/RAM).
- Elimina cualquier formato Markdown, tablas o símbolos que un sintetizador de voz no sabría pronunciar bien.
- Sé directo, profesional y ve al grano.

Reporte original:
{text}
"""
    try:
        response = await client.chat.completions.create(
            model=GEMMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al conectar con Gemma: {e}")
        return original_speech # Fallback seguro
