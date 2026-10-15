# Release AWS v5 — 14/10/2026, 00:24 America/Chicago

> **Registro de cortes anteriores a v11.** Los resultados sanos y las pruebas
> E2E de este archivo preceden al intento v11. No representan la salud actual
> del portal; para el estado más reciente consulta
> [AWS-DESPLIEGUE-V11](AWS-DESPLIEGUE-V11-2026-10-14.md).

## E2E autenticado posterior — 14/10/2026, 14:56–14:58 America/Chicago

El smoke desplegado se ejecutó en una EC2 activa por SSM, con guardas de
inventario `demo-inventory-ledger` y opt-in explícito. Admin inició sesión y
completó el flujo ERP; Comercial y Operaciones pasaron sus rutas 200/403. La
importación del SKU sintético pasó, la venta quedó `completed_demo`, la compra
`received_demo`, ambos eventos outbox `delivered` y el stock demo regresó de
10 a 10. Veinticuatro lecturas autenticadas dieron 200 (concurrencia 6, p95
1,360.41 ms) desde loopback en EC2, no por ALB. El smoke dejó pedidos/registros
de QA en RDS y eventos sintéticos en Azure; no cambió infraestructura ni
inventario físico. Datos sanitizados:
[`AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json`](AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json).

## Paridad revalidada — 14/10/2026, 14:30–14:44 America/Chicago

Tras actualizar localmente el perfil `default` con el token temporal entregado,
AWS STS autenticó. CloudFormation está `UPDATE_COMPLETE` y la última detección
de drift informó `IN_SYNC`. El ALB está activo con dos destinos sanos; el ASG
tiene mínimo/deseado 2, máximo 4 y dos instancias `InService`. La portada,
`/health` y `/ready` respondieron 200; la API administrativa anónima respondió
401. RDS sigue disponible, privada y cifrada, Single-AZ con retención de un día.

SSM ejecutó únicamente `cat BUILD_REVISION`, `sha256sum` y
`systemctl is-active` en ambas EC2. Las dos reportaron v10, servicio activo y
los mismos hashes que el árbol local:

| Archivo | SHA-256 |
|---|---|
| `app.py` | `f8b0d1b9a733581936a21320a5e81a36a9c0132000b2010f131adb0e72aa1ee5` |
| `erp_service.py` | `8b07c5528a30ff4738d08c442d0936e0ea70f81ff2f0da6727f13231583d7b1a` |
| `requirements.lock` | `b93d99918791772134a7fa1da366ee0d1859f39e9cd4f535406d6573ea018a9b` |

No se publicaron artefactos ni se cambió infraestructura durante esta
revalidación.

## Revalidación de paridad del release — 01:40 America/Chicago

AWS SSM ejecutó una lectura `sha256sum` en las dos EC2 InService. Ambas
reportaron la revisión `20261014-erp-admin-security-v5-python312` y hashes
idénticos al árbol local actual:

| Archivo | SHA-256 local y en ambas EC2 |
|---|---|
| `app.py` | `66f78ddfbccc6ff446c217e3c9d576d68b5865d80b759784c716a2c5cf596daf` |
| `erp_service.py` | `e6186b58e6633fe47d8f5c9b96ae17bb98d4f00a334a2c9c6ba3160a86133c95` |
| `requirements.lock` | `b93d99918791772134a7fa1da366ee0d1859f39e9cd4f535406d6573ea018a9b` |

Esto verifica los tres archivos principales del runtime, no cada archivo del
paquete ni el estado visual en navegador. La operación remota fue solo lectura;
no se reiniciaron instancias ni se modificó infraestructura.

## Artefacto y despliegue

