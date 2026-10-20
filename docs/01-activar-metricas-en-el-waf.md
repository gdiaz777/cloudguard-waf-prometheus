# 1. Activar las métricas en el WAF

La activación es un ajuste del **perfil**, no del asset: se aplica a todos los agentes de ese perfil.

## 1.1 Requisitos

| Requisito | Docker | VMware |
| --- | --- | --- |
| Agente conectado a Infinity Portal | Contenedor `cloudguard-appsec-standalone` registrado con el token del perfil | VM *CloudGuard WAF Gateway* (plantilla OVF) registrada con el token del perfil |
| Tipo de perfil | Docker | WAF Gateway |
| Permisos en Infinity Portal | Editar perfiles y hacer Publish + Enforce | Igual |
| Acceso para verificar | Shell en el host Docker | SSH a la VM con el usuario `admin` |

Para comprobar que el agente está registrado antes de empezar:

```bash
# Docker
docker exec <contenedor-waf> cpnano -s
# VMware (en la VM)
cpnano -s
```

Busca `Registration status: Succeeded` y un valor en `Policy version`.

## 1.2 Añadir la Advanced Setting

1. Infinity Portal → **WAF** → menú **Policy** → **Profiles**.
2. Haz clic en el perfil:
   - **Docker:** el perfil de tipo *Docker* (columna *Type*: "Check Point WAF").
   - **VMware:** el perfil de tipo *WAF Gateway* que tienen asignado las VMs.
3. Abre la pestaña **Advanced**.
4. En la tabla **Advanced Settings**, pulsa **+** (arriba a la derecha de la tabla).
5. Rellena:

   | key | value |
   | --- | --- |
   | `prometheus` | `true` |

6. En la barra superior pulsa **Publish** y después **Enforce**.

## 1.3 Qué pasa en el agente

- El ajuste llega como **settings** del agente, no como política. La versión de política puede no cambiar; en el laboratorio se quedó en la misma y el ajuste se aplicó en menos de 2 minutos.
- El orquestador se **reinicia** y relanza todos los nano-servicios, incluido el que inspecciona el tráfico. Con *Allow traffic upon internal failures* activado en el perfil, el tráfico sigue pasando **sin inspección** durante unos segundos.
- Aparece un servicio nuevo, `cp-nano-prometheus`, escuchando en `:::7465` (todas las interfaces).

> ⚠️ **Producción:** aplica el cambio en una ventana de mantenimiento.

## 1.4 Verificar

### Docker

```bash
# El servicio escucha en el 7465 dentro del contenedor
docker exec <contenedor-waf> sh -c 'netstat -ltnp | grep 7465'
# tcp  0  0 :::7465  :::*  LISTEN  36950/cp-nano-prome

# Y responde (desde el host, si el puerto está publicado)
curl -s http://localhost:7465/metrics | head
```

Si el contenedor no publica el 7465, añádelo y recrea el contenedor. El registro se conserva si `/etc/cp/conf` está en un volumen persistente:

```bash
docker run -d --name=agent-container \
  -p 80:80 -p 443:443 -p 7465:7465 \
  -v <ruta>/conf:/etc/cp/conf -v <ruta>/data:/etc/cp/data -v <ruta>/logs:/var/log/nano_agent \
  -v <ruta>/nginx-conf.d:/etc/nginx/conf.d \
  -it checkpoint/cloudguard-appsec-standalone /cloudguard-appsec-standalone --token <token> [--nginx-self-managed]
```

### VMware

```bash
# SSH a la VM
ssh admin@<IP-de-la-VM>

netstat -ltnp | grep 7465
curl -s http://localhost:7465/metrics | head
```

Después, **desde el servidor de Prometheus**:

```bash
curl -s http://<IP-de-la-VM>:7465/metrics | head
```

| Resultado | Significado | Acción |
| --- | --- | --- |
| Funciona en la VM y desde Prometheus | Todo correcto | Seguir al paso 2 |
| Funciona en la VM pero no desde Prometheus | Bloqueo de red | Abrir TCP 7465 (firewall, NSX, ACLs) solo desde la IP de Prometheus |
| No funciona ni en la VM | El ajuste no ha llegado | Revisar que se editó el perfil correcto y se hizo Enforce; esperar 2 min; `cpnano -s` |

> Si la VM tiene varias interfaces (externa hacia Internet, interna hacia el backend), haz el scrape por la **interna o de gestión**. El 7465 escucha en todas las interfaces y no debe quedar expuesto a Internet.

## 1.5 Seguridad del endpoint

- `GET /metrics` en HTTP plano, **sin autenticación ni TLS**.
- Cualquier otra ruta devuelve una respuesta vacía.
- Restringe el acceso por red a la IP de Prometheus.

Siguiente: [02-prometheus.md](02-prometheus.md)
