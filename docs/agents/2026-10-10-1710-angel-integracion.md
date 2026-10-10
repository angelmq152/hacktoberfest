---
de: angel (claude-code)
para: todos
tipo: aviso
estado: abierto
---

# Rama `integracion`: las tres partes juntas

He juntado `main` (Parte 1 + Parte 3 + SP_01_fase1), `parte2-nucleo` y `docs/plan-implementacion` en la rama `integracion`.
`ruff` y los 80 tests pasan, y un smoke test de `main.master_handler` con Telegram, Gemma y Docker falsos recorre
listar → pedir confirmación → cancelar → confirmar → reiniciar, y rechaza a usuarios fuera de la whitelist.

## Cambios en vuestro código (para que lo reviséis)

- **Alex (`input/`)**
  - `stt.py` y `telegram_in.py` usan `get_settings()` en vez de `settings`; la whitelist es `get_settings().allowed_ids`.
  - `telegram_in.py`: `list_names()` se llama con `asyncio.to_thread` (es síncrona y bloqueaba el bucle) y, si Docker
    falla (`ToolError`), se sigue sin fuzzy match en vez de perder el mensaje. `_fuzzy_match_containers(text, names)`
    recibe ahora los nombres por parámetro.
- **Pedro (`output/`)**
  - `tts.py` lee `ELEVENLABS_*` con `get_settings()`. Con `os.getenv` no veía el `.env` (pydantic-settings no
    lo exporta al entorno), así que al probar en local nunca había audio.
- **Zona común**
  - `shared/config.py`: queda la versión de `parte2-nucleo` (`get_settings()` con caché, `allowed_ids`, `out_dir: Path`).
    `shared/contracts.py` no cambia.
  - `main.py`: el `master_handler` de los compañeros, solo cambia a `get_settings()`.
  - `requirements.txt`: unión de las dos listas, con versiones fijadas (`python-telegram-bot[job-queue]==22.8`,
    `elevenlabs==2.71.0`).
- **Núcleo**: `core.agent` entiende el `CANCEL:<id>` que manda el botón Cancelar (antes respondía "caducada") y ya no
  repite la pregunta de confirmación en `text`, porque la Parte 3 ya la manda con los botones.

## Pendiente

- No hay Dockerfile del bot. Para probar en local hace falta `ffmpeg` en el PATH y un `.env` (ver `.env.example`).
- `PLAN.md` en la raíz es una copia idéntica de `docs/PLAN.md`; propongo borrar la de la raíz.
