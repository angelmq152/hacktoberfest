# Bot de Telegram por voz — Plan de implementación

Hacktoberfest 2026 · Equipo: **Alex** (Parte 1, entrada) · **Angel** (Parte 2, núcleo) · **Pedro** (Parte 3, salida)

## 1. Objetivo

Bot de Telegram al que le hablas por **nota de voz** (o texto) y que:

- Gestiona los contenedores Docker del servidor: listar, ver estado, logs y consumo, y reiniciar, parar o arrancar.
- Genera **Excel, PDF y gráficas** con datos de los contenedores o con lo que le pidas.
- **Responde por voz** (ElevenLabs TTS) y adjunta los ficheros generados.
- Usa **Gemma** (API de la hackathon) como cerebro, con herramientas (tool calling).

## 2. Arquitectura y reparto

```
 [Usuario Telegram]
        │ nota de voz / texto
        ▼
 ┌────────────────────┐  IncomingRequest  ┌──────────────────────┐  BotResponse  ┌─────────────────────┐
 │ PARTE 1 · ENTRADA  │ ────────────────▶ │ PARTE 2 · NÚCLEO     │ ────────────▶ │ PARTE 3 · SALIDA    │
 │ Alex               │                   │ Angel                │               │ Pedro               │
 │ voz → texto (STT)  │                   │ Gemma + tools        │               │ texto → voz (TTS)   │
 │ ElevenLabs Scribe  │                   │ Docker / XLSX / PDF  │               │ sendVoice/Document  │
 └────────────────────┘                   └──────────┬───────────┘               └─────────────────────┘
                                                     │
                                      docker-socket-proxy (permisos mínimos)
```

Un único proceso Python (asyncio) con tres módulos. Los módulos se comunican **solo** mediante dos dataclasses de `shared/contracts.py`. Así cada uno trabaja en paralelo desde el minuto 1 contra versiones falsas (mocks) de las otras partes.

## 3. Contratos (fase 0, los tres juntos)

```python
# shared/contracts.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class IncomingRequest:
    chat_id: int
    user_id: int
    text: str                                # transcription or typed text
    source: Literal["voice", "text", "callback"]
    lang: str = "es"
    confirm_action_id: str | None = None     # set when the user presses "Confirm"


@dataclass
class OutFile:
    path: Path
    mime: str                                # application/pdf, xlsx, image/png...
    caption: str = ""


@dataclass
class Confirmation:
    action_id: str                           # pending action stored in core
    prompt: str                              # "¿Reinicio 'redis'?"


@dataclass
class BotResponse:
    chat_id: int
    speech: str                              # SHORT text for TTS, no markdown
    text: str = ""                           # markdown detail (tables, logs)
    files: list[OutFile] = field(default_factory=list)
    confirmation: Confirmation | None = None
    error: str | None = None
```

Interfaces que expone cada parte:

| Parte | Función |
|---|---|
| 1 · Entrada | `async def to_request(update) -> IncomingRequest` |
| 2 · Núcleo | `async def handle(req: IncomingRequest) -> BotResponse` |
| 3 · Salida | `async def send(bot, resp: BotResponse) -> None` |

`main.py` solo encadena: `await send(bot, await handle(await to_request(update)))`.

## 4. Estructura del repo

```
hacktoberfest/
├── main.py                    # bot start (polling) + wiring
├── shared/
│   ├── contracts.py
│   └── config.py              # .env loading (pydantic-settings)
├── input/                     # PARTE 1 · Alex
│   ├── telegram_in.py         # voice/text/callback handlers, whitelist
│   └── stt.py                 # ElevenLabs Scribe
├── core/                      # PARTE 2 · Angel
│   ├── agent.py               # LLM loop + tool calling
│   ├── llm.py                 # Gemma client
│   ├── pending.py             # actions awaiting confirmation
│   └── tools/
│       ├── docker_tools.py
│       └── reports.py         # xlsx, pdf, charts
├── output/                    # PARTE 3 · Pedro
│   ├── tts.py                 # ElevenLabs TTS → ogg/opus
│   └── telegram_out.py        # sendVoice, sendMessage, sendDocument, buttons
├── tests/
├── docs/PLAN.md
├── compose.yaml
├── Dockerfile
└── .env.example
```

