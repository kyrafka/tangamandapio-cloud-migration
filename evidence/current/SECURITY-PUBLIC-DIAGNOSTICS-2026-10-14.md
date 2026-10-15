# Hardening de diagnósticos públicos — 14/10/2026

## Candidato v9 y último release AWS confirmado — 07:49 America/Chicago

La fuente actual en `app/src` y en `app/aws_release/current` conserva el
chequeo interno de base de datos y devuelve desde `/health` solo el estado
agregado y timestamp; `/ready` es mínimo y `/metrics` queda apagado por defecto.
Si se habilita, requiere admin autenticado. El candidato v9 pasó la compuerta
integral de 140 pruebas Python, 8 Node, PT-PERF-02, build, auditorías e IaC. El
paquete local reproducible es
[`portal-b2b-20261014-public-diagnostics-hardening-v9-python312.tar.gz`](../../artifacts/portal-b2b-20261014-public-diagnostics-hardening-v9-python312.tar.gz),
SHA-256 `78327e426cf86368cbc3a455be6241b57148bf8c43de6fe14f4e33041ea15316`.
Las pruebas verifican 404 por defecto, 401 sin sesión, 403 para sales y 200
para admin al habilitar la ruta. No está publicado.

En el corte de 06:46, la consola AWS autenticada confirmó el stack `tangamandapio-live-20261013`
`UPDATE_COMPLETE`, dos instancias saludables y dos destinos `Healthy`. El
parámetro del stack identifica el paquete vivo como
`20261014-erp-admin-security-v5-python312` (SHA-256
`19d1c9ae9225316a5802932ab89f2781480ae9eeedf4945ee5e2308ae0273bad`). El
candidato v9 continúa sin publicar/desplegar; no se modificó AWS.

Una relectura HTTP del DNS actual del ALB devolvió 200 en `/health`, `/ready`
y `/api`; `/health` conserva las claves `database` e `instance`, y `/api` la
clave `instance`. `/api/admin/users` sin autenticación devolvió 401. GET
anónimo a `/metrics` devolvió 200 y un cuerpo de 592 bytes; el cuerpo no se
inspeccionó ni guardó. Esto confirma que el runtime AWS no tiene el hardening
del candidato v9. AWS CLI devolvió `ExpiredToken` a las 07:05 y de nuevo a las
07:39; Chrome no permitió verificar la URL activa. 06:46 sigue siendo el último estado cloud
confirmado y no se afirma que siga igual ahora.

Los procesos que sirven `127.0.0.1:8080` y `:8081` son previews Flask antiguos:
`/health` aún devuelve el campo `database`, y `:8080` además incluye el host
de instancia. No se reiniciaron porque no se pudo confirmar su configuración,
base ni sesión. En AWS, el último release confirmado era v5 y el hallazgo del
ALB seguía abierto; no se hizo despliegue.

## Revalidación HTTP local — 08:15 America/Chicago

GET a `/` respondió HTTP 200 tanto en `127.0.0.1:8080` como en
`127.0.0.1:8081`; un GET anónimo a `/api/admin/users` respondió HTTP 401 en
ambos. No se leyó el cuerpo ni se inició sesión. Esto confirma que esa ruta
administrativa no acepta acceso anónimo en los procesos actuales, pero no
valida las capacidades del panel ni los permisos de sesiones autenticadas.
Los procesos siguen siendo previews antiguos; `/health` aún devuelve `database`
y el servicio `:8080` también expone `instance`.

## Candidato v7 y revisión HTTP local — 05:39 America/Chicago

El candidato `20261014-public-diagnostics-hardening-v7-python312` elimina
`database: ok/error` de `/health`; conserva la comprobación SQL interna y usa
solo el estado agregado (`ok`/`degraded`) y el código 200/503. Si la conexión
falla, la respuesta no identifica la dependencia ni incluye su error. Pruebas
para éxito y fallo pasan tanto en `app/src` como en el release AWS. El resto del
hardening (sin hostnames en `/api`/`/health`, `/ready` mínimo y `/metrics`
desactivado por defecto) también pasa en la puerta integral de 132 pruebas y
8 pruebas Node.

El artefacto local, no publicado, es
[`portal-b2b-20261014-public-diagnostics-hardening-v7-python312.tar.gz`](../../artifacts/portal-b2b-20261014-public-diagnostics-hardening-v7-python312.tar.gz),
SHA-256 `cd322774ad89b0ddbcb7e1747e58765be1065a9a40a7784be5cd9b7016f471a3`.
No reemplaza el release v5 de AWS. La revalidación de STS sigue en
`ExpiredToken` y el ALB no se volvió a consultar.

El servicio vivo local `127.0.0.1:8081` se identificó como `python -m flask
--app src.app run` y no ha recargado el módulo; la lectura HTTP aún contiene
`database`. Se dejó intacto porque la identidad/configuración runtime y la
base de datos/sesión que usa ese proceso no se pudieron confirmar. El cambio
está en el código y el paquete probados, no en ese proceso ni en `:8080`.

## Relectura del release vivo — 04:59 America/Chicago

La sesión AWS `default` expiró (`ExpiredToken`), así que no fue posible
consultar el plano de control ni preparar un despliegue seguro. El ALB aún
responde `/api` y `/health` 200 con un campo `instance`, `/metrics` devuelve
200 sin sesión y `/api/admin/users` anónimo devuelve 401. No se leyó el cuerpo
de métricas ni se registró el valor del host. Azure Function `/api/health`
responde `ok`. El v6 local todavía no está desplegado: el hallazgo sigue
abierto en producción.

