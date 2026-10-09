# Portal B2B de Tangamandapio

Aplicación propia React/Vite y Flask para demostrar pedidos, salud, persistencia y el contrato AWS-Azure. La versión actual incorpora un portal B2B con control de acceso por rol; no es una tienda pública ni un proyecto open source reutilizado.

## Acceso y roles

La API aplica los permisos en el servidor; ocultar una opción en React no concede acceso. Las funciones son:

- `customer`: crea y ve únicamente los pedidos de su empresa.
- `sales`: registra pedidos comerciales.
- `warehouse`: consulta pedidos y estado del WMS.
- `operations`: ve outbox, estado Azure y solicita reintentos.
- `admin`: administra usuarios, roles, auditoría y operaciones.
- `auditor`: solo lectura de trazabilidad y estado operativo.

El primer administrador no está codificado. Para un arranque local se define una contraseña temporal en la sesión de PowerShell, nunca en Git:

```powershell
$env:BOOTSTRAP_ADMIN_USERNAME='admin@tangamandapio.local'
$env:BOOTSTRAP_ADMIN_PASSWORD='Cambiar-Esta-Clave-Local-2026'
$env:APP_SESSION_SECRET='secreto-local-distinto-y-largo'
python src/app.py
```

En AWS, esos valores se deben cargar desde Secrets Manager y `SESSION_COOKIE_SECURE` se activa cuando el ALB use HTTPS con certificado y dominio. Mientras el laboratorio siga con HTTP temporal, no se debe usar con credenciales reales.

## Interfaz web

La interfaz se encuentra en `web/`. Permite registrar pedidos, consultar pedidos recientes y visualizar el estado de la API y la base de datos. Durante el desarrollo, Vite usa un proxy local hacia Flask para no exponer CORS. Para generar el frontend que Flask servirá en el mismo origen:

```powershell
cd web
pnpm install
pnpm build
```

El build de publicación genera `src/static/`. La puerta de calidad usa
`pnpm run build:check`, que crea un artefacto aislado en `web/dist/` para no
reemplazar los archivos servidos por Flask mientras solo se valida el código.
Después de iniciar Flask, `http://localhost:8080/` sirve el portal y
`http://localhost:8080/api` mantiene la descripción JSON de la API.

## Servicios y endpoints

Servicio principal (`aws-app`):

- `GET /`: identidad de la instancia.
- `GET /health`: salud del servicio y la base de datos.
- `GET /ready`: disponibilidad de la base de datos y dependencias necesarias.
- `GET /api/orders`: lista de pedidos.
- `POST /api/orders`: confirma pedido y evento en la misma transacción; después intenta entregarlo al WMS.
- `GET /api/outbox`: trazabilidad de eventos pendientes, entregados o fallidos.
- `GET /metrics`: métricas Prometheus del núcleo de pedidos y de la integración.
- `GET /api/multicloud`: consulta la salud del receptor Azure.
- `POST /api/multicloud/sync`: envía un evento al receptor Azure.
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`: acceso al portal.
- `GET /api/dashboard`: indicadores filtrados por rol.
- `GET`/`POST /api/admin/companies`: alta y consulta de empresas B2B (tenants), exclusivo de `admin`.
- `GET`/`POST /api/admin/users`: administración de cuentas, exclusivo de `admin`.
- `GET /api/audit`: trazabilidad, solo lectura para auditoría y operaciones autorizadas.
- `POST /api/outbox/<event_id>/retry`: reintento auditado, exclusivo de operaciones/admin.

Servicio secundario (`azure-service`), simulación local del contrato de Azure Function:

- `GET /health`: salud del servicio autenticado.
- `GET /ready`: readiness autenticado del receptor.
- `POST /api/fulfillment/events`: recibe eventos autenticados e idempotentes.
- `GET /api/events`: enumera eventos recibidos durante la ejecución.

## Pruebas locales

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Simulación con contenedores y operaciones

```powershell
$env:DEMO_FUNCTION_KEY='reemplace-para-su-prueba-local'
docker compose up --build
```

Prueba de persistencia:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/orders -ContentType application/json -Body '{"customer":"Cliente Demo","total":49.90}'
Invoke-RestMethod -Uri http://localhost:8080/api/orders
Invoke-RestMethod -Uri http://localhost:8080/api/outbox
```

El perfil `ops` activa el plano de observabilidad local: Prometheus, Grafana y Portainer. Todos los puertos se enlazan exclusivamente a `127.0.0.1`; no son servicios públicos ni sustituyen a CloudWatch/Azure Monitor.

```powershell
$env:GRAFANA_ADMIN_PASSWORD='una-clave-local-temporal'
docker compose --profile ops up --build -d

# Portal: http://localhost:8080
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (usuario opsadmin)
# Portainer: https://localhost:9443 (crear usuario inicial local)
```

Para cerrar por completo los contenedores y sus datos temporales:

```powershell
docker compose --profile ops down --volumes
```

### Alcance de observabilidad

- **CloudWatch y Azure Monitor** son la observabilidad administrada de las nubes; las alertas cloud se mantienen en IaC.
- **Prometheus/Grafana** permiten demostrar métricas de aplicación y alarmas de disponibilidad en laboratorio o en un host de operaciones privado.
- **Portainer** sólo está habilitado bajo el perfil `ops`, por loopback y con HTTPS. No se despliega como parte de la carga pública.
- No se incorpora Zabbix para evitar duplicar almacenamiento, agentes y base de datos en un laboratorio educativo. Si la organización ya tuviera Zabbix, se puede integrar como fuente adicional de Grafana sin alterar la aplicación.

Prueba multicloud simulada:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/multicloud
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/multicloud/sync -ContentType application/json -Body '{"event_id":"evt-20260925-0001","event_type":"order.created","order_id":101}'
```

## Diferencia entre versión local y versión cloud

La versión local usa SQLite para probar sin infraestructura. La versión AWS desplegada utilizó PostgreSQL/RDS mediante el código incluido en CloudFormation. SQLite no representa la base de datos final.

Actualmente existen dos empaquetados de la aplicación: `app/src` con el build Vite para desarrollo local y un portal estático ligero embebido en `iac/cloudformation/aws-lab.yaml` para el laboratorio. Este último sí permite demostrar el flujo web/API/RDS, pero no equivale a publicar el build Vite versionado. Unificarlos en una imagen versionada es una mejora pendiente para evitar deriva entre ambientes.

La clave predeterminada de Docker Compose es exclusivamente local. Para cualquier demostración compartida debe definirse `DEMO_FUNCTION_KEY` y no publicarse el puerto del receptor fuera del equipo de prueba.
