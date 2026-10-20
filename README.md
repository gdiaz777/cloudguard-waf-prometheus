# CloudGuard WAF + Prometheus + Grafana

Guía paso a paso para monitorizar un agente **Check Point CloudGuard WAF** con **Prometheus** y **Grafana**, válida para un WAF desplegado en **Docker** o en **VMware** (CloudGuard WAF Gateway).

![Dashboard de Grafana](docs/img/grafana-dashboard.png)

## Cómo funciona

```
 Usuarios ──HTTPS──▶ CloudGuard WAF (VM o contenedor) ──▶ Aplicación
                       │
                       │  cp-nano-prometheus  →  GET http://<waf>:7465/metrics
                       ▼
                  Prometheus (scrape cada 15 s, alertas) ──PromQL──▶ Grafana

 Opcional:  Infinity Portal API ──▶ waf-api-exporter (:9466) ──▶ Prometheus   (estadísticas por asset)
```

1. Activas una *Advanced Setting* en el perfil del WAF (`prometheus=true`).
2. El agente arranca un servicio interno que publica métricas en el **puerto TCP 7465**.
3. Prometheus las lee y Grafana las muestra.

No hace falta instalar nada en el WAF. El agente es el propio *exporter*.

## Qué cambia entre Docker y VMware

| Paso | WAF en Docker | WAF en VMware |
| --- | --- | --- |
| 1. Activar métricas en el portal | Perfil de tipo **Docker** | Perfil de tipo **WAF Gateway** asociado a las VMs |
| 2. Exponer el puerto 7465 | Publicarlo en el contenedor: `-p 7465:7465` | No hay mapeo: la VM escucha en su IP. Abrir **TCP 7465** en firewalls/NSX desde la IP de Prometheus |
| 3. Verificar en el WAF | `docker exec <contenedor> ...` | SSH a la VM con el usuario `admin` |
| 4. Target en Prometheus | `host.docker.internal:7465` o `<IP del host>:7465` | `<IP de gestión de la VM>:7465` (una línea por VM) |
| 5. Prometheus y Grafana | **Igual** | **Igual** |
| 6. Dashboard y alertas | **Igual** | **Igual** |

Todo lo que no aparece en esta tabla es idéntico en los dos casos.

## Contenido del repositorio

```
.
├── README.md                     ← esta guía
├── docs/
│   ├── 01-activar-metricas-en-el-waf.md   ← paso 1 en detalle (Docker y VMware)
│   ├── 02-prometheus.md
│   ├── 03-grafana.md
│   ├── 04-metricas-y-promql.md            ← qué métricas hay y cómo consultarlas
│   ├── 05-exporter-api-por-asset.md       ← opcional: datos por asset vía API
│   └── 06-troubleshooting.md
├── monitoring/                   ← stack Prometheus + Grafana (sirve para Docker y VMware)
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── alerts.yml
│   │   └── targets/
│   │       ├── waf-agents.yml   ← AQUÍ se ponen los WAF a monitorizar
│   │       └── waf-api.yml
│   ├── grafana/                  ← datasource + dashboard provisionados
│   └── waf-api-exporter/         ← opcional
└── lab-docker-waf/               ← laboratorio: WAF en Docker + Juice Shop (solo pruebas)
```

## Guía rápida

> Requisitos: un agente CloudGuard WAF ya desplegado y conectado a Infinity Portal, y un servidor Linux con Docker y Docker Compose para Prometheus y Grafana.

### Paso 1. Activar las métricas en el WAF (Infinity Portal)

1. Entra en Infinity Portal → **WAF** → **Policy → Profiles**.
2. Abre el perfil del agente:
   - **Docker:** el perfil de tipo *Docker* (por ejemplo, "Docker Agents").
   - **VMware:** el perfil de tipo *WAF Gateway* al que están asociadas las VMs.
3. Pestaña **Advanced** → tabla **Advanced Settings** → botón **+**.
4. Escribe la clave `prometheus` y el valor `true`.
5. Pulsa **Publish** y después **Enforce**.

> ⚠️ Al recibir el ajuste, el agente **reinicia sus nano-servicios**. Durante unos segundos el tráfico pasa sin inspección (fail-open). En producción, hazlo en una ventana de cambio.

Detalle: [docs/01-activar-metricas-en-el-waf.md](docs/01-activar-metricas-en-el-waf.md)

### Paso 2. Comprobar que el WAF publica las métricas

Espera 1–2 minutos después del Enforce.

**Docker** (dentro del host del contenedor):

```bash
docker exec <contenedor-waf> sh -c 'netstat -ltnp | grep 7465'
curl -s http://localhost:7465/metrics | head
```

**VMware** (SSH a la VM con `admin`):

```bash
netstat -ltnp | grep 7465
curl -s http://localhost:7465/metrics | head
```

