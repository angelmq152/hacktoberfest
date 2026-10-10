# AGENTS.md — Instrucciones para agentes de IA

Este repo lo trabajan tres personas, cada una con sus agentes (Antigravity, Claude Code, etc.).
Cualquier agente que entre aquí **debe leer este fichero y `docs/PLAN.md` antes de tocar nada**.

## Proyecto

Bot de Telegram por voz para gestionar Docker y generar informes (Hacktoberfest 2026).
Plan completo, contratos y reparto: [docs/PLAN.md](docs/PLAN.md).

| Parte | Persona | Rama | Carpeta |
|---|---|---|---|
| 1 · Entrada (voz → texto) | Alex | `parte1-entrada` | `input/` |
| 2 · Núcleo (Gemma + tools) | Angel | `parte2-nucleo` | `core/` |
| 3 · Salida (texto → voz) | Pedro | `parte3-salida` | `output/` |

Zona común: `shared/` (`contracts.py`, `config.py`). **No se cambia sin avisar** a las otras dos partes (ver abajo).

## Reglas para agentes

1. Trabaja solo en la carpeta y la rama de tu parte. No edites el código de otra parte: si necesitas algo, pídelo con un mensaje.
2. Los módulos se comunican **solo** con las dataclasses de `shared/contracts.py`. Si un contrato tiene que cambiar, abre antes un mensaje de tipo `contrato`.
3. Nunca commitees secretos (`.env`, tokens, claves). Usa `.env.example` para documentar variables nuevas.
4. Nunca hagas push a `main`, ni force-push, ni merge. Todo entra por PR pequeño.
5. Código: identificadores y comentarios en inglés. Commits, docs y mensajes en español.
6. Los tests (pytest, sin red) tienen que pasar antes de abrir el PR.

## Canal de comunicación entre agentes

La comunicación asíncrona entre agentes (y humanos) se hace con **ficheros `.md` en `docs/agents/`, en esta rama (`docs/plan-implementacion`)**.

### Cómo dejar un mensaje

Crea un fichero nuevo:

```
docs/agents/AAAA-MM-DD-HHMM-<de>-<tema-corto>.md
```

Ejemplo: `docs/agents/2026-10-10-1630-angel-tool-list-names.md`

Con esta cabecera:

```markdown
---
de: angel (claude-code)          # persona (agente)
para: alex                        # alex | angel | pedro | todos
tipo: pregunta                    # pregunta | aviso | contrato | bloqueo | hecho
estado: abierto                   # abierto | respondido | cerrado
---

# Título corto

Qué necesitas o qué has hecho, con rutas de fichero y ejemplos concretos.
```

### Cómo responder

- **No reescribas el mensaje original.** Añade al final una sección `## Respuesta — <persona> (<agente>), AAAA-MM-DD HH:MM`.
- Cambia `estado:` a `respondido`. Lo pasa a `cerrado` quien abrió el hilo cuando lo da por resuelto.

### Al empezar una sesión

1. Haz `git pull` de `docs/plan-implementacion`.
2. Lee los mensajes de `docs/agents/` con `estado: abierto` y `para:` tu persona o `todos`.
3. Respóndelos o tenlos en cuenta antes de ponerte con tu tarea.

### Commits en el canal

- Haz commit solo de ficheros en `docs/agents/`, con mensajes del tipo `agents: <de> → <para>: <tema>`.
- Haz push directamente a `docs/plan-implementacion`. Es la única rama donde se permite push directo, y solo para este canal.
- Si hay conflicto, `git pull --rebase` y vuelve a intentarlo. Como cada mensaje es un fichero nuevo, casi nunca habrá conflictos.
