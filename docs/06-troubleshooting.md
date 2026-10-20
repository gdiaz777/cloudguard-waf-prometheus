# 6. Troubleshooting

Donde dice **Docker**, ejecuta los comandos con `docker exec <contenedor-waf> …`. Donde dice **VMware**, ejecútalos por SSH en la VM con el usuario `admin`. Donde no se indica, aplica a los dos.

## 6.1 Tabla de síntomas

| Síntoma | Causa probable | Comprobación / solución |
| --- | --- | --- |
| Nada escucha en el 7465 | El ajuste no ha llegado | `cpnano -s` (registro OK). Revisa que `prometheus=true` está en el **perfil correcto** y que se hizo **Enforce**. Espera 1–2 min |
| **Docker:** target DOWN, pero `docker exec … curl localhost:7465/metrics` funciona | Puerto no publicado | Añade `-p 7465:7465` y recrea el contenedor |
| **VMware:** target DOWN, pero `curl localhost:7465/metrics` funciona en la VM | Red o firewall | `curl http://<IP-VM>:7465/metrics` desde Prometheus. Abre TCP 7465 solo desde esa IP |
| Target DOWN con `context deadline exceeded` | Latencia o filtrado parcial | Revisa la ruta de red y sube `scrape_timeout` (por defecto 10 s) |
| Series que saltan a 0 o desaparecen un instante | Muestras por ventana; algún worker no responde a tiempo | Normal. Usa `sum_over_time` / `max_over_time` ([04](04-metricas-y-promql.md)) |
| `rate()` da valores absurdos | Las métricas no son contadores acumulados | Usa `sum_over_time` |
| Las series tienen `exported_agent` en vez de `agent` | Se definió la etiqueta `agent` en `waf-agents.yml` | Renómbrala a `gateway` |
| Durante unos segundos tras activar el ajuste no hubo inspección | Reinicio de nano-servicios | Esperado; hazlo en ventana de cambio |
| `nano_service_restarts_counter` alto desde el principio | Cuenta todos los arranques desde que se inició el agente | Vigila si **sube**, no el valor absoluto |
| Faltan métricas de tipos de ataque o peticiones | No se exportan en la versión probada | Ver [04 §4.2](04-metricas-y-promql.md#42-lo-que-no-publica-aunque-la-documentación-lo-enumera) |
| Grafana: panel "No data" | Datasource o etiqueta `gateway` | Comprueba en Prometheus `up{job="openappsec"}` y que exista la etiqueta `gateway` |

## 6.2 Comandos útiles en el WAF

```bash
cpnano -s                                       # estado, política, registro, versión
netstat -ltnp | grep 7465                       # servicio cp-nano-prometheus
curl -s http://localhost:7465/metrics | grep '^# TYPE' | sort -u   # catálogo publicado
tail -f /var/log/nano_agent/cp-nano-prometheus.dbg                 # log del servicio

# Lo que agrega cp-nano-prometheus (endpoints internos)
curl -s http://127.0.0.1:7777/service-metrics   # orquestador
curl -s http://127.0.0.1:12000/service-metrics  # primer worker del HTTP Transaction Handler
```

En el log `cp-nano-prometheus.dbg` es normal ver `Failed to get service metrics. Service: <host>_<n>` justo después de un reinicio, mientras arrancan los workers.

## 6.3 Debug avanzado

Para comprobar si el handler calcula la telemetría WAAP:

```bash
cpnano --debug --set --service http-transaction-handler --flags D_WAAP=Trace
# genera tráfico y busca:
grep -h "telemetry" /var/log/nano_agent/cp-nano-http-transaction-handler.dbg* | tail
# MUY IMPORTANTE: vuelve al nivel por defecto (genera mucho log)
cpnano --debug --default --service http-transaction-handler
```

## 6.4 Desactivar las métricas

Borra la Advanced Setting `prometheus` del perfil (o ponla a `false`) y haz **Publish + Enforce**. No se ha probado en laboratorio, pero es previsible que los nano-servicios se reinicien de nuevo, igual que al activarlo: hazlo también en ventana de cambio.