La compuerta local `tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 120 pruebas unitarias (46 API, 23 Function Azure, 41
release AWS y 10 guards/smoke), auditoría de dependencias, build Vite,
CloudFormation y Terraform validate/fmt. El paquete AWS se publicó antes de
actualizar instancias, en el bucket privado con versionado y SSE-S3 AES256:

- Revisión: `20261014-erp-admin-security-v5-python312`.
- SHA-256: `19d1c9ae9225316a5802932ab89f2781480ae9eeedf4945ee5e2308ae0273bad`.
- Tamaño: 18,180,457 bytes; versión S3 `aly3yJeiQYfu1g_PhscbnFQFaj0mMXwk`.
- Change set: `tangamandapio-v5-20261014-erp-admin-security`; seis recursos
  modificados para Launch Template, Auto Scaling y observabilidad. No propuso
  modificar RDS, buckets ni eliminar recursos.

CloudFormation completó `UPDATE_COMPLETE`. Ambas instancias nuevas confirmaron
por SSM la revisión, los hashes de `app.py`, `erp_service.py` y
`requirements.lock` iguales al árbol probado, y el servicio `tangamandapio`
activo. La detección posterior terminó `IN_SYNC`. El ASG regresó a capacidad
deseada/mínima 2, con dos destinos saludables en zonas distintas.

## Comprobaciones posteriores

| Comprobación | Resultado |
|---|---|
| ALB `/health` y `/ready` | HTTP 200; PostgreSQL `ok`. |
| `/administracion` sin sesión | HTTP 303 al inicio de sesión. |
| `/api/admin/users` y `/api/admin/alarm-subscriptions` anónimos | HTTP 401. |
| RDS | `available`, cifrada, privada, Single-AZ y backups automáticos de 1 día; no se modificó. |
| Tema SNS de alarmas | Dos suscripciones de correo confirmadas. |
| Azure Function `tangama-wms-261008` | `Running`, HTTPS-only; `/api/health` devolvió HTTP 200. |

La consulta ARM del setting `DEPLOYMENT_PACKAGE_SHA256` excedió el tiempo de
espera y se canceló; por tanto, esta revalidación no vuelve a certificar el hash
live de Azure. El corte Azure del 13/10 registra el ZIP inmutable
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065` y un plan
sin cambios.

## Lo que no queda afirmado

El ALB continúa en HTTP mientras falta el dominio/certificado. No hay túnel
privado AWS–Azure: la SCP de AWS Academy denegó `CreateCustomerGateway` en la
prueba temporal y sus recursos Azure se limpiaron. El ledger Azure sigue siendo
de demostración, no inventario de un WMS comercial. El portal ofrece correo
interno; no hay relay SMTP externo configurado. Esta pasada comprobó las
barreras anónimas administrativas, no una sesión de cada rol ni una llamada
WebRTC entre dos navegadores.

## Preparación final de HTTPS — 14/10/2026, 00:33 America/Chicago

Se preparó la plantilla local para aceptar `PortalDomainName` junto con
`CertificateArn`. El despliegue ahora exige un certificado ACM `ISSUED` en la
región del ALB y comprueba su SAN antes de crear el listener; el output HTTPS
usará el dominio propio y el listener HTTP redirigirá a HTTPS. CloudFormation
lint y la compuerta local completa volvieron a pasar. Las guardas bloquearon
sin cambios un dominio sin ARN y un ARN de otra región. Esta preparación local
no cambia el stack vivo: sigue solo HTTP hasta que exista dominio y certificado.

## Revalidación pública de salud — 14/10/2026, 00:45 America/Chicago

Lecturas HTTP/HTTPS anónimas de solo lectura: el ALB devolvió HTTP 200 en
`/health` y reportó PostgreSQL `ok`; la Azure Function devolvió HTTP 200 en
`/api/health`. Esto confirma disponibilidad de esos endpoints en ese momento,
no reemplaza STS/ARM/CloudFormation autenticados ni prueba VPN, inventario real
o sesión de usuario.

## Release v9 actualizado y verificado — 14/10/2026, 08:42–08:52 America/Chicago

Se publicó el artefacto `20261014-public-diagnostics-hardening-v9-python312`
en S3 privado con SSE-S3. Su SHA-256 es
`78327e426cf86368cbc3a455be6241b57148bf8c43de6fe14f4e33041ea15316`, tamaño
18,179,184 bytes y versión S3 `pPRBh3fjqxbyMcoviF0yhI_LGaSkR71J`. El change set
`tangamandapio-v9-review-20261014` actualizó seis recursos de Launch Template,
Auto Scaling y observabilidad: cero cambios a RDS, cero eliminaciones y cero
reemplazos de base de datos. CloudFormation terminó `UPDATE_COMPLETE` a las
08:49:38; la detección posterior terminó `IN_SYNC` a las 08:51:34.

