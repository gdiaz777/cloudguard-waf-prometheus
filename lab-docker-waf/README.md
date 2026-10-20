# Laboratorio: WAF en Docker + Prometheus + Grafana

Demo completa en un solo equipo Linux:

- **WAF** CloudGuard en Docker (*single container*, NGINX autogestionado)
- **OWASP Juice Shop** como aplicación protegida
- **Prometheus + Grafana** desde [`../monitoring`](../monitoring)

> Solo para pruebas. En un despliegue VMware este directorio no se usa: el WAF es la VM y solo necesitas [`../monitoring`](../monitoring).

## Requisitos

- Linux con Docker y Docker Compose v2.
- Puertos libres: 80, 443, 7465 (WAF), 9090 (Prometheus) y 3000 (Grafana).
- Un tenant de Infinity Portal con WAF.

## Paso 1. Preparar el perfil y el asset en Infinity Portal

1. **Policy → Profiles → New Profile** → tipo **Docker**, subtipo *Single Container – Check Point WAF (with Reverse Proxy)*.
2. Marca **"I want to manage NGINX myself not via this management"**: este laboratorio trae su propia configuración de NGINX.
3. En **Authentication**, copia el **Token**.
4. En **Advanced → Advanced Settings** añade `prometheus` = `true`.
5. **Assets → New → Web Application**:
   - URL: `https://docker.example.com` (o el nombre que vayas a usar).
   - Profiles: el perfil Docker del punto 1.
   - Modo de la práctica Web: el que quieras. Con *Learn/Detect* los ataques pasan pero se registran.
6. **Publish** y **Enforce**.

## Paso 2. Configurar el laboratorio

```bash
cd lab-docker-waf
cp .env.example .env            # pega el token en APPSEC_TOKEN
chmod 600 .env
```

Si usas un host distinto de `docker.example.com`, cámbialo en `nginx/conf.d/waf.conf` (`server_name`). Debe coincidir **exactamente** con la URL del asset.

Genera el certificado:

```bash
./scripts/gen-cert.sh docker.example.com
```

Haz que el nombre resuelva al equipo:

```bash
echo "127.0.0.1 docker.example.com" | sudo tee -a /etc/hosts
```

## Paso 3. Arrancar el WAF

```bash
docker compose up -d
```

Comprueba el registro (puede tardar 1–2 min):

```bash
docker exec appsec-agent cpnano -s | grep -E "Registration status|Policy version"
# Registration status: Succeeded
# Policy version: <n>
```

El agente aparece en Infinity Portal → **Agents**.

Comprueba el tráfico:

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://docker.example.com/    # 200
```

## Paso 4. Comprobar las métricas del WAF

```bash
docker exec appsec-agent sh -c 'netstat -ltnp | grep 7465'
curl -s http://localhost:7465/metrics | head
```

Si no escucha, revisa que el perfil tiene `prometheus=true` y que se hizo Enforce.

## Paso 5. Arrancar la monitorización

```bash
cd ../monitoring
cp .env.example .env
docker compose up -d
```

`prometheus/targets/waf-agents.yml` ya apunta a `host.docker.internal:7465` (el 7465 publicado por el WAF en este host), así que no hay que tocar nada.

- Prometheus: http://localhost:9090/targets → `openappsec` **UP**
- Grafana: http://localhost:3000 → *CloudGuard WAF - Prometheus*

## Paso 6. Generar tráfico y ataques

Peticiones sueltas:

```bash
U=https://docker.example.com
curl -sk "$U/rest/products/search?q=%27%20or%201%3D1--"      # SQLi
curl -sk "$U/?q=%3Cscript%3Ealert(1)%3C/script%3E"          # XSS
curl -sk "$U/?file=../../../../etc/passwd"                  # path traversal
```

Tráfico continuo (legítimo + ataques) para ver las gráficas moverse:

```bash
./scripts/traffic.sh https://docker.example.com     # Ctrl+C para parar
```

En 1–2 minutos verás el panel *Coincidencias del motor IPS por minuto* subir en Grafana, y los eventos en Infinity Portal → **Monitor → Events**.

## Acceso desde tu PC si el laboratorio está en un servidor remoto

**VS Code Remote-SSH:** panel **Ports** → *Forward a Port* → `3000`, `9090` y `443`. Para que el WAF reconozca el asset, en tu PC añade `127.0.0.1 docker.example.com` al fichero hosts y reenvía el 443 al 443 local.

## Parar y limpiar

```bash
cd monitoring && docker compose down          # -v para borrar también los datos
cd ../lab-docker-waf && docker compose down
```

`agent/` guarda el registro del agente: si lo borras, al volver a arrancar se registra como un agente nuevo.

## Notas

- En modo `--nginx-self-managed` el health check del puerto 8117 no escucha, por eso no se publica.
- Cada vez que cambias los puertos del compose se recrea el contenedor. El registro se conserva en `agent/conf`, pero las métricas tardan ~1 min en volver.
- El token aparece en la línea de comandos del proceso dentro del contenedor (`ps`). Trátalo como un secreto.
