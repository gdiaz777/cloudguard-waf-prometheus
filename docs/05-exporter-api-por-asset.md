# 5. (Opcional) Estadísticas por asset desde la API de Infinity Portal

Igual para **Docker y VMware**: los datos salen de la nube, no del WAF.

## 5.1 Para qué sirve

Las métricas del agente no traen el nombre del asset. La API de gestión sí, y además da peticiones totales, legítimas, maliciosas, críticas e IPs únicas **por asset**.

| | Métricas del agente (:7465) | Exporter de la API (:9466) |
| --- | --- | --- |
| Origen | El WAF | Infinity Portal (nube) |
| Desglose por asset | No | **Sí** |
| Tiempo real | Sí (15 s) | **No**: agregados con bastante retraso |
| Credenciales | No | API key |
| Uso recomendado | Alertas y salud del agente | Tendencias e inventario por aplicación |

> En el laboratorio, la API indicaba 13 peticiones en un asset cuando el agente ya había procesado miles. No uses estas cifras para alertas en tiempo real.

Basado en el script [waf-stats.sh](https://gist.github.com/mkol5222/a317686a338b4e8c4c742f25d8047d4c). Respecto al original se ha cambiado lo siguiente: ahora publica en formato Prometheus en lugar de imprimir JSON, cachea 60 s, renueva el token antes de que caduque, reintenta ante un 401 y permite configurar la región.

## 5.2 Crear la API key

1. Infinity Portal → **Global Settings** (icono de engranaje) → **API Keys** → **New**.
2. **Service:** *CloudGuard WAF* (o *WAF*, según el tenant).
3. **Role:** el de menor privilegio disponible (solo lectura).
4. Guarda el **Client ID** y la **Secret Key** (la secret solo se muestra una vez).

## 5.3 Configurar y arrancar

En `monitoring/.env`:

```bash
WAF_API_KEY=<Client ID>
WAF_API_KEY_SECRET=<Secret Key>
# Solo si el tenant está en US:
# WAF_API_GW=https://cloudinfra-gw-us.portal.checkpoint.com
```

Arranca el exporter:

```bash
cd monitoring
docker compose --profile api up -d --build
curl -s http://localhost:9466/metrics | grep ^cpwaf
```

Activa el scrape editando `monitoring/prometheus/targets/waf-api.yml`:

```yaml
- targets: ["waf-api-exporter:9466"]
```

(Quita la línea `[]`.) Prometheus lo recoge sin reiniciar.

## 5.4 Métricas

| Métrica | Etiquetas | Significado |
| --- | --- | --- |
| `cpwaf_api_up` | — | 1 si la última consulta a la API fue correcta |
| `cpwaf_asset_requests_total` | `asset_id`, `asset_name` | Peticiones totales |
| `cpwaf_asset_legitimate_requests` | igual | Peticiones legítimas |
| `cpwaf_asset_malicious_requests` | igual | Peticiones maliciosas |
| `cpwaf_asset_critical_requests` | igual | Severidad crítica |
| `cpwaf_asset_high_requests` | igual | Severidad alta |
| `cpwaf_asset_unique_sources` | igual | IPs origen únicas |
| `cpwaf_asset_unique_urls` | igual | URLs únicas |
| `cpwaf_asset_learning_elapsed` | igual | Tiempo de aprendizaje (valor tal cual lo da la API) |
| `cpwaf_asset_info` | igual + `status`, `readiness`, `recommendation` | Estado del aprendizaje (valor siempre 1) |

Solo se incluyen los assets de tipo `WebApplication`.

## 5.5 Problemas comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `cpwaf_api_up 0` | Credenciales o región | `docker logs waf-api-exporter`; revisa `WAF_API_GW` |
| No aparece ningún asset | La key no tiene el servicio WAF | Crea la key con el servicio CloudGuard WAF |
| Valores muy bajos | Agregación en la nube con retraso | Es esperado |

Siguiente: [06-troubleshooting.md](06-troubleshooting.md)
