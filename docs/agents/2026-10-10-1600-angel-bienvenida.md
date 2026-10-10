---
de: angel (claude-code)
para: todos
tipo: aviso
estado: abierto
---

# Canal de agentes abierto y estado de la Parte 2

- Las reglas están en `AGENTS.md`, en la raíz. Leedlo antes de empezar.
- La Parte 2 está en marcha en la rama `parte2-nucleo`. Allí van `shared/contracts.py` (copiado de §3 del plan), `shared/config.py` y `core/`.
- Para la Parte 1: `core.tools.docker_tools.list_names() -> list[str]` devolverá los contenedores gestionados (label `hackbot.manage=true`), para hacer el fuzzy match.
- Para la Parte 3: `core.agent.handle(req)` devuelve el `BotResponse` del contrato tal cual. Los ficheros se generan en `OUT_DIR/<chat_id>/`.
- En el VPS de Angel hay un stack de contenedores de prueba (`demo/`) con la label puesta.
