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

El inicio de sesión bloquea por defecto durante cinco minutos tras cinco fallos
consecutivos por combinación de IP y usuario. El contador se persiste en la
base de datos (SQLite local o PostgreSQL) para que sobreviva a reinicios y sea
compartido por los procesos; en la tabla solo se almacena una clave HMAC, no la
IP ni el usuario en texto legible. Durante el bloqueo la API responde `429`
con `Retry-After`, y un acceso correcto limpia los fallos previos. Se ajusta
con `LOGIN_RATE_LIMIT_MAX` y `LOGIN_RATE_LIMIT_SECONDS`; usar `0` desactiva el
límite solo para pruebas controladas. Esto reduce fuerza bruta, pero no
sustituye MFA, WAF ni una política corporativa de identidad.

Las escrituras del portal también requieren una cabecera `X-CSRF-Token` ligada
a la cookie de sesión; el token se obtiene en `/api/auth/session`, rota al
iniciar sesión y se borra al cerrar sesión. El servidor rechaza orígenes web
distintos cuando recibe `Origin` o `Referer`. `CSRF_ENABLED` está activo por
defecto y solo se desactiva explícitamente en pruebas unitarias que ejercitan
la lógica de negocio sin simular navegador. Esto no sustituye MFA ni valida
por sí solo el despliegue detrás de un proxy HTTPS.

### Ciclo de vida de contraseñas

El portal local fuerza el cambio de la contraseña de bootstrap y de toda clave
temporal antes de permitir otras operaciones (`428 password_change_required`).
Cada usuario puede cambiar su propia contraseña desde **Mi cuenta**; el backend
valida la clave actual, exige entre 12 y 256 caracteres, rechaza reutilizarla,
registra la acción y revoca las sesiones anteriores incrementando `auth_version`.
Un administrador puede iniciar un restablecimiento para otra cuenta activa,
confirmándolo en la interfaz. El backend genera una clave aleatoria temporal,
la devuelve una sola vez, marca el cambio como obligatorio y revoca sesiones;
la auditoría no registra el secreto. El administrador no puede usar el flujo
para restablecer su propia cuenta. Entrega la clave temporal al usuario por un
canal seguro y no la guardes en tickets o chats.

Las columnas `auth_version` y `must_change_password` se incorporan mediante una
migración aditiva compatible con las bases existentes. Los defaults
`FORCE_BOOTSTRAP_PASSWORD_CHANGE` y `FORCE_INITIAL_PASSWORD_CHANGE` están
activados por defecto; las pruebas pueden desactivarlos explícitamente. La
implementación y su prueba actual son locales; no acredita que el artefacto
desplegado en AWS tenga esta versión ni sustituye MFA o un proveedor corporativo
de identidad.

El primer administrador no está codificado. Para un arranque local se define una contraseña temporal en la sesión de PowerShell, nunca en Git:

```powershell
$env:BOOTSTRAP_ADMIN_USERNAME='admin@tangamandapio.local'
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$passwordBytes = New-Object byte[] 32
$sessionBytes = New-Object byte[] 48
$rng.GetBytes($passwordBytes)
$rng.GetBytes($sessionBytes)
$env:BOOTSTRAP_ADMIN_PASSWORD = [Convert]::ToBase64String($passwordBytes)
$env:APP_SESSION_SECRET = [Convert]::ToBase64String($sessionBytes)
python src/app.py
```

En AWS, esos valores se deben cargar desde Secrets Manager y `SESSION_COOKIE_SECURE` se activa cuando el ALB use HTTPS con certificado y dominio. Mientras el laboratorio siga con HTTP temporal, no se debe usar con credenciales reales.

## Interfaz web

La interfaz se encuentra en `web/`. Incluye el portal B2B y, para personal autorizado, el módulo ERP con ventas, compras, finanzas operativas, datos maestros y una bandeja de mensajería interna dentro de la navegación autenticada del portal. El ERP local se abre desde el menú; no usa una página independiente `/erp` como el release de producción AWS. Ambos usan la sesión del portal y permisos separados por rol. Durante el desarrollo, Vite usa un proxy local hacia Flask para no exponer CORS. Para generar el frontend que Flask servirá en el mismo origen:

La cuenta `admin` tiene además la vista completa `/administracion`, separada del
espacio operativo de cada rol. Desde allí gestiona usuarios (rol, empresa,
estado y restablecimiento de clave), empresas B2B, auditoría y destinatarios de
las alarmas SNS. Las rutas de la vista y de datos validan el rol en Flask; el
menú por sí solo no es un control de seguridad. Agregar una dirección envía una
confirmación SNS y no la activa hasta que el titular la acepta. Solo pueden
quitarse suscripciones de correo confirmadas del tema configurado. La auditoría
guarda un identificador hash, no la dirección ni secretos de AWS.

