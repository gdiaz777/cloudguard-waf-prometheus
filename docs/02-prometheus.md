# 2. Prometheus

Prometheus is **the same for Docker and VMware**. The only difference is the list of WAFs in `monitoring/prometheus/targets/waf-agents.yml`.

## 2.1 Server requirements

- Linux with Docker and Docker Compose v2.
- Network access to each WAF on **TCP 7465**.
- Free ports: 9090 (Prometheus) and 3000 (Grafana).

If the customer already runs Prometheus, this stack is not needed: copy the `openappsec` job and `alerts.yml` into their configuration (see 2.5).

## 2.2 Configure the WAFs to monitor

Edit `monitoring/prometheus/targets/waf-agents.yml`:

### WAF in Docker

| Where Prometheus runs | Target |
| --- | --- |
| On the same host as the WAF container | `host.docker.internal:7465` |
| On another server | `<Docker host IP>:7465` |

```yaml
- targets: ["host.docker.internal:7465"]
  labels:
    gateway: lab-docker
    platform: docker
```

### WAF in VMware

One entry per VM, using its management IP:

```yaml
- targets: ["10.10.20.11:7465"]
  labels:
    gateway: waf-gw-01
    platform: vmware
    site: dc-madrid
- targets: ["10.10.20.12:7465"]
  labels:
    gateway: waf-gw-02
    platform: vmware
    site: dc-madrid
```

### Label rules

- `gateway` is the readable name used by the dashboard and the alerts. **It is required.**
- **Do not use `agent`.** The WAF already publishes that label with its UUID. If you set it yourself, Prometheus renames the WAF's label to `exported_agent` and you can no longer tell agents apart.
- Add any other labels you need: `platform`, `site`, `env`…

Prometheus re-reads this file automatically, so adding or removing a WAF needs no restart.

## 2.3 Start

```bash
cd monitoring
cp .env.example .env        # change GRAFANA_PASSWORD
docker compose up -d
docker compose ps
```

## 2.4 Verify

1. `http://<server>:9090/targets` → the **openappsec** job is **UP** for every WAF.
2. `http://<server>:9090/graph` → query `up{job="openappsec"}`; it must be `1`.
3. `http://<server>:9090/alerts` → four rules in the *Inactive* state.

To validate the configuration without starting anything:

```bash
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/etc/prometheus" prom/prometheus:v3.15.0 \
  check config /etc/prometheus/prometheus.yml
```

## 2.5 Integrate into an existing Prometheus

Add to their `prometheus.yml`:

```yaml
rule_files:
  - alerts.yml               # copy monitoring/prometheus/alerts.yml

scrape_configs:
  - job_name: openappsec
    scrape_interval: 15s     # important: see docs/04-metrics-and-promql.md
    static_configs:
      - targets: ["10.10.20.11:7465"]
        labels: {gateway: waf-gw-01, platform: vmware}
```

Then reload with `curl -X POST http://<prometheus>:9090/-/reload` (requires `--web.enable-lifecycle`), or restart the service.

## 2.6 Key settings

| Setting | Value | Why |
| --- | --- | --- |
| `scrape_interval` | **15s** | The agent refreshes its values in windows of about 15 s. A longer interval misses windows and totals come out lower than reality |
| `job_name` | `openappsec` | The name used by the official documentation, the dashboard and the alerts |
| Retention | 15d (`PROMETHEUS_RETENTION` in `.env`) | Adjustable |

## 2.7 Included alerts

File: `monitoring/prometheus/alerts.yml`.

| Alert | Fires when | Severity |
| --- | --- | --- |
| `WafAgentMetricsDown` | Prometheus cannot read port 7465 for 2 min | critical |
| `WafDetectionSpike` | IPS detect + prevent matches in 5 min > 500, sustained for 5 min | warning |
| `WafNanoServiceRestarts` | The watchdog restart counter has increased compared with 15 min ago | warning |
| `WafApiExporterFailing` | The optional exporter cannot query the API for 10 min | info |

**Tune the `WafDetectionSpike` threshold** to the customer's baseline. In the lab, with continuous attacks, the expression was around 375. Recommendation: measure for a week and set it to 3–5 times the 95th percentile.

Sending alerts by email, Teams, etc. requires Alertmanager, which is out of the scope of this repository.

Next: [03-grafana.md](03-grafana.md)
