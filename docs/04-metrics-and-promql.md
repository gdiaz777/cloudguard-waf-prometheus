# 4. Available metrics and how to query them

Same for **Docker and VMware**: it is the same agent.

Validated with agent **1.2637.8044694** (October 2026). Other versions may publish a different set; check with `curl -s http://<waf>:7465/metrics | grep '^# TYPE' | sort -u`.

## 4.1 Catalog

The endpoint publishes **17 metrics**, all of type `gauge`. They all carry `agent="<agent UUID>"`, and none of them carries the asset name.

| Metric | Own labels | What it measures | Behavior |
| --- | --- | --- | --- |
| `detect_action_matches_counter` | `id`, `metricName="IPS Stats"` | IPS engine matches in detect mode | Value of the last window (~15 s); drops back to 0 |
| `prevent_action_matches_counter` | `id`, `metricName="IPS Stats"` | IPS matches in prevent mode | Same |
| `ignore_action_matches_counter` | `id`, `metricName="IPS Stats"` | IPS matches ignored by exceptions | Same |
| `all_assets_counter` | `id`, `metricName="Assets Count"` | Number of protected assets | Only published when the services start |
| `nano_service_restarts_counter` | `metricName="Watchdog Metrics"` | Nano-service starts by the watchdog | Cumulative since the agent started |
| `cpu_usage_percentage_average` / `_max` / `_last_value` | `process`, `metricName` | Overall and per-process CPU, in % | Intermittent |
| `general_total_used_memory_average` / `_max` / `_min` | `process`, `metricName` | Total memory used | Intermittent |
| `service_physical_memory_size_kb_average` / `_max` / `_min` | `process`, `id` | Physical memory (RSS) per nano-service, in KB | About 1 sample per minute, 0 in between |
| `service_virtual_memory_size_kb_average` / `_max` / `_min` | `process`, `id` | Virtual memory per nano-service, in KB | Same |

Label meanings:

- `agent`: the agent UUID (the same one shown by `cpnano -s`).
- `id`: `<hostname>_<n>`. The *HTTP Transaction Handler* runs as **one process per worker** (12 in the lab), and each one publishes its own series.
- `process`: nano-service (`cp-nano-orchestration`, `cp-nano-http-transaction-handler`, `cp-nano-prometheus`…).
- `gateway`, `platform`, `site`: added by you in `waf-agents.yml`.

## 4.2 What it does NOT publish (although the documentation lists it)

The [official documentation](https://waf-doc.inext.checkpoint.com/how-to/integrate-cloudguard-waf-with-prometheus) lists metrics for requests (total, per method, unique sources), blocking, threat levels, attack types (SQLi, XSS, RCE, path traversal, LDAP, XXE…), response codes and latency.

**None of them appeared on the tested agent**, after 27 minutes of continuous traffic with SQLi, XSS, path traversal, RCE and LDAP injection.

Diagnosis: with `D_WAAP=Trace` debug enabled, the *HTTP Transaction Handler* does compute that telemetry per asset (`Log the decision for telemetry. Asset ID: … Threat level: …`). However, it does not register it on its internal `/service-metrics` endpoint, which is what `cp-nano-prometheus` aggregates. In this version that data is only sent to Infinity Portal.

**Consequence:** do not promise "attack types" or "response codes" panels until Check Point confirms which agent version exports them. For a per-asset view, use the [API exporter](05-per-asset-api-exporter.md).

## 4.3 How to write PromQL

### Rule 1: do not use `rate()` or `increase()` on `*_matches_counter`

Despite the `counter` name, these are `gauge`s holding the value of **the last ~15 s window**. Measured in the lab, under constant traffic the same worker alternates `22 → 0 → 22`. `rate()` treats every drop as a counter reset and returns meaningless values.

Correct: sum the samples.

```promql
# IPS matches (detect) in the last 5 minutes, per gateway
sum by (gateway) (sum_over_time(detect_action_matches_counter[5m]))

# Per minute (for a graph)
sum by (gateway) (sum_over_time(detect_action_matches_counter[1m]))

# Total over the Grafana dashboard time range
sum(sum_over_time(detect_action_matches_counter[$__range]))
```

This is an **approximation**. It needs `scrape_interval: 15s` so that no window is missed.

### Rule 2: always aggregate the workers

Each handler worker has its own series (`id`). Aggregate by `gateway` or by `agent`; never show series per `id`.

### Rule 3: use `max_over_time` for CPU, memory and assets

They are published intermittently and are 0 between samples.

```promql
# CPU per process
max by (gateway, process) (max_over_time(cpu_usage_percentage_average{metricName="CPU process usage"}[2m]))

# Physical memory per process, in bytes (the handler adds up its workers)
sum by (gateway, process) (max_over_time(service_physical_memory_size_kb_average[5m])) * 1024

# Protected assets (only published when the services start)
max by (gateway) (max_over_time(all_assets_counter[1d]))
```

### Rule 4: for restarts, watch the change, not the absolute value

`nano_service_restarts_counter` starts high, because it counts every start since the agent was launched. What matters is whether it **increases**:

```promql
max by (gateway) (max_over_time(nano_service_restarts_counter[15m]))
  - max by (gateway) (max_over_time(nano_service_restarts_counter[15m] offset 15m)) > 0
```

## 4.4 How it works internally (for troubleshooting)

Every ~15 s, `cp-nano-prometheus` queries the internal REST endpoint `/service-metrics` of each nano-service and publishes the aggregate on port 7465:

```bash
# On the WAF (docker exec … / SSH to the VM)
curl -s http://127.0.0.1:7777/service-metrics    # orchestrator
curl -s http://127.0.0.1:12000/service-metrics   # first HTTP Transaction Handler worker (12000-120NN)
```

If a worker does not answer in time, its series is missing from that scrape. That is why sums fluctuate slightly, and it is expected.

Next: [05-per-asset-api-exporter.md](05-per-asset-api-exporter.md)
