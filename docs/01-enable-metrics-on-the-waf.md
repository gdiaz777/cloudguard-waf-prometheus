# 1. Enable metrics on the WAF

Enabling metrics is a **profile** setting, not an asset setting. It applies to every agent in that profile.

## 1.1 Requirements

| Requirement | Docker | VMware |
| --- | --- | --- |
| Agent connected to Infinity Portal | `cloudguard-appsec-standalone` container registered with the profile token | *CloudGuard WAF Gateway* VM (OVF template) registered with the profile token |
| Profile type | Docker | WAF Gateway |
| Infinity Portal permissions | Edit profiles, Publish and Enforce | Same |
| Access to verify | Shell on the Docker host | SSH to the VM as `admin` |

To check that the agent is registered before you start:

```bash
# Docker
docker exec <waf-container> cpnano -s
# VMware (on the VM)
cpnano -s
```

Look for `Registration status: Succeeded` and a value in `Policy version`.

## 1.2 Add the Advanced Setting

1. Infinity Portal → **WAF** → **Policy** menu → **Profiles**.
2. Click the profile:
   - **Docker:** the *Docker* profile (*Type* column: "Check Point WAF").
   - **VMware:** the *WAF Gateway* profile assigned to the VMs.
3. Open the **Advanced** tab.
4. In the **Advanced Settings** table, click **+** (top right of the table).
5. Fill in:

   | key | value |
   | --- | --- |
   | `prometheus` | `true` |

6. In the top bar, click **Publish**, then **Enforce**.

## 1.3 What happens on the agent

- The setting is delivered as agent **settings**, not as policy. The policy version may stay the same: in the lab it did not change, and the setting was applied in under 2 minutes.
- The orchestrator **restarts** and relaunches every nano-service, including the one that inspects traffic. With *Allow traffic upon internal failures* enabled in the profile, traffic keeps flowing **without inspection** for a few seconds.
- A new service, `cp-nano-prometheus`, appears and listens on `:::7465` (all interfaces).

> ⚠️ **Production:** apply the change during a maintenance window.

## 1.4 Verify

### Docker

```bash
# The service listens on 7465 inside the container
docker exec <waf-container> sh -c 'netstat -ltnp | grep 7465'
# tcp  0  0 :::7465  :::*  LISTEN  36950/cp-nano-prome

# And it responds (from the host, if the port is published)
curl -s http://localhost:7465/metrics | head
```

If the container does not publish 7465, add it and recreate the container. The registration is kept as long as `/etc/cp/conf` is on a persistent volume:

```bash
docker run -d --name=agent-container \
  -p 80:80 -p 443:443 -p 7465:7465 \
  -v <path>/conf:/etc/cp/conf -v <path>/data:/etc/cp/data -v <path>/logs:/var/log/nano_agent \
  -v <path>/nginx-conf.d:/etc/nginx/conf.d \
  -it checkpoint/cloudguard-appsec-standalone /cloudguard-appsec-standalone --token <token> [--nginx-self-managed]
```

### VMware

```bash
# SSH to the VM
ssh admin@<VM-IP>

netstat -ltnp | grep 7465
curl -s http://localhost:7465/metrics | head
```

Then, **from the Prometheus server**:

```bash
curl -s http://<VM-IP>:7465/metrics | head
```

| Result | Meaning | Action |
| --- | --- | --- |
| Works on the VM and from Prometheus | All good | Continue to step 2 |
| Works on the VM but not from Prometheus | Network block | Allow TCP 7465 (firewall, NSX, ACLs) from the Prometheus IP only |
| Does not work even on the VM | The setting has not arrived | Check that the right profile was edited and Enforce was done; wait 2 min; run `cpnano -s` |

> If the VM has several interfaces (external towards the Internet, internal towards the backend), scrape through the **internal or management** one. Port 7465 listens on all interfaces and must not be exposed to the Internet.

## 1.5 Endpoint security

- `GET /metrics` over plain HTTP, with **no authentication and no TLS**.
- Any other path returns an empty response.
- Restrict network access to the Prometheus IP.

Next: [02-prometheus.md](02-prometheus.md)
