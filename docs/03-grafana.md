# 3. Grafana

Same for **Docker and VMware**.

## 3.1 With this repository's stack

Nothing to configure. On startup, Grafana loads:

- the `Prometheus` **datasource** (uid `prometheus`) → `monitoring/grafana/provisioning/datasources/prometheus.yml`
- the *CloudGuard WAF - Prometheus* **dashboard** in the *CloudGuard WAF* folder → `monitoring/grafana/dashboards/cloudguard-waf.json`

Steps:

1. Open `http://<server>:3000`.
2. Log in with `GRAFANA_USER` / `GRAFANA_PASSWORD` from `.env`.
3. **Dashboards → CloudGuard WAF → CloudGuard WAF - Prometheus**.
4. The **Gateway** selector at the top left filters by the `gateway` label from `waf-agents.yml`.

## 3.2 In an existing Grafana

1. **Dashboards → New → Import**.
2. Upload `monitoring/grafana/dashboards/cloudguard-waf.json`.
3. If their Prometheus datasource does not have uid `prometheus`, edit the JSON before importing it and replace `"uid": "prometheus"` with the right uid (it is in the URL of *Connections → Data sources → <datasource>*).

## 3.3 Panels

| Row | Panel | What it shows |
| --- | --- | --- |
| Agent | Agent scrape | UP/DOWN for each WAF |
| Agent | IPS detections (range) | Approximate total of IPS matches in detect mode over the selected time range |
| Agent | IPS preventions (range) | Same, in prevent mode |
| Agent | Nano-service restarts | Watchdog counter |
| Agent | Protected assets | Number of assets on the agent |
| Agent | IPS engine matches per minute | detect / prevent / ignore per gateway |
| Agent | CPU per process | CPU % of each nano-service |
| Agent | Physical memory per process | RSS of each nano-service (the handler adds up all its workers) |
| Per asset (optional) | Management API / Per-asset summary / Requests per asset / Malicious requests per asset | Require the API exporter ([05](05-per-asset-api-exporter.md)) |

If you do not enable the exporter, the *per asset* row stays empty. You can collapse it or delete it.

## 3.4 Customizing

Queries follow the rules in [04-metrics-and-promql.md](04-metrics-and-promql.md). Read it before you build new panels: the agent's metrics **are not cumulative counters**, and `rate()` gives wrong results.

Next: [04-metrics-and-promql.md](04-metrics-and-promql.md)
