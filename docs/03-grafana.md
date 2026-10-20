# 3. Grafana

Igual para **Docker y VMware**.

## 3.1 Con el stack de este repo

No hay que configurar nada. Al arrancar, Grafana carga:

- **Datasource** `Prometheus` (uid `prometheus`) → `monitoring/grafana/provisioning/datasources/prometheus.yml`
- **Dashboard** *CloudGuard WAF - Prometheus* en la carpeta *CloudGuard WAF* → `monitoring/grafana/dashboards/cloudguard-waf.json`

Pasos:

1. Abre `http://<servidor>:3000`.
2. Inicia sesión con `GRAFANA_USER` / `GRAFANA_PASSWORD` de `.env`.
3. **Dashboards → CloudGuard WAF → CloudGuard WAF - Prometheus**.
4. Arriba a la izquierda, el selector **Gateway** filtra por la etiqueta `gateway` de `waf-agents.yml`.

## 3.2 En un Grafana existente

1. **Dashboards → New → Import**.
2. Sube `monitoring/grafana/dashboards/cloudguard-waf.json`.
3. Si su datasource Prometheus no tiene uid `prometheus`, edita el JSON antes de importarlo y sustituye `"uid": "prometheus"` por el uid correcto (lo ves en *Connections → Data sources → <datasource>*, en la URL).

## 3.3 Paneles

| Fila | Panel | Qué muestra |
| --- | --- | --- |
| Agente | Scrape del agente | UP/DOWN de cada WAF |
| Agente | Detecciones IPS (rango) | Total aproximado de coincidencias IPS en modo detect en el rango de tiempo elegido |
| Agente | Prevenciones IPS (rango) | Igual, en modo prevent |
| Agente | Reinicios de nano-servicios | Contador del watchdog |
| Agente | Assets protegidos | Número de assets del agente |
| Agente | Coincidencias del motor IPS por minuto | detect / prevent / ignore por gateway |
| Agente | CPU por proceso | % de CPU de cada nano-servicio |
| Agente | Memoria física por proceso | RSS de cada nano-servicio (el handler suma todos sus workers) |
| Por asset (opcional) | API de gestión / Resumen por asset / Peticiones por asset / Maliciosas por asset | Requieren el exporter de la API ([05](05-exporter-api-por-asset.md)) |

Si no activas el exporter, la fila *por asset* aparece vacía. Puedes plegarla o borrarla.

## 3.4 Personalizar

Las consultas siguen las reglas de [04-metricas-y-promql.md](04-metricas-y-promql.md). Léelo antes de crear paneles nuevos: las métricas del agente **no son contadores acumulados** y `rate()` da resultados incorrectos.

Siguiente: [04-metricas-y-promql.md](04-metricas-y-promql.md)
