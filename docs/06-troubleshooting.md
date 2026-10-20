# 6. Troubleshooting

Where it says **Docker**, run the commands with `docker exec <waf-container> …`. Where it says **VMware**, run them over SSH on the VM as `admin`. Where nothing is stated, it applies to both.

## 6.1 Symptoms

| Symptom | Likely cause | Check / fix |
| --- | --- | --- |
| Nothing listens on 7465 | The setting has not arrived | `cpnano -s` (registration OK). Check that `prometheus=true` is on the **right profile** and that **Enforce** was done. Wait 1–2 min |
| **Docker:** target DOWN, but `docker exec … curl localhost:7465/metrics` works | Port not published | Add `-p 7465:7465` and recreate the container |
| **VMware:** target DOWN, but `curl localhost:7465/metrics` works on the VM | Network or firewall | Run `curl http://<VM-IP>:7465/metrics` from Prometheus. Allow TCP 7465 from that IP only |
| Target DOWN with `context deadline exceeded` | Latency or partial filtering | Check the network path and raise `scrape_timeout` (default 10 s) |
| Series that drop to 0 or briefly disappear | Per-window samples; a worker did not answer in time | Expected. Use `sum_over_time` / `max_over_time` ([04](04-metrics-and-promql.md)) |
| `rate()` returns absurd values | The metrics are not cumulative counters | Use `sum_over_time` |
| Series carry `exported_agent` instead of `agent` | An `agent` label was set in `waf-agents.yml` | Rename it to `gateway` |
| No inspection for a few seconds after enabling the setting | Nano-service restart | Expected; do it in a change window |
| `nano_service_restarts_counter` is high from the start | It counts every start since the agent was launched | Watch whether it **increases**, not its absolute value |
| Attack-type or request metrics are missing | Not exported in the tested version | See [04 §4.2](04-metrics-and-promql.md#42-what-it-does-not-publish-although-the-documentation-lists-it) |
| Grafana: "No data" panel | Datasource or `gateway` label | In Prometheus, check `up{job="openappsec"}` and that the `gateway` label exists |

## 6.2 Useful commands on the WAF

```bash
cpnano -s                                       # status, policy, registration, version
netstat -ltnp | grep 7465                       # cp-nano-prometheus service
curl -s http://localhost:7465/metrics | grep '^# TYPE' | sort -u   # published catalog
tail -f /var/log/nano_agent/cp-nano-prometheus.dbg                 # service log

# What cp-nano-prometheus aggregates (internal endpoints)
curl -s http://127.0.0.1:7777/service-metrics   # orchestrator
curl -s http://127.0.0.1:12000/service-metrics  # first HTTP Transaction Handler worker
```

Right after a restart, it is normal to see `Failed to get service metrics. Service: <host>_<n>` in `cp-nano-prometheus.dbg` while the workers start up.

## 6.3 Advanced debug

To check whether the handler computes WAAP telemetry:

```bash
cpnano --debug --set --service http-transaction-handler --flags D_WAAP=Trace
# generate traffic and look for:
grep -h "telemetry" /var/log/nano_agent/cp-nano-http-transaction-handler.dbg* | tail
# VERY IMPORTANT: go back to the default level (it generates a lot of logs)
cpnano --debug --default --service http-transaction-handler
```

## 6.4 Disable metrics

Remove the `prometheus` Advanced Setting from the profile (or set it to `false`) and do **Publish + Enforce**. This was not tested in the lab, but the nano-services will most likely restart again, as they do when you enable it: do this in a change window too.