En los dos casos debes ver el proceso `cp-nano-prometheus` escuchando en el 7465 y líneas como esta:

```
# TYPE cpu_usage_percentage_average gauge
cpu_usage_percentage_average{agent="3c95…",metricName="CPU general usage",process="cp-nano-orchestration"} 0.11
```

### Paso 3. Abrir el puerto 7465 hacia Prometheus

- **Docker:** publica el puerto en el contenedor del WAF (`-p 7465:7465` o `ports: ["7465:7465"]` en compose).
- **VMware:** permite **TCP 7465** desde la IP del servidor Prometheus hasta la IP de gestión de cada VM (firewall perimetral, NSX, ACLs entre VLANs).

Prueba desde el servidor de Prometheus:

```bash
curl -s http://<IP-del-WAF>:7465/metrics | head
```

> 🔒 El endpoint **no tiene autenticación ni TLS**. Ábrelo solo a la IP de Prometheus y nunca hacia Internet.

### Paso 4. Desplegar Prometheus y Grafana

```bash
git clone git@github.com:gdiaz777/cloudguard-waf-prometheus.git
cd cloudguard-waf-prometheus/monitoring
cp .env.example .env          # cambia GRAFANA_PASSWORD
```

Edita `prometheus/targets/waf-agents.yml` y deja una entrada por WAF:

```yaml
# Docker
- targets: ["host.docker.internal:7465"]     # o "<IP del host Docker>:7465"
  labels: {gateway: lab-docker, platform: docker}

# VMware: una entrada por VM
- targets: ["10.10.20.11:7465"]
  labels: {gateway: waf-gw-01, platform: vmware, site: cpd-madrid}
```

> No uses la etiqueta `agent`: el WAF ya la publica con su UUID y se pisaría.

Arranca el stack:

```bash
docker compose up -d
```

Detalle: [docs/02-prometheus.md](docs/02-prometheus.md)

### Paso 5. Verificar Prometheus

1. Abre `http://<servidor>:9090/targets`.
2. El job **openappsec** debe aparecer en estado **UP**.
3. En `http://<servidor>:9090/graph` ejecuta `detect_action_matches_counter`. Debe devolver series.

### Paso 6. Abrir Grafana

1. Abre `http://<servidor>:3000` e inicia sesión con el usuario y la contraseña de `.env`.
2. Ve a **Dashboards → CloudGuard WAF → CloudGuard WAF - Prometheus**.

El datasource y el dashboard ya vienen provisionados, así que no hay que importar nada. Detalle: [docs/03-grafana.md](docs/03-grafana.md)

### Paso 7 (opcional). Estadísticas por asset desde la API

Las métricas del agente **no incluyen el nombre del asset**. Si quieres un desglose por aplicación, activa el exporter de la API de Infinity Portal: [docs/05-exporter-api-por-asset.md](docs/05-exporter-api-por-asset.md)

## Antes de presentarlo al cliente: qué métricas hay de verdad

Validado con el agente **1.2637.8044694** (octubre 2026):

| Disponible en el agente | No disponible (aunque la documentación lo menciona) |
| --- | --- |
| Coincidencias del motor IPS: detect, prevent, ignore | Peticiones totales y por método HTTP |
| Número de assets protegidos | Tipos de ataque (SQLi, XSS, RCE…) |
| Reinicios de nano-servicios | Niveles de amenaza |
| CPU y memoria por proceso del agente | Códigos de respuesta y latencia |

El agente calcula la telemetría WAAP por asset, pero en esta versión solo la envía a Infinity Portal; no la publica en el 7465. Más detalle y cómo escribir el PromQL correcto (estas métricas no son contadores acumulados): [docs/04-metricas-y-promql.md](docs/04-metricas-y-promql.md)

## Laboratorio en Docker

Para reproducir la demo completa en un solo equipo (WAF en Docker + Juice Shop + monitorización): [lab-docker-waf/README.md](lab-docker-waf/README.md)

## Referencias

- [Integrate CloudGuard WAF with Prometheus](https://waf-doc.inext.checkpoint.com/how-to/integrate-cloudguard-waf-with-prometheus)
- [Deployment using docker command](https://waf-doc.inext.checkpoint.com/getting-started/deploy-enforcement-point/docker/single-docker/deployment-using-docker-command)
- [CloudGuard WAF Gateway en VMware](https://waf-doc.inext.checkpoint.com/getting-started/deploy-enforcement-point/gateway-virtual-machine/vmware)
- [checkpoint/cloudguard-appsec-standalone](https://hub.docker.com/r/checkpoint/cloudguard-appsec-standalone)
- Script original de estadísticas por asset: [gist mkol5222/waf-stats.sh](https://gist.github.com/mkol5222/a317686a338b4e8c4c742f25d8047d4c)