**Stack:** Python 3.12, `python-telegram-bot` v21 (async), `elevenlabs`, `docker`, `openpyxl`, `reportlab`, `matplotlib`, `httpx`, y `ffmpeg` en la imagen.

## 5. Parte 1 — Entrada (Alex)

1. Crear el bot con **@BotFather** y guardar el token en `.env` (`TELEGRAM_TOKEN`).
2. Handlers para `filters.VOICE`, `filters.AUDIO` y `filters.TEXT`, más un `CallbackQueryHandler` para los botones de confirmación (`confirm:<action_id>` / `cancel:<action_id>`).
3. **Whitelist** de `user_id` (`ALLOWED_USER_IDS`). El resto de usuarios se ignora y se registra en el log. Es crítico, porque el bot controla Docker.
4. Descargar la nota de voz (`.oga`, Opus) con `await voice.get_file()` y `download_to_memory()`.
5. Transcribir con **ElevenLabs Speech-to-Text (Scribe)**. El ogg se envía tal cual, con `language_code="spa"`.
6. Normalizar los nombres de contenedor mal transcritos con un fuzzy match contra la lista real que expone el núcleo (`core.tools.docker_tools.list_names()`). Por ejemplo, «post gres» → `postgres`.
7. Avisar en cuanto llega el mensaje: `send_chat_action(TYPING / RECORD_VOICE)` mientras se procesa.
8. Construir el `IncomingRequest` y devolverlo.

- **Mock inicial:** `to_request` devuelve siempre `"lista los contenedores"`.
- **Hecho cuando:** una nota de voz real produce un `IncomingRequest` con la transcripción correcta.

## 6. Parte 2 — Núcleo (Angel)

### 6.1 LLM (Gemma)

- Cliente en `core/llm.py` contra el endpoint de la hackathon:
  - Google AI Studio / Gemini API: modelo `gemma-3-27b-it` (o el que esté habilitado).
  - Endpoint compatible con OpenAI (vLLM, Ollama…): SDK `openai` con `base_url`.
- **Tool calling robusto:** según el endpoint, Gemma puede no tener function calling nativo, así que el prompt de sistema le obliga a responder **solo JSON**:
  - `{"tool": "<nombre>", "args": {...}}`
  - `{"final": {"speech": "...", "text": "..."}}`
- Parser tolerante: extrae el primer bloque JSON y reintenta una vez. Si vuelve a fallar, devuelve un `BotResponse.error`.
- Máximo **5 llamadas a herramientas** por petición. Memoria corta por `chat_id` (últimos 6 turnos).

### 6.2 Herramientas

**Docker** (SDK `docker`, `DOCKER_HOST=tcp://socket-proxy:2375`):

| Tool | Args | ¿Confirmación? |
|---|---|---|
| `list_containers` | `all: bool` | no |
| `container_status` | `name` | no |
| `container_logs` | `name, tail=100, since?` | no |
| `container_stats` | `name?` (todos si vacío) | no |
| `restart_container` | `name` | **sí** |
| `stop_container` / `start_container` | `name` | **sí** |

**Informes** (los ficheros se escriben en `/data/out/<chat_id>/` y se devuelven como `OutFile`):

| Tool | Qué hace |
|---|---|
| `make_excel` | `title, sheets: [{name, columns, rows}]` → `.xlsx` con cabecera en negrita, autofiltro y ancho de columna ajustado |
| `make_pdf` | `title, sections: [{heading, paragraphs, table?}]` → PDF (reportlab) |
| `make_chart` | `kind: bar/line/pie, labels, values, title` → PNG (matplotlib) |
| `docker_report` | Atajo: foto de todos los contenedores (estado, CPU, RAM, uptime, reinicios) → Excel + PDF con gráfica |

### 6.3 Seguridad (no negociable)

