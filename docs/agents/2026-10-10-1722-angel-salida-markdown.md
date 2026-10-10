---
de: angel (claude-code)
para: pedro
tipo: aviso
estado: abierto
---

# Cambios en `output/` tras la primera prueba real

En la prueba por Telegram el texto salía con `| tablas |`, `` `código` `` y `**negrita**` literales: el núcleo
manda markdown (como dice el contrato) y `telegram_out` lo enviaba como HTML.

- `output/telegram_out.py`: `md_to_html()` convierte el markdown del núcleo a HTML de Telegram (tablas alineadas en
  `<pre>`, bloques ``` en `<pre>`, `código`, negrita y títulos). El troceo a 4096 se hace ahora por líneas para no
  partir etiquetas. `print()` pasa a `logging` (con stdout redirigido a fichero no salía en el log).
- `output/tts.py`: voz por defecto Sarah (`EXAVITQu4vr4xnSDxMaL`). Rachel es de la biblioteca y con cuenta gratuita
  la API devuelve 402 `paid_plan_required`. `print()` → `logging`.
- Tests nuevos en `tests/test_telegram_out.py`.
