# 5. (Optional) Per-asset statistics from the Infinity Portal API

Same for **Docker and VMware**: the data comes from the cloud, not from the WAF.

## 5.1 What it is for

The agent's metrics do not include the asset name. The management API does, and it also returns total, legitimate, malicious and critical requests, plus unique source IPs, **per asset**.

| | Agent metrics (:7465) | API exporter (:9466) |
| --- | --- | --- |
| Source | The WAF | Infinity Portal (cloud) |
| Per-asset breakdown | No | **Yes** |
| Real time | Yes (15 s) | **No**: aggregates with a significant delay |
| Credentials | No | API key |
| Recommended use | Alerts and agent health | Trends and per-application inventory |

> In the lab, the API reported 13 requests for an asset while the agent had already processed thousands. Do not use these figures for real-time alerts.

Based on the [waf-stats.sh](https://gist.github.com/mkol5222/a317686a338b4e8c4c742f25d8047d4c) script. Changes from the original: it publishes in Prometheus format instead of printing JSON, caches results for 60 s, renews the token before it expires, retries on a 401, and lets you set the region.

## 5.2 Create the API key

1. Infinity Portal → **Global Settings** (gear icon) → **API Keys** → **New**.
2. **Service:** *CloudGuard WAF* (or *WAF*, depending on the tenant).
3. **Role:** the least-privileged one available (read-only).
4. Save the **Client ID** and the **Secret Key** (the secret is shown only once).

## 5.3 Configure and start

In `monitoring/.env`:

```bash
WAF_API_KEY=<Client ID>
WAF_API_KEY_SECRET=<Secret Key>
# Only if the tenant is in the US region:
# WAF_API_GW=https://cloudinfra-gw-us.portal.checkpoint.com
```

Start the exporter:

```bash
cd monitoring
docker compose --profile api up -d --build
curl -s http://localhost:9466/metrics | grep ^cpwaf
```

Enable scraping by editing `monitoring/prometheus/targets/waf-api.yml`:

```yaml
- targets: ["waf-api-exporter:9466"]
```

(Remove the `[]` line.) Prometheus picks it up without a restart.

## 5.4 Metrics

| Metric | Labels | Meaning |
| --- | --- | --- |
| `cpwaf_api_up` | — | 1 if the last API query succeeded |
| `cpwaf_asset_requests_total` | `asset_id`, `asset_name` | Total requests |
| `cpwaf_asset_legitimate_requests` | same | Legitimate requests |
| `cpwaf_asset_malicious_requests` | same | Malicious requests |
| `cpwaf_asset_critical_requests` | same | Critical severity |
| `cpwaf_asset_high_requests` | same | High severity |
| `cpwaf_asset_unique_sources` | same | Unique source IPs |
| `cpwaf_asset_unique_urls` | same | Unique URLs |
| `cpwaf_asset_learning_elapsed` | same | Learning time (raw value returned by the API) |
| `cpwaf_asset_info` | same + `status`, `readiness`, `recommendation` | Learning status (value is always 1) |

Only `WebApplication` assets are included.

## 5.5 Common problems

| Symptom | Cause | Fix |
| --- | --- | --- |
| `cpwaf_api_up 0` | Credentials or region | `docker logs waf-api-exporter`; check `WAF_API_GW` |
| No assets appear | The key does not include the WAF service | Create the key with the CloudGuard WAF service |
| Very low values | Delayed aggregation in the cloud | Expected |

Next: [06-troubleshooting.md](06-troubleshooting.md)
