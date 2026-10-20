# 4. Métricas disponibles y cómo consultarlas

Igual para **Docker y VMware**: es el mismo agente.

Validado con el agente **1.2637.8044694** (octubre 2026). En otras versiones el catálogo puede cambiar; compruébalo con `curl -s http://<waf>:7465/metrics | grep '^# TYPE' | sort -u`.

## 4.1 Catálogo

El endpoint publica **17 métricas**, todas de tipo `gauge`. Todas llevan `agent="<UUID del agente>"`, y ninguna lleva el nombre del asset.

| Métrica | Etiquetas propias | Qué mide | Comportamiento |
| --- | --- | --- | --- |
| `detect_action_matches_counter` | `id`, `metricName="IPS Stats"` | Coincidencias del motor IPS en modo detect | Valor de la última ventana (~15 s); vuelve a 0 |
| `prevent_action_matches_counter` | `id`, `metricName="IPS Stats"` | Coincidencias IPS en modo prevent | Igual |
| `ignore_action_matches_counter` | `id`, `metricName="IPS Stats"` | Coincidencias IPS ignoradas por excepciones | Igual |
| `all_assets_counter` | `id`, `metricName="Assets Count"` | Número de assets protegidos | Solo se publica cuando arrancan los servicios |
| `nano_service_restarts_counter` | `metricName="Watchdog Metrics"` | Arranques de nano-servicios por el watchdog | Acumulado desde que arrancó el agente |
| `cpu_usage_percentage_average` / `_max` / `_last_value` | `process`, `metricName` | CPU general y por proceso, en % | Intermitente |
| `general_total_used_memory_average` / `_max` / `_min` | `process`, `metricName` | Memoria total usada | Intermitente |
| `service_physical_memory_size_kb_average` / `_max` / `_min` | `process`, `id` | Memoria física (RSS) por nano-servicio, en KB | ~1 muestra por minuto, 0 entre medias |
| `service_virtual_memory_size_kb_average` / `_max` / `_min` | `process`, `id` | Memoria virtual por nano-servicio, en KB | Igual |

Significado de las etiquetas:

- `agent`: UUID del agente (el mismo que muestra `cpnano -s`).
- `id`: `<hostname>_<n>`. El *HTTP Transaction Handler* corre como **un proceso por worker** (12 en el laboratorio), y cada uno publica su propia serie.
- `process`: nano-servicio (`cp-nano-orchestration`, `cp-nano-http-transaction-handler`, `cp-nano-prometheus`…).
- `gateway`, `platform`, `site`: las añades tú en `waf-agents.yml`.

## 4.2 Lo que NO publica (aunque la documentación lo enumera)

La [documentación oficial](https://waf-doc.inext.checkpoint.com/how-to/integrate-cloudguard-waf-with-prometheus) lista métricas de peticiones (totales, por método, IPs únicas), bloqueos, niveles de amenaza, tipos de ataque (SQLi, XSS, RCE, path traversal, LDAP, XXE…), códigos de respuesta y latencia.

**En el agente probado no aparecieron**, tras 27 minutos de tráfico continuo con SQLi, XSS, path traversal, RCE y LDAP injection.

Diagnóstico: con debug `D_WAAP=Trace` el *HTTP Transaction Handler* sí calcula esa telemetría por asset (`Log the decision for telemetry. Asset ID: … Threat level: …`). Sin embargo, no la registra en su endpoint interno `/service-metrics`, que es lo que agrega `cp-nano-prometheus`. En esta versión esos datos solo se envían a Infinity Portal.

**Consecuencia:** no prometas paneles de "tipos de ataque" o "códigos de respuesta" hasta confirmar con Check Point en qué versión se exportan. Para una vista por asset usa el [exporter de la API](05-exporter-api-por-asset.md).

## 4.3 Cómo escribir el PromQL

### Regla 1: no uses `rate()` ni `increase()` con `*_matches_counter`

Aunque se llamen `counter`, son `gauge` con el valor de **la última ventana de ~15 s**. Medido en laboratorio, con tráfico constante el mismo worker alterna `22 → 0 → 22`. `rate()` interpreta cada bajada como un reinicio del contador y da resultados sin sentido.

Correcto: suma las muestras.

```promql
# Coincidencias IPS (detect) en los últimos 5 minutos, por gateway
sum by (gateway) (sum_over_time(detect_action_matches_counter[5m]))

# Por minuto (para una gráfica)
sum by (gateway) (sum_over_time(detect_action_matches_counter[1m]))

# Total en el rango del dashboard de Grafana
sum(sum_over_time(detect_action_matches_counter[$__range]))
```

Es una **aproximación**. Requiere `scrape_interval: 15s` para no perder ventanas.

### Regla 2: agrega siempre los workers

Cada worker del handler tiene su propia serie (`id`). Agrega por `gateway` o por `agent`, nunca muestres series por `id`.

### Regla 3: usa `max_over_time` con CPU, memoria y assets

Se publican de forma intermitente y valen 0 entre muestras.

```promql
# CPU por proceso
max by (gateway, process) (max_over_time(cpu_usage_percentage_average{metricName="CPU process usage"}[2m]))

# Memoria física por proceso, en bytes (el handler suma sus workers)
sum by (gateway, process) (max_over_time(service_physical_memory_size_kb_average[5m])) * 1024

# Assets protegidos (solo se publica al arrancar los servicios)
max by (gateway) (max_over_time(all_assets_counter[1d]))
```

### Regla 4: reinicios = cambio, no valor absoluto

`nano_service_restarts_counter` arranca alto (cuenta todos los arranques desde que se inició el agente). Lo relevante es que **suba**:

```promql
max by (gateway) (max_over_time(nano_service_restarts_counter[15m]))
  - max by (gateway) (max_over_time(nano_service_restarts_counter[15m] offset 15m)) > 0
```

## 4.4 Cómo funciona por dentro (para troubleshooting)

`cp-nano-prometheus` consulta cada ~15 s el endpoint REST interno `/service-metrics` de cada nano-servicio y publica el agregado en el 7465:

```bash
# Dentro del WAF (docker exec … / SSH a la VM)
curl -s http://127.0.0.1:7777/service-metrics    # orquestador
curl -s http://127.0.0.1:12000/service-metrics   # primer worker del HTTP Transaction Handler (12000-120NN)
```

Si un worker no responde a tiempo, su serie falta en ese scrape. Por eso las sumas oscilan ligeramente, y es normal.

Siguiente: [05-exporter-api-por-asset.md](05-exporter-api-por-asset.md)
