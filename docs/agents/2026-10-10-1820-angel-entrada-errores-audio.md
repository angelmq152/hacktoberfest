---
de: angel (claude-code)
para: alex
tipo: aviso
estado: abierto
---

# Errores de audio ya no llegan al núcleo como texto "mock: ..."

En la prueba real, una descarga de voz dio `Timed out` y `telegram_in` mandó al núcleo el texto
`"mock: error bajando audio"`; el modelo contestó que no encontraba un contenedor llamado "audio".

- `input/telegram_in.py`: la descarga se reintenta una vez (`read_timeout=60`). Si falla, o si la transcripción
  viene vacía, se avisa al usuario (`AUDIO_DOWNLOAD_ERROR` / `AUDIO_STT_ERROR`) y `to_request` devuelve `None`.
- `input/stt.py`: en error devuelve `""` en vez de `"mock: ..."`. El mock sin API key se queda como estaba.
- Tests en `tests/test_telegram_in.py`.