El ASG volvió a 2/2 instancias `InService` y `Healthy`, y el target group quedó
2/2 `healthy`. SSM verificó en ambas la misma revisión v9, `app.py` SHA-256
`f8b0d1b9a733581936a21320a5e81a36a9c0132000b2010f131adb0e72aa1ee5`,
`erp_service.py` `e6186b58e6633fe47d8f5c9b96ae17bb98d4f00a334a2c9c6ba3160a86133c95`
y `requirements.lock` `b93d99918791772134a7fa1da366ee0d1859f39e9cd4f535406d6573ea018a9b`;
el servicio estaba activo y su health local devolvió 200.

Pruebas anónimas a través del ALB: `/` 200, `/health` 200 con solo `status` y
`timestamp`, `/ready` 200 con solo `status`, `/api` 200 sin host de instancia,
`/metrics` 404 y `/api/admin/users` 401. RDS quedó `available`, cifrada, privada,
Single-AZ y con un día de retención; no se cambió.

La Function Azure también se actualizó al paquete local
`ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27`; ver
[E2E Azure](../azure/AZURE-ERP-E2E-2026-10-14.md). El smoke posterior desde EC2
envió un evento sintético sin artículos, aceptado con 202 y procesado como
`awaiting_items`; el inventario demo se mantuvo 24→24. La venta autenticada
completa del portal desde EC2 sigue pendiente: el login admin acepta la
contraseña de bootstrap, pero `GET /api/wms/inventory` devuelve HTTP 428 hasta
que se complete su cambio obligatorio. No se creó pedido, socio ni reposición
en RDS durante la prueba. El ALB sigue HTTP, sin dominio ni certificado ACM.

## Acceso administrativo, roles y E2E ERP — 14/10/2026, 10:11 America/Chicago

Se completó el cambio obligatorio de contraseña que causaba HTTP 428. Para no
dejar la credencial final viajando por el ALB público HTTP, se volvió a rotar
por un túnel temporal de AWS Systems Manager desde una EC2 hacia el ALB. La
clave vigente se conserva como `SecureString` Standard en
`/tangamandapio/portal/admin-login`; el valor no está en el repositorio ni en
esta evidencia. La autenticación posterior confirmó rol `admin`, sin cambio
forzado pendiente, y acceso HTTP 200 a `/api/admin/users`.

Se crearon dos cuentas internas de prueba y sus claves se conservaron como
`SecureString` Standard, separadas del secreto de bootstrap:
`comercial.demo@tangamandapio.local` en
`/tangamandapio/portal/users/comercial-demo` y
`operaciones.demo@tangamandapio.local` en
`/tangamandapio/portal/users/operaciones-demo`. Pruebas autenticadas por API:
Comercial obtuvo dashboard y ventas ERP 200, y recibió 403 en outbox, WMS y
administración; Operaciones obtuvo dashboard, outbox y WMS 200, y 403 en ERP
ventas y administración. Las rutas de consola devolvieron `/platform` 200 para
admin/Operaciones y 403 para Comercial; `/administracion` devolvió 200 solo
para admin y 403 para ambos roles. Esto verifica autorización de servidor; no
es una prueba visual del navegador.

Desde el portal desplegado, usando admin y una sesión SSM protegida, se registró
el socio `QA E2E AWS Azure 2026-10-14` y una venta de una unidad de
`SKU-ARROZ-001`. El proceso confirmó `DATABASE_ENGINE=postgresql`, creó la venta
`VTA-20261014-321AB5` y el evento outbox
`evt-61b5cba2b33544538d6ea4449b5e357a`; Azure recibió el evento, la Queue/Function
lo procesó como `demo_fulfillment_completed` y el outbox quedó `delivered` en un
intento. El estado del ERP pasó a `completed_demo` y el saldo ficticio bajó de
24 a 23.

Para no dejar alterado el inventario de demostración, el mismo recorrido creó
una orden de compra QA `OC-20261014-E0B473`, entregada a Azure mediante el evento
`evt-397c9e4a113247e79f1f33f79fd5c4ee`; el worker informó
`demo_restock_completed`, el outbox quedó `delivered` en un intento, y el ERP
marcó `received_demo`. El saldo regresó a 24. Se generaron dos documentos
financieros de prueba (CxC/CxP). Son transacciones sintéticas persistidas en
RDS y auditoría, no operaciones comerciales ni contabilidad legal; el WMS
continúa siendo un ledger ficticio de Azure.

