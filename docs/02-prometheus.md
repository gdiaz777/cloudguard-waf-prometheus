# 2. Prometheus

Prometheus es **igual para Docker y VMware**. Lo único que cambia es la lista de WAF en `monitoring/prometheus/targets/waf-agents.yml`.

## 2.1 Requisitos del servidor

- Linux con Docker y Docker Compose v2.
- Conectividad hacia cada WAF por **TCP 7465**.
- Puertos libres: 9090 (Prometheus) y 3000 (Grafana).

Si el cliente ya tiene Prometheus, no hace falta este stack: copia el job `openappsec` y `alerts.yml` a su configuración (ver 2.5).

## 2.2 Configurar los WAF a monitorizar

Edita `monitoring/prometheus/targets/waf-agents.yml`:

### WAF en Docker

| Dónde está Prometheus | Target |
| --- | --- |
| En el mismo host que el contenedor del WAF | `host.docker.internal:7465` |
| En otro servidor | `<IP del host Docker>:7465` |

```yaml
- targets: ["host.docker.internal:7465"]
  labels:
    gateway: lab-docker
    platform: docker
```

### WAF en VMware

Una entrada por VM, con su IP de gestión:

```yaml
- targets: ["10.10.20.11:7465"]
  labels:
    gateway: waf-gw-01
    platform: vmware
    site: cpd-madrid
- targets: ["10.10.20.12:7465"]
  labels:
    gateway: waf-gw-02
    platform: vmware
    site: cpd-madrid
```

### Reglas para las etiquetas

- `gateway` es el nombre legible que usan el dashboard y las alertas. **Es obligatoria.**
- **No uses `agent`.** El WAF ya publica esa etiqueta con su UUID; si la defines tú, Prometheus renombra la del WAF a `exported_agent` y se pierde la distinción entre agentes.
- Puedes añadir las que quieras: `platform`, `site`, `env`…

Prometheus relee este fichero automáticamente, así que añadir o quitar WAF no requiere reiniciar nada.

## 2.3 Arrancar

```bash
cd monitoring
cp .env.example .env        # cambia GRAFANA_PASSWORD
docker compose up -d
docker compose ps
```

## 2.4 Verificar

1. `http://<servidor>:9090/targets` → job **openappsec** en **UP** para cada WAF.
2. `http://<servidor>:9090/graph` → consulta `up{job="openappsec"}`; debe valer `1`.
3. `http://<servidor>:9090/alerts` → cuatro reglas en estado *Inactive*.

Validación de la configuración sin arrancar nada:

```bash
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/etc/prometheus" prom/prometheus:v3.15.0 \
  check config /etc/prometheus/prometheus.yml
```

## 2.5 Integrar en un Prometheus existente

Añade a su `prometheus.yml`:

```yaml
rule_files:
  - alerts.yml               # copia monitoring/prometheus/alerts.yml

scrape_configs:
  - job_name: openappsec
    scrape_interval: 15s     # importante: ver docs/04-metricas-y-promql.md
    static_configs:
      - targets: ["10.10.20.11:7465"]
        labels: {gateway: waf-gw-01, platform: vmware}
```

Y recarga: `curl -X POST http://<prometheus>:9090/-/reload` (requiere `--web.enable-lifecycle`) o reinicia el servicio.

## 2.6 Parámetros importantes

| Parámetro | Valor | Por qué |
| --- | --- | --- |
| `scrape_interval` | **15s** | El agente renueva sus valores en ventanas de ~15 s. Con un intervalo mayor se pierden ventanas y los totales salen por debajo de lo real |
| `job_name` | `openappsec` | Es el nombre que usan la documentación oficial, el dashboard y las alertas |
| Retención | 15d (`PROMETHEUS_RETENTION` en `.env`) | Ajustable |

## 2.7 Alertas incluidas

Fichero: `monitoring/prometheus/alerts.yml`.

| Alerta | Se dispara cuando | Severidad |
| --- | --- | --- |
| `WafAgentMetricsDown` | Prometheus no puede leer el 7465 durante 2 min | critical |
| `WafDetectionSpike` | Detect + prevent IPS en 5 min > 500, sostenido 5 min | warning |
| `WafNanoServiceRestarts` | El contador de reinicios del watchdog sube respecto a hace 15 min | warning |
| `WafApiExporterFailing` | El exporter opcional no puede consultar la API durante 10 min | info |

**Ajusta el umbral de `WafDetectionSpike`** a la línea base del cliente. En el laboratorio, con ataques continuos, la expresión daba unas 375. Recomendación: medir una semana y fijar 3–5 veces el percentil 95.

Para enviar las alertas por correo, Teams, etc. hace falta Alertmanager, que queda fuera de este repo.

Siguiente: [03-grafana.md](03-grafana.md)
