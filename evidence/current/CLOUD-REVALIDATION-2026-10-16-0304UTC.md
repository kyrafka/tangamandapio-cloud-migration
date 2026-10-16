# Revalidación de login público y permisos — 16/10/2026, 03:04 UTC

## Login real por el FQDN HTTPS

Se usó el FQDN público `https://tangamandapio.kendellnm.me` desde la máquina
local, con TLS verificado, cookies de sesión y token CSRF obtenido desde la
misma aplicación. Las credenciales se leyeron en memoria desde AWS Parameter
Store y no se imprimieron ni guardaron en archivos del proyecto.

- Administrador: login y logout aprobados; sesión con rol `admin`, acceso
  `erp_admin` y consulta de suscripciones de alarma HTTP 200 (dos suscripciones,
  sin revelar sus direcciones).
- Comercial: login y logout aprobados; ventas HTTP 200; outbox, inventario y
  usuarios admin HTTP 403.
- Operaciones: login y logout aprobados; ventas HTTP 403; outbox e inventario
  HTTP 200; usuarios admin HTTP 403.
- Se verificó CSRF en cada login/logout. No se crearon pedidos, pagos ni
  cambios del ledger; únicamente se generaron eventos normales de auditoría de
  autenticación.
- Una solicitud aislada con usuario sintético inexistente devolvió el 401
  esperado a través del FQDN, confirmando que el endpoint llega a la API.

## Diagnóstico del 403 de la automatización AWS

El smoke `admin-readonly` ejecutado desde EC2 vía Systems Manager hacia el
mismo FQDN recibió 403 durante el POST de login. El comando SSM terminó y se
inspeccionó antes de cualquier posible repetición. Una consulta posterior al
log de aplicación encontró los logins locales por el FQDN (incluidos los tres
roles), pero ninguna petición `/api/auth/login` del intento SSM ni rechazo
CSRF en esa ventana. Esto sitúa el bloqueo antes de Flask; es específico de la
ruta de automatización/egress y **no** demuestra que el login general por el
dominio falle. No se tiene acceso a los eventos de Cloudflare para atribuirlo a
una regla concreta y no se cambió su configuración.

El control visual de Chrome sigue sin verificarse: Computer Use no pudo
determinar la URL activa y se detuvo, sin navegar ni leer otras pestañas.

## Estado y siguientes brechas

La salud pública HTTPS y el estado AWS/Azure siguen en la
[revalidación 02:55 UTC](CLOUD-REVALIDATION-2026-10-16-0255UTC.md). Persisten:
red privada bloqueada por SCP AWS Academy y ausencia de VNet Azure; prueba de
carga insuficiente para 3,000 usuarios; WAF no desplegado; RDS Single-AZ con
retención de un día; causa del 503 histórico no atribuida; prueba WebRTC de dos
navegadores y recorrido visual de CSV pendientes; y evidencia visual reciente
de consolas/monitor. El buzón es interno al portal, no SMTP externo, y el WMS
mantiene un ledger sintético.