La Function Azure volvió a responder `/api/health` 200 y CloudFormation seguía
`UPDATE_COMPLETE`. El ALB continúa sin dominio ni HTTPS público; el túnel
temporal SSM fue cerrado al terminar. No se probó visualmente el navegador, la
conexión VPN privada, el WMS comercial ni WebRTC entre dos navegadores.

## Dataset QA sintético y recorrido ERP→Azure — 14/10/2026, 10:18 America/Chicago

El inventario es ficticio por diseño y sirve para demostrar integración y
consistencia; no se presenta como stock comercial. Desde el portal AWS, sobre
PostgreSQL/RDS, se añadieron tres distribuidores QA y un proveedor QA. La cuenta
Comercial registró tres ventas pequeñas: 2 unidades de `SKU-ARROZ-001`, 2 de
`SKU-AZUCAR-001` y 1 de `SKU-ACEITE-001`. Cada venta llegó por outbox al endpoint
HTTPS de Azure, Queue y Function; las referencias `VTA-20261014-56B41E`,
`VTA-20261014-3A9EE2` y `VTA-20261014-6E5D21` quedaron `completed_demo`. La
cuenta admin registró y recibió la compra QA `OC-20261014-012D70`; Azure la
procesó como `received_demo`.

La lectura final autenticada confirmó 7/7 eventos outbox `delivered`, seis
documentos financieros de demostración (4 CxC y 2 CxP, incluyendo el E2E previo)
y saldos del ledger Azure iguales a la lectura inicial: aceite 18, arroz 24,
azúcar 40. Las claves de QA permanecen fuera de Git en Parameter Store
`SecureString`. No hubo cambio de infraestructura ni afirmación de stock real,
WMS comercial o contabilidad legal.

## Actualización de release — 14/10/2026, 11:58 America/Chicago

Posteriormente se desplegó `20261014-synthetic-catalog-v10-python312` mediante
CloudFormation. La pila terminó `UPDATE_COMPLETE`; la detección de deriva quedó
`IN_SYNC` con cero recursos desviados. El artefacto privado versionado en S3,
cifrado AES256, tiene SHA-256
`c365c7005ba5e7f9108395f5716ef7504d706f810028dba6199144767da5b246`. SSM
confirmó el mismo `BUILD_REVISION` y hashes de aplicación/dependencias en ambas
EC2. Los dos destinos activos del ALB quedaron sanos; `/`, `/health`, `/ready`
y `/api` devolvieron 200. `/api/admin/users` sin sesión devolvió 401 y
`/metrics` devolvió 404. RDS no fue modificada: permanece cifrada, privada,
Single-AZ, con un día de retención de backups. El rollout no añade VPN,
dominio ni TLS público.

## E2E posterior desde el portal v10 — 14/10/2026, 12:09 America/Chicago

Desde una EC2 v10 vía SSM se autenticó la cuenta QA admin usando el secreto
SecureString resuelto en memoria dentro de AWS. El portal importó el SKU
`SKU-QA-V10-20261014` con saldo 10; una venta de una unidad y una recepción
compensatoria de una unidad terminaron `completed_demo` y `received_demo`.
Ambos eventos outbox quedaron `delivered` y la lectura final confirmó saldo 10,
igual a la línea base. La prueba ejecutó el flujo portal autenticado → base de
datos/outbox → Azure; la importación del archivo CSV desde el navegador no se
ha probado todavía. La evidencia reproducible está en
[`DEPLOY-CATALOGO-SINTETICO-2026-10-14.md`](../DEPLOY-CATALOGO-SINTETICO-2026-10-14.md).

## Repetición del E2E y microcarga de lectura — 14/10/2026, 12:16 America/Chicago

La misma prueba live de catálogo/venta/recepción terminó de nuevo con dos
eventos `delivered` y el ledger `SKU-QA-V10-20261014` en 10→10. Después se
ejecutaron 24 lecturas autenticadas (pedidos, compras y outbox), concurrencia 6,
contra el proceso local de una EC2: 24/24 HTTP 200, p95 304.09 ms. No hubo
escrituras durante esa microcarga. Es una medida reducida de proceso/base de
datos, directa por loopback; no es tráfico por ALB ni valida ASG, multi-AZ o
3,000 usuarios.
