# hackbot-demo

Stack de contenedores de PRUEBA para que el bot de Telegram tenga que listar, reiniciar y ver logs.
Solo interno: sin puertos publicados, sin Caddy, sin DNS. Red propia `hackbot-demo_net`.

## Servicios (todos `hackbot-demo-*`)

Con label `hackbot.manage=true`: glpi, grafana, affine, nginx, redis, postgres, uptime-kuma,
logger (logs continuos), worker (sale con error a proposito y queda caido), unhealthy (healthcheck que falla).

Sin label (soporte): glpi-db, affine-db, affine-redis, affine-migration (job one-shot, termina con exito).

RAM: limites con `mem_limit`, uso real aproximado 1.5 GB.

## Uso

```bash
cp demo/.env.example demo/.env   # y rellenar con: openssl rand -hex 16
docker compose -f demo/compose.yaml up -d
docker compose -f demo/compose.yaml down -v   # baja y borra volumenes
```

Notas: GLPI y AFFiNE arrancan sin configurar (instalador web / primer admin), no hace falta para la demo.