- **Nunca montar `/var/run/docker.sock` en el bot.** Se usa `tecnativa/docker-socket-proxy` con:
  - Permitido: `CONTAINERS=1`, `POST=1`, `ALLOW_RESTARTS=1`, `ALLOW_START=1`, `ALLOW_STOP=1`.
  - Bloqueado (a 0): `EXEC`, `IMAGES`, `VOLUMES`, `NETWORKS` y `BUILD`.
- **Allowlist de contenedores:** el bot solo gestiona los que llevan la label `hackbot.manage=true`.
- **Acciones peligrosas:** el núcleo no las ejecuta directamente.
  - Las guarda en `pending.py` como `{action_id → (tool, args, user_id, expira en 60 s)}` y devuelve un `BotResponse.confirmation`.
  - Solo las ejecuta cuando llega un `confirm_action_id` del mismo usuario.
- **Validación:** el LLM solo puede invocar las tools registradas, y se validan sus argumentos (nombre dentro de la allowlist, `tail` ≤ 500).
- **Logs:** se truncan (máx. ~4 KB) y se tratan como datos, no como instrucciones, para evitar prompt injection.

### 6.4 Prompt de sistema (esbozo)

> Eres DockerOps, asistente de operaciones. Respondes en español. `speech` es una frase natural de 2-3 oraciones como máximo, para leer en voz alta, sin markdown ni IDs largos. Las tablas, logs y detalles van en `text`. Si piden un informe, genera el fichero con la tool correspondiente. Nunca inventes contenedores: consulta primero.

- **Mock inicial:** `handle` devuelve un `BotResponse` fijo con `speech`, `text` y un PDF de ejemplo.
- **Hecho cuando:** funcionan de principio a fin «¿qué contenedores están caídos?», «dame un Excel con el consumo de memoria» y «reinicia redis» (con confirmación).

## 7. Parte 3 — Salida (Pedro)

1. **TTS con ElevenLabs:** `text_to_speech.convert(voice_id, model_id=..., output_format=...)`.
   - Modelo `eleven_flash_v2_5` (baja latencia) o `eleven_multilingual_v2` (más calidad).
   - Fijar una voz en español en `ELEVENLABS_VOICE_ID`.
2. **Formato:** Telegram solo muestra como nota de voz el **OGG/Opus**. Hay que convertir con `ffmpeg -i in.mp3 -c:a libopus -b:a 48k out.ogg` (o pedir Opus directamente si el plan lo permite) y enviar con `send_voice`.
3. **Orden de envío:** nota de voz (`speech`) → mensaje de texto (`text`, en HTML o MarkdownV2 escapado) → ficheros (`send_document`, o `send_photo` para los PNG).
4. **Confirmaciones:** `InlineKeyboardMarkup` con «✅ Confirmar» / «❌ Cancelar», `callback_data="confirm:<action_id>"` (máx. 64 bytes).
5. **Errores:**
   - Si llega `resp.error`: mensaje de texto y un audio corto.
   - Si ElevenLabs falla o se acaba la cuota: **se envía solo texto** y el bot no se rompe.
6. **Límites de Telegram:** texto de 4096 caracteres por mensaje (hay que trocearlo) y documentos de 50 MB.
7. **Extra:** caché de audios por hash de `speech`.

- **Mock inicial:** coger un `BotResponse` fijo y enviarlo a un chat de prueba.
- **Hecho cuando:** un `BotResponse` con speech, texto, 2 ficheros y confirmación llega bien a Telegram.

## 8. Hermes / OpenClaw

Para la hackathon recomendamos un **pipeline propio** como producto principal, por tres motivos:

- permite repartirlo en 3 partes;
- deja controlar la seguridad de Docker;
- no obliga a configurar un framework entero con prisas.

Para sumar puntos sin depender de ellos:

- Exponer las tools de la Parte 2 también como **servidor MCP** (`core/mcp_server.py`, con FastMCP). Así **OpenClaw** o **Hermes Agent** las pueden usar con Gemma como LLM.
- En la demo, mostrar que el mismo núcleo funciona desde nuestro bot y desde OpenClaw/Hermes.
- También sirve de plan B si nuestro bucle de tool calling con Gemma falla.
- Solo si sobra tiempo (fase 4): no bloquea nada.