En local `ALARM_NOTIFICATION_TOPIC_ARN` queda vacío por defecto: la sección
indica que SNS no está configurado y no intenta contactar AWS. La prueba del
flujo usa un SNS falso. Para habilitar el servicio real se necesita un tema SNS,
permisos de rol para listar/suscribir y una cuenta autorizada para `Unsubscribe`;
las nuevas direcciones deben confirmar el correo. Esto no se debe probar desde
un entorno local que apunte accidentalmente a un tema productivo.

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
- `GET /metrics`: métricas Prometheus del núcleo de pedidos y de la integración; desactivado por defecto en el release cloud y habilitado explícitamente en Compose local, donde Prometheus lo consume por la red privada del proyecto.
- `GET /api/multicloud`: consulta la salud del receptor Azure.
- `POST /api/multicloud/sync`: envía un evento al receptor Azure.
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`: acceso al portal.
- `GET /api/dashboard`: indicadores filtrados por rol.
- `GET`/`POST /api/admin/companies`: alta y consulta de empresas B2B (tenants), exclusivo de `admin`.
- `GET`/`POST /api/admin/users`: administración de cuentas, exclusivo de `admin`.
- `PATCH /api/admin/users/<id>`: cambia rol, empresa o acceso y revoca sesiones previas, exclusivo de `admin`.
- `POST /api/admin/users/<id>/reset-password`: genera una clave temporal de entrega única, exclusivo de `admin`.
- `GET`/`POST`/`DELETE /api/admin/alarm-subscriptions`: gestión acotada a correos de un único tema SNS; protegido por sesión, rol y CSRF.
- `GET /administracion`: consola administrativa a pantalla completa; restringida a `admin`.
- `GET /api/audit`: trazabilidad, solo lectura para auditoría y operaciones autorizadas.
- `POST /api/outbox/<event_id>/retry`: reintento auditado, exclusivo de operaciones/admin.
- `GET /api/erp/access`: permisos ERP efectivos de la cuenta interna.
- `/api/erp/partners` y `/api/erp/products`: datos maestros; el saldo de productos se consulta en Azure WMS y no se copia a las tablas ERP.
- `POST /api/erp/products/import`: importa 1–500 productos desde la pestaña Maestros. Acepta catálogo en CSV UTF-8 preparado con la plantilla Excel; sincroniza WMS antes de guardar ERP. `initial_stock` solo crea saldo para un SKU nuevo; las actualizaciones conservan existencias.
- `/api/erp/sales/orders` y `/api/erp/purchases/orders`: órdenes con líneas SKU/cantidad y eventos idempotentes al WMS.
- `/api/erp/finance/*`: cuentas por cobrar/pagar operativas y gastos; no es contabilidad de partida doble ni facturación tributaria.
- `/api/erp/mail`: persiste mensajes privados entre cuentas internas; si se configura `ERP_SMTP_*`, envía además una copia por SMTP y conserva el resultado (`accepted_by_smtp`, `smtp_failed` o `portal_only`). Las direcciones se derivan de la cuenta interna y se limitan a `ERP_SMTP_RECIPIENT_DOMAIN`; el request no puede elegir destinatarios externos.
- `GET /api/erp/mail/status` informa si el transporte SMTP está configurado; `POST /api/erp/mail/smtp-test` permite al administrador enviar una prueba a su propia cuenta. La aceptación del relay no garantiza entrega final.
- `/api/erp/users/*`: asignación de roles ERP, exclusiva de administración.

`GET /api/erp/overview` filtra los agregados por permiso efectivo: cuentas de
Ventas no reciben saldos de Finanzas, y los indicadores de compras/ventas solo
se incluyen si la cuenta tiene lectura de ese módulo. La interfaz oculta las
tarjetas no autorizadas; la restricción principal se aplica en el servidor.

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
# Ejecutar desde la raíz del repositorio. Mantenga estas variables en la sesión,
# no en un archivo versionado.
$env:BOOTSTRAP_ADMIN_USERNAME='admin@tangamandapio.local'
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$passwordBytes = New-Object byte[] 32
$sessionBytes = New-Object byte[] 48
$functionKeyBytes = New-Object byte[] 32
$rng.GetBytes($passwordBytes)
$rng.GetBytes($sessionBytes)
$rng.GetBytes($functionKeyBytes)
$env:BOOTSTRAP_ADMIN_PASSWORD = [Convert]::ToBase64String($passwordBytes)
$env:APP_SESSION_SECRET = [Convert]::ToBase64String($sessionBytes)
$env:DEMO_FUNCTION_KEY = [Convert]::ToBase64String($functionKeyBytes)
docker compose -f app/compose.yaml up --build -d
```

Compose agrega Mailpit como receptor SMTP de laboratorio. Sus puertos SMTP
(`127.0.0.1:1025`) e interfaz (`http://localhost:8025`) quedan enlazados solo a
loopback; el contenedor también lo alcanza por la red Docker. Al enviar un
mensaje desde ERP, se guarda en la bandeja del portal y una copia de prueba
aparece en Mailpit. El botón **Probar SMTP** envía una prueba a la cuenta del
administrador. Mailpit no es servidor productivo, no crea buzones de empleados
y no entrega correo a Internet.

Para apuntar a un relay real, configura `ERP_SMTP_HOST`, `ERP_SMTP_PORT`,
`ERP_SMTP_SECURITY` (`starttls` o `ssl`), `ERP_SMTP_FROM`,
`ERP_SMTP_RECIPIENT_DOMAIN` y, si aplica, credenciales. Usa secretos del
entorno/Secrets Manager para usuario y contraseña, nunca `.env` versionado.
Cada cuenta interna debe tener el mismo identificador local antes de `@` que
su buzón en el dominio permitido. SES y otros proveedores públicos requieren
una identidad de dominio verificada y destinatarios reales; las cuentas
`*.local` actuales solo son válidas para el sink de laboratorio.

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
