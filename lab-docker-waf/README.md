# Lab: WAF in Docker + Prometheus + Grafana

Full demo on a single Linux machine:

- **CloudGuard WAF** in Docker (*single container*, self-managed NGINX)
- **OWASP Juice Shop** as the protected application
- **Prometheus + Grafana** from [`../monitoring`](../monitoring)

> Testing only. In a VMware deployment this directory is not used: the WAF is the VM, and you only need [`../monitoring`](../monitoring).

## Requirements

- Linux with Docker and Docker Compose v2.
- Free ports: 80, 443, 7465 (WAF), 9090 (Prometheus) and 3000 (Grafana).
- An Infinity Portal tenant with WAF.

## Step 1. Prepare the profile and the asset in Infinity Portal

1. **Policy → Profiles → New Profile** → type **Docker**, sub type *Single Container – Check Point WAF (with Reverse Proxy)*.
2. Tick **"I want to manage NGINX myself not via this management"**: this lab ships its own NGINX configuration.
3. Under **Authentication**, copy the **Token**.
4. Under **Advanced → Advanced Settings**, add `prometheus` = `true`.
5. **Assets → New → Web Application**:
   - URL: `https://docker.example.com` (or the name you will use).
   - Profiles: the Docker profile from step 1.
   - Web practice mode: whatever you like. With *Learn/Detect*, attacks go through but are logged.
6. **Publish** and **Enforce**.

## Step 2. Configure the lab

```bash
cd lab-docker-waf
cp .env.example .env            # paste the token into APPSEC_TOKEN
chmod 600 .env
```

If you use a host other than `docker.example.com`, change it in `nginx/conf.d/waf.conf` (`server_name`). It must match the asset URL **exactly**.

Generate the certificate:

```bash
./scripts/gen-cert.sh docker.example.com
```

Make the name resolve to this machine:

```bash
echo "127.0.0.1 docker.example.com" | sudo tee -a /etc/hosts
```

## Step 3. Start the WAF

```bash
docker compose up -d
```

Check the registration (it may take 1–2 min):

```bash
docker exec appsec-agent cpnano -s | grep -E "Registration status|Policy version"
# Registration status: Succeeded
# Policy version: <n>
```

The agent appears in Infinity Portal → **Agents**.

Check the traffic:

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://docker.example.com/    # 200
```

## Step 4. Check the WAF metrics

```bash
docker exec appsec-agent sh -c 'netstat -ltnp | grep 7465'
curl -s http://localhost:7465/metrics | head
```

If nothing is listening, check that the profile has `prometheus=true` and that Enforce was done.

## Step 5. Start monitoring

```bash
cd ../monitoring
cp .env.example .env
docker compose up -d
```

`prometheus/targets/waf-agents.yml` already points to `host.docker.internal:7465` (port 7465 published by the WAF on this host), so nothing needs to change.

- Prometheus: http://localhost:9090/targets → `openappsec` **UP**
- Grafana: http://localhost:3000 → *CloudGuard WAF - Prometheus*

## Step 6. Generate traffic and attacks

Single requests:

```bash
U=https://docker.example.com
curl -sk "$U/rest/products/search?q=%27%20or%201%3D1--"      # SQLi
curl -sk "$U/?q=%3Cscript%3Ealert(1)%3C/script%3E"          # XSS
curl -sk "$U/?file=../../../../etc/passwd"                  # path traversal
```

Continuous traffic (legitimate + attacks) to see the graphs move:

```bash
./scripts/traffic.sh https://docker.example.com     # Ctrl+C to stop
```

Within 1–2 minutes the *IPS engine matches per minute* panel rises in Grafana, and the events show up in Infinity Portal → **Monitor → Events**.

## Access from your PC when the lab runs on a remote server

**VS Code Remote-SSH:** **Ports** panel → *Forward a Port* → `3000`, `9090` and `443`. For the WAF to recognize the asset, add `127.0.0.1 docker.example.com` to the hosts file on your PC and forward port 443 to local port 443.

## Stop and clean up

```bash
cd monitoring && docker compose down          # add -v to also delete the data
cd ../lab-docker-waf && docker compose down
```

`agent/` holds the agent registration: if you delete it, the agent registers as a new agent the next time it starts.

## Notes

- In `--nginx-self-managed` mode the health check on port 8117 does not listen, which is why it is not published.
- Every time you change the compose ports, the container is recreated. The registration is kept in `agent/conf`, but metrics take about 1 min to come back.
- The token appears in the process command line inside the container (`ps`). Treat it as a secret.
