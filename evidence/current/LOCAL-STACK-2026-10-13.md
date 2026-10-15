# Verificación del portal local — 13/10/2026

## Resultado — 03:13 America/Chicago

Se levantó el stack con `docker compose -f app/compose.yaml up --build -d`.
Docker Desktop Engine 28.5.1 respondió. Los tres servicios quedaron saludables:
`app-aws-app-1`, `app-azure-service-1` y `app-mailpit-1`.

Comprobaciones de solo lectura posteriores al inicio:

- `/health`: servicio `ok`, base SQLite `ok`.
- Login local `admin@tangamandapio.local`: autenticado con rol `admin`; también
  se comprobó la sesión autenticada. No se creó ni modificó ningún pedido.
- `/api/multicloud`: `connected` con el servicio WMS **local de demostración**.
- `/api/erp/access`: rol `erp_admin`.
- `/api/erp/products`: tres productos y WMS `demo-inventory-ledger`.
- Mailpit local: interfaz HTTP 200. Es un sink SMTP de laboratorio, no entrega
  correo a Internet ni representa buzones productivos.

La contraseña de bootstrap y la clave de sesión se generaron aleatoriamente al
arrancar; no se escribieron en Git ni en un archivo del proyecto. Como Compose
las mantiene en la configuración del contenedor local para esta instancia,
rotarlas si otra persona obtiene acceso al equipo. El usuario recibe el acceso
local en el chat; no copiarlo a esta evidencia.

Durante el primer arranque se encontró que `/data` no era escribible por el
usuario no privilegiado del contenedor. Se corrigieron ambos Dockerfiles para
crear el directorio con propietario `appuser`; tras reconstruir, Azure local,
portal y Mailpit quedaron sanos.

## Alcance

Este corte prueba el perfil local y sus servicios simulados. No implica que el
ALB AWS esté sano ni que el ledger local sea un WMS empresarial, que Mailpit
sea un correo corporativo de Internet o que exista conectividad privada
AWS–Azure. El estado cloud más reciente está en
[la revalidación general](REVALIDACION_ESTADO_2026-10-13.md).

## Actualización — 03:39 America/Chicago

Se corrigió el ciclo de auditoría de la administración local y del artefacto
AWS: altas de empresas/usuarios, cambios de rol/empresa/estado y reseteos de
contraseña ahora escriben el evento de auditoría dentro de la misma transacción
de base de datos. Si la auditoría falla, la mutación se revierte. Se añadieron
dos pruebas de rollback locales (usuario y empresa) y tres de regresión en el
conjunto ERP del artefacto release (alta, cambio de usuario y reset de clave).

El stack se reconstruyó preservando el volumen `app_aws-data`; la base y el
estado de bootstrap no se recrearon. `aws-app`, `azure-service` y `mailpit`
quedaron saludables. `/` devolvió HTTP 200, `/health` dio `ok` con base `ok` y
una llamada anónima a `/api/admin/users` devolvió 401.

La compuerta completa pasó: **81 pruebas** (30 portal, 21 Azure Functions, 30
release AWS), auditoría Python/frontend sin vulnerabilidades conocidas,
frontend build, lint CloudFormation, formato/validación de los cuatro entornos
Terraform y 2/2 pruebas mock de la compuerta VPN. No hubo `terraform apply` ni
operaciones de nube. Estos resultados validan el código y los mocks; no
demuestran que los cambios estén publicados en AWS. Además, el test suite
enfocado ERP del artefacto AWS pasó 7/7; no forma parte del conteo 81 del runner.

## Revalidación HTTP — 05:34 America/Chicago

El portal local respondió HTTP 200 en `/` y `/health`; la respuesta de salud
marcó servicio y base de datos como `ok`. `/api/health` devuelve 404 porque el
portal local publica su health check en `/health` (el endpoint Azure sí usa
`/api/health`). Esta consulta fue de solo lectura y no implica una prueba de
login ni estado de los recursos cloud.