## 9. Configuración (`.env.example`)

```
TELEGRAM_TOKEN=
ALLOWED_USER_IDS=111111,222222,333333
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5
GEMMA_API_KEY=
GEMMA_BASE_URL=
GEMMA_MODEL=gemma-3-27b-it
DOCKER_HOST=tcp://socket-proxy:2375
MANAGED_LABEL=hackbot.manage=true
OUT_DIR=/data/out
```

> ⚠️ Las claves **no se pegan en chats ni se commitean**. Van en `.env`, que ya está en `.gitignore`. Pasáoslas por un canal privado.

## 10. Despliegue

`compose.yaml` con dos servicios:

- `bot`: imagen propia (Python + ffmpeg), usuario no root, `read_only` y un volumen en `/data/out`.
- `socket-proxy`: en una red interna, sin puertos publicados.

El bot usa **long polling**, así que no expone puertos ni necesita dominio. Para la demo se añaden 3-4 contenedores de prueba con la label `hackbot.manage=true` (nginx, redis, postgres y un `worker` que falle a propósito).

## 11. Calendario

| Fase | Tiempo | Qué | Quién |
|---|---|---|---|
| 0 | 0:00–0:45 | Repo, contratos, `.env`, bot en BotFather y `main.py` funcionando con los 3 mocks | Los 3 |
| 1 | 0:45–4:00 | Cada parte real contra los mocks de las otras dos | En paralelo |
| 2 | 4:00–5:30 | Integración: voz real → Gemma → voz real. Ajustar los contratos | Los 3 |
| 3 | 5:30–7:00 | Informes, confirmaciones, errores y degradación | Angel + Pedro (Alex: fuzzy match y latencia) |
| 4 | 7:00–8:00 | Extras: MCP para OpenClaw/Hermes y caché TTS | Quien quede libre |
| 5 | Última hora | Guion de demo y vídeo de respaldo | Los 3 |

**Reglas de git:**

- Una rama por parte: `parte1-entrada`, `parte2-nucleo` y `parte3-salida`.
- PR pequeños contra `main`.
- Desde la fase 2, `main` siempre tiene que funcionar.

## 12. Tests y CI

Se cubre con pytest, sin red y con mocks:

- el parser JSON del LLM;
- la validación de argumentos de las tools;
- `pending.py` (expiración y usuario distinto);
- la generación de xlsx y pdf (se abren y tienen las filas esperadas);
- el troceado de mensajes de más de 4096 caracteres;
- la whitelist.

Los tests se ejecutan solos con **GitHub Actions** en cada PR y con `pre-commit` (ruff + pytest rápido).

## 13. Guion de demo (3 min)

1. 🎙️ «¿Cómo están mis contenedores?» → «Tienes 4, 3 en marcha y uno caído: worker», más una tabla.
2. 🎙️ «¿Por qué se ha caído el worker?» → resume los logs por voz.
3. 🎙️ «Reinícialo» → botón de confirmar → «Hecho, worker vuelve a estar arriba».
4. 🎙️ «Mándame un informe en PDF y un Excel del consumo» → audio, 2 ficheros y una gráfica.
5. *(Extra)* Lo mismo desde OpenClaw/Hermes vía MCP.

## 14. Riesgos

| Riesgo | Mitigación |
|---|---|
| Gemma no devuelve JSON válido | Parser tolerante, 1 reintento y ejemplos (few-shot) en el prompt |
| Latencia alta (STT + LLM + TTS) | `eleven_flash_v2_5`, `speech` corto y aviso de «grabando audio» mientras procesa |
| Cuota de ElevenLabs | Enviar solo texto y cachear audios |
| Bot con control de Docker | Whitelist, socket-proxy, allowlist por label y confirmación |
| Integración tardía | Contratos y mocks desde la fase 0 |