## Revalidación de la brecha — 04:07 America/Chicago

El ALB volvió a responder 200 en `/api`, `/health` y `/metrics`; `/api` aún
incluye `instance`. La ruta anónima `/api/admin/users` continúa devolviendo
401. La Function Azure respondió 200 en su endpoint de salud. El release AWS
v5 sigue publicado, por lo que la exposición operativa permanece abierta.

El candidato v6 se probó después en un servidor Flask aislado en
`127.0.0.1:8081`: `/api`, `/health` y `/ready` 200 sin `instance` ni detalle de
dependencias, `/metrics` 404 por defecto y API administrativa 401. El servicio
`127.0.0.1:8080` existente no se tocó y aún mantiene la versión anterior.

## Hallazgo vivo

Aproximadamente a las 03:32 America/Chicago, una lectura anónima del ALB mostró que `/health` y
`/api` devolvían el campo `instance` con el nombre DNS privado de la EC2. Diez
GET seguidos a `/health` respondieron `200` y dos valores distintos de
`instance`, señal de que al menos dos backends atendieron solicitudes. La API
AWS que permitiría consultar el ASG y el target group devolvió `AccessDenied`
por el `explicit deny` `voc-cancel-cred`; no se deduce el número total ni el
estado formal de salud del target group.

El API administrativo público sin sesión devolvió `401`, por lo que esta
observación no implica exposición de datos administrativos. `/ready` también
devolvía detalle de la dependencia de base de datos. `/metrics` respondió
`200` anónimo; no se recuperó ni guardó su cuerpo durante la comprobación, pero
la ruta publica contadores operativos según el código del release.

## Corrección preparada localmente

El candidato `20261014-public-diagnostics-hardening-v6-python312`:

- retira el hostname privado de las respuestas `/api` y `/health`;
- conserva el chequeo de base de datos y el estado HTTP de `/health` para la
  sonda del ALB y los scripts de despliegue;
- hace que `/ready` responda solo `ready`/`not_ready` y el código HTTP, sin
  publicar el detalle de la dependencia;
- deshabilita `/metrics` por defecto en el release de nube; Compose local lo
  habilita explícitamente para Prometheus dentro de la red del proyecto;
- deja los hostname de instancia únicamente en telemetría interna del servidor.

Se añadieron pruebas de regresión para los endpoints en el backend local y en
el release empaquetable, incluida la desactivación predeterminada de métricas y
el opt-in local. La compuerta integral pasó: 126 pruebas Python, 8
pruebas Node de permisos/navegación, build Vite, auditorías de dependencias,
CloudFormation y validación/formato/tests Terraform. No se hicieron llamadas
de escritura a AWS o Azure.

El paquete local final es
[`portal-b2b-20261014-public-diagnostics-hardening-v6-python312.tar.gz`](../../artifacts/portal-b2b-20261014-public-diagnostics-hardening-v6-python312.tar.gz),
SHA-256 `bfe3e7e45dd4f5c4a06ff6a795740801e88b9e949778b566682b0624bdd1606c`.
El archivo incluye `BUILD_REVISION`, backend, migraciones, locks y frontend del
release; se verificó el contenido y la huella después de pasar el gate.

## Estado de publicación

Este candidato **no está desplegado ni subido a S3**. El release v5 sigue
siendo la versión documentada como publicada; las respuestas públicas del ALB
seguirán exponiendo los hostnames hasta que se apruebe un despliegue v6 y se
repitan las sondas. No se cambió infraestructura durante este trabajo.

La relectura de las 03:40 confirmó que `/api` y `/health` siguen devolviendo el
campo `instance` en el release vivo, mientras `/api/admin/users` sin sesión
responde `401` y `/metrics` responde `200`. Esto confirma que el riesgo todavía
debe tratarse como abierto, no como mitigado en producción.

El listener local `127.0.0.1:8080` también sirve el proceso anterior (`/api` y
`/health` con `instance`, `/metrics` 200); los tests del candidato v6 corrieron
en entorno aislado y no actualizaron ese proceso. No se reinició porque no hay
`app/.env`/`BOOTSTRAP_ADMIN_PASSWORD` y Docker Desktop no responde, por lo que
no se pudo identificar el contenedor, preservar su base de datos y reutilizar
su acceso con seguridad. El código y paquete v6 están listos, pero la vista
local abierta aún no los refleja.

## Estado vigente tras desplegar v9 — 14/10/2026, 08:49 America/Chicago

La sección histórica anterior queda superada para AWS. El release
`20261014-public-diagnostics-hardening-v9-python312` está instalado en las dos
EC2 y CloudFormation reportó `IN_SYNC`. Desde el ALB, GET anónimo comprobó
`/health` 200 con `status,timestamp`, `/ready` 200 con `status`, `/api` 200 sin
hostname, `/metrics` 404 y `/api/admin/users` 401. Esto verifica la superficie
pública y sus límites; no valida permisos de todas las sesiones autenticadas.

El login del admin AWS respondió HTTP 200, pero el siguiente GET protegido a
`/api/wms/inventory` devolvió HTTP 428 por `must_change_password`. No se
desactivó esa protección ni se intentó otra contraseña. No se generaron pedidos
ni se mutó inventario. Hay que completar el cambio de contraseña inicial en el
portal antes de probar los módulos con esa cuenta.
