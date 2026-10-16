# Paquete de release AWS

> Último release preparado: v18, `20261015-outbox-pagination-v18-python312`,
> SHA-256 `c629ab0e7b07c007cfa74c3eca1b9879c601829f44ad3471615cb85e3e09197f`.
> CloudFormation terminó `UPDATE_COMPLETE` el 16/10 a las 00:42:53 UTC. A las
> 01:17 UTC la app seguía en 503; AWS STS autentica, pero CloudFormation, ELB,
> ASG y RDS de lectura son denegados por `voc-cancel-cred`; la disponibilidad y
> el smoke autenticado v18 no están confirmados. Azure Function está `Running`,
> health 200 y el E2E sintético
> local→Azure pasó. Véase
> [la revalidación 01:17 UTC](../../evidence/current/CLOUD-REVALIDATION-2026-10-16-0110UTC.md).

## Release v18 desplegado — paginación íntegra del outbox

`current/BUILD_REVISION` identifica `20261015-outbox-pagination-v18-python312`.
La API conserva el arreglo JSON histórico de `GET /api/outbox` y agrega
`limit`/`offset` y metadatos de página; el panel de plataforma recorre el
historial y muestra el total completo. La consulta usa orden estable y se añadió
el índice correspondiente a las migraciones SQLite y PostgreSQL.

El artefacto inmutable se subió al bucket privado con SSE-S3 y metadato SHA-256
verificado. La puerta local aprobó 209 pruebas. Las pruebas específicas
verificaron 45 eventos en dos páginas de 30 + 15, compatibilidad del arreglo
anterior y rechazo de parámetros fuera de rango. El código v18 está desplegado,
pero su disponibilidad final no quedó confirmada por la denegación del
laboratorio.

## Corte anterior — 15/10/2026, 23:24 UTC (v17)

CloudFormation
`tangamandapio-live-20261013` terminó `UPDATE_COMPLETE`; drift `IN_SYNC`
(0 recursos desviados). El ASG volvió a 2/2 deseadas/sanas (máximo 5); un
destino anterior seguía drenando durante la limpieza. El portal HTTPS, salud,
readiness y el bundle v17 respondieron 200; HTTP redirige con 301.
El E2E sintético desde EC2 por ALB-HTTPS completó venta y recepción hacia
Azure, con dos eventos entregados y el ledger demo restaurado 10→10.
Corte de módulos: 15/10/2026, 23:45 UTC. Smoke remoto de Finanzas creó,
liquidó y releyó una cuenta sintética de S/ 0.05; el correo `portal_only`
llegó al buzón Comercial y se marcó leído; la Azure poison queue informó 0
mensajes, consultada sin mutar ni exponer payloads. Resumen admin: 1 pedido,
0 pendientes, 45 entregados; la lista de esa versión mostraba solo los 30 más
recientes. SNS: 2 confirmadas/0 pendientes; no se disparó alarma ni se envió
SMTP. No se registra material de credenciales en este archivo.

## Release v17 desplegado — indicador de salud coherente con API pública

`current/BUILD_REVISION` identifica
`20261015-dashboard-health-card-v17-python312`. SHA-256 del artefacto:
`f2a4f3b8b58fae62529d27842c8422cc0c408f189efbef8956125f2e3891c8fa`. La revisión
y el digest coinciden entre plantilla, parámetros vivos y el objeto privado en
S3 (cifrado SSE-S3). El paquete está excluido de Git; se versionan fuentes,
plantilla y evidencia, nunca credenciales.

El indicador AWS ya no espera detalles de base de datos que el endpoint público
omite intencionalmente: traduce solo el estado agregado seguro que devuelve
`/health`, sin exponer dependencias internas. El bundle con hash
`index-473d503bd063.js` fue descargado por HTTPS (200; 289742 bytes).

La portada usa el SVG versionado en
`current/static/images/tangamandapio-operations.svg`, no PNG ni audio local
ignorado por Git. Las páginas incluyen query de release en los bundles para
evitar respuestas antiguas del CDN. HTTPS con verificación TLS normal devolvió
200 para portada, `/health`, `/ready` y el bundle; HTTP devolvió 301 a HTTPS.

La actualización gradual de CloudFormation terminó correctamente, con drift
`IN_SYNC` y cero diferencias. El ASG terminó en 2 deseadas, 2 sanas y máximo 5;
el balanceador tenía dos destinos sanos y el anterior en drenaje mientras
terminaba su baja. Detalle, prueba E2E y brechas en
[la revalidación del 15/10 a las 23:24 UTC](../../evidence/current/CLOUD-REVALIDATION-2026-10-15-2324UTC.md).

La puerta local del corte v17 aprobó 197 pruebas Python, 14 Node, 40 transacciones aisladas,
build/auditorías frontend y dependencias, `cfn-lint`, y Terraform
`fmt`/`validate`/pruebas con mocks en seis raíces. GitHub Actions para el commit
`a257a71` pasó sus tres jobs. El E2E verificó Admin, Comercial y Operaciones en
la API; el recorrido visual autenticado/CSV y WebRTC entre dos navegadores aún
no están probados. En la revalidación del 15/10 a las 23:45 UTC, la suite
específica del smoke obtuvo 26 aprobadas y el quality gate general 205; este
último no ejecutó Terraform ni desplegó infraestructura. Detalle en
[`CLOUD-REVALIDATION-2026-10-15-2345UTC.md`](../../evidence/current/CLOUD-REVALIDATION-2026-10-15-2345UTC.md).

## Historial — candidato v15 (supersedido por el release v17)

### Candidato local v15 — corte histórico anterior al despliegue

En el corte de las 20:45 UTC, `current/BUILD_REVISION` identificaba
`20261015-public-safe-landing-v15-python312`. Aquel paquete reproducible tenía SHA-256
`a0558db0c96bbb0622ec599555795d4a9d3703141c4856b4ac14fe3ecb4a2987`, y la
plantilla CloudFormation apuntaba entonces a esa revisión y digest. En aquel
corte no se pudo confirmar su presencia en S3 ni el despliegue porque el CLI
respondía `ExpiredToken`; ambos puntos quedaron resueltos después con v16.

El paquete reemplaza la portada rasterizada por el vector versionado en el
repositorio `static/images/tangamandapio-operations.svg`; excluye explícitamente
los PNG y el audio locales ignorados por Git, y las páginas del portal,
administración y observabilidad apuntan al CSS con hash SHA-256 actualizado.
El preload espera a `HTMLImageElement.decode()` antes de revelar la portada y
mantiene el comportamiento de movimiento reducido. Se conserva el cableado de
dimensiones CloudWatch que llegó en el candidato anterior.

La puerta local completa aprobó 181 pruebas Python, 14 pruebas Node, build y
auditoría frontend, auditorías de dependencias Python, CloudFormation con
`cfn-lint`, y Terraform (formato, validación y pruebas con mocks); el flujo de
carga simulada aprobó 40 transacciones aisladas. En ese corte, esto validaba el
candidato local y no un despliegue vivo. La revisión visual del panel admin
quedó pendiente porque la sesión de control de Chrome se interrumpió antes de
abrir sus módulos.

El último release confirmado en nube en aquel corte era v12,
`20261015-login-drawer-a11y-v12-python312`, SHA-256
`c884314dd8ec617df90739aeee25d2f912d7e1d70ec1e66d442fbc6720407c13`. Se
se necesitaba una sesión AWS CLI vigente para publicar v15 con clave inmutable,
aplicar el cambio gradual y verificar salud; el trabajo posterior desplegó v16.

## Historial — release v12, foco seguro del acceso oculto

Se añadió `accessibility-drawer-7f1356105ee4.js` al bundle de `current/`.
Observa el estado del panel de login, marca el contenedor `inert` y
`aria-hidden="true"` al cerrarse y devuelve el foco al disparador. Al abrirse,
quita ambos estados y enfoca el campo corporativo. En Chrome HTTPS comprobé que
Tab ya no entra al campo oculto y que al abrir el panel el foco sí llega al
usuario. Tema claro/oscuro probado y se restauró el tema oscuro. El usuario
debe autenticarse manualmente antes de probar las vistas privadas.

La suite del paquete pasó 45 pruebas y la suite `current/` pasó 12. También pasó
`node --check` para el helper y el empaquetado reproducible generó el mismo SHA
dos veces. `cfn-lint` no estaba instalado en el entorno local; no se afirma una
validación con esa herramienta en este corte.

## Historial de release v11 — carga de imagen sin aparición parcial

El estado de despliegue de v11 en esta sección es histórico y queda supersedido
por el corte v12 de arriba. La evidencia contemporánea está en
[el intento v11 del 14/10](../../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

## Release v11 — carga de imagen sin aparición parcial

La portada usa el póster pixelado y difuminado `walpurgis-rising-pixel-diffused-v1.png`.
El servidor añade su `preload` solo para una sesión anónima; el JavaScript espera
a `HTMLImageElement.decode()` antes de mostrarlo con una transición breve y
respeta `prefers-reduced-motion`. Si el usuario ya inició sesión, no se descarga
el póster innecesariamente; si cierra sesión en la SPA, el observador lo carga
cuando aparece de nuevo la portada.

El HTML se sirve con `no-cache, max-age=0, must-revalidate`; API, salud, archivos
estáticos sin versión y grabaciones siguen con `no-store`. Los bundles con hash
de contenido y la imagen versionada usan `public, max-age=31536000, immutable`.
El cambio evita servir una URL mutable como inmutable y actualiza las entradas
HTML de portal, administración y centro de nube para apuntar al CSS versionado.
Pruebas locales: 64 de `app/tests/test_app.py` y 45 del paquete AWS. La puerta
completa más reciente aprobó 165 pruebas Python, 14 pruebas Node, el build
frontend, auditorías y Terraform sin `apply`. El empaquetador normalizado
produjo el mismo SHA en WSL y Git Bash. El PNG original sigue pesando unos 2 MB; esta versión
prioriza y decodifica la imagen antes de revelarla, pero no cambia su formato.

## Referencia del artefacto v9 desplegado

La revisión local es `20261014-public-diagnostics-hardening-v9-python312`.
El paquete final local es
[`portal-b2b-20261014-public-diagnostics-hardening-v9-python312.tar.gz`](../../artifacts/portal-b2b-20261014-public-diagnostics-hardening-v9-python312.tar.gz),
SHA-256 `78327e426cf86368cbc3a455be6241b57148bf8c43de6fe14f4e33041ea15316`.
El cambio elimina el hostname privado de EC2 en las respuestas públicas `/api`
y `/health`, devuelve solo estado agregado desde `/health` aunque verifique la
base internamente, reduce `/ready` a su estado sin exponer el detalle de la
dependencia y apaga `/metrics` salvo opt-in explícito; si se habilita, exige un
admin autenticado. La versión previa respondió en producción con nombres DNS
internos en `/api` y `/health`; este hardening se incorporó en v9. La evidencia
viva enlazada arriba resume las respuestas verificadas en ese corte.

La compuerta local aprobó 133 pruebas Python, 8 pruebas de navegación por rol,
PT-PERF-02, build web, auditorías de dependencias, CloudFormation y
validación/tests Terraform. Las pruebas verifican `/metrics` 404 por defecto,
401 sin sesión y 403 para el rol sales al habilitarlo; admin recibe 200. La
prueba del empaquetador generó dos archivos idénticos y el hash coincidió con
el artefacto v9 desplegado, según el corte AWS enlazado arriba.

### Release v10 desplegado — catálogo sintético (14/10/2026)

`current/BUILD_REVISION` identifica `20261014-synthetic-catalog-v10-python312`.
El cambio añade al ERP del paquete la importación de hasta 500 SKU desde CSV
UTF-8 preparado con la plantilla Excel, una vista previa, validación de filas
y sincronización idempotente con el ledger ficticio Azure. El saldo inicial se
aplica solo a SKU nuevos; las actualizaciones conservan el saldo actual. AWS
publicó el artefacto en el bucket privado versionado con SSE-S3, y CloudFormation
terminó `UPDATE_COMPLETE`; los dos destinos regresaron a `healthy`, el hash de
los archivos principales coincidió en ambas EC2 y el drift quedó `IN_SYNC`. Azure
recibió el paquete Function con el catálogo v2; su plan Terraform posterior dio
`No changes` y la ruta de catálogo viva preservó el saldo demo. Esto sí es un
despliegue, pero no una prueba visual de la carga CSV en navegador ni un E2E de
la aplicación AWS v10 hacia RDS y Azure. El
artefacto reproducible es
[`portal-b2b-20261014-synthetic-catalog-v10-python312.tar.gz`](../../artifacts/portal-b2b-20261014-synthetic-catalog-v10-python312.tar.gz),
SHA-256 `c365c7005ba5e7f9108395f5716ef7504d706f810028dba6199144767da5b246`;
la prueba del empaquetador lo generó dos veces con el mismo hash y verificó que
incluye ambos formatos de plantilla y el parser web.

El release incluye la consola `/administracion` para usuarios, roles,
empresas, auditoría y destinatarios SNS. El tema SNS queda desactivado en local
por defecto; el CRUD de suscripciones se prueba con un SNS simulado y requiere
confirmación por correo al habilitarlo en AWS. También conserva hardening de
autenticación, recuperación de contraseñas, correo/ERP y observabilidad. El
release v5 se desplegó con un cambio gradual y conserva el filtrado server-side
de agregados del resumen ERP: ventas, compras y saldos financieros solo se
incluyen para los permisos correspondientes; ambas interfaces esconden los
indicadores no autorizados. Hay pruebas explícitas en el backend local y en el
paquete de release.

El bundle de release es distinto de `app/web`, la SPA local. No compilar la
SPA local sobre `current/static`: el release mantiene su propio frontend para
las vistas activas de telefonía y administración.

El artefacto incluye Flask, sus migraciones SQLite/PostgreSQL, el frontend
compilado del portal y la extensión ERP/correo. Los cambios del portal de
producción se empaquetan desde este directorio; no se debe reemplazar el bundle
principal con `app/web` porque no contiene las vistas actuales de telefonía y
administración.

El runtime AWS se instala en un virtualenv Python 3.12 desde
`current/requirements.lock` con `pip --require-hashes`; sus versiones quedan
alineadas con el lock de CI y la auditoría de vulnerabilidades forma parte de
la compuerta local. Esto es deliberado: AL2023 conserva `/usr/bin/python3` en
3.9, mientras Boto3 1.43.110 requiere 3.10 o superior. No se altera el Python
del sistema. La compatibilidad Linux se valida con un dry-run dirigido a
CPython 3.12/manylinux. Para regenerar el lock, compila `requirements.txt`
usando como restricciones `../../requirements-ci.lock` y valida de nuevo
ambos manifests y el dry-run antes de publicar. Referencias primarias:
[Python en AL2023](https://docs.aws.amazon.com/linux/al2023/ug/python.html) y
[metadatos de boto3 1.43.110](https://pypi.org/project/boto3/1.43.110/).

Las grabaciones usan un bucket privado independiente definido en
`iac/cloudformation/voice-recordings.yaml`. La aplicación deriva su nombre del
ARN de Secrets Manager ya inyectado en las instancias, salvo que se configure
`VOICE_RECORDINGS_BUCKET` explícitamente. En SQLite se conserva almacenamiento
local únicamente para desarrollo; PostgreSQL no habilita grabaciones sin S3.

Para validar el paquete desde este directorio:

```powershell
python -m py_compile app.py
python -m unittest discover -s tests -v
```

## Backend desplegado y validación Azure (8 de octubre de 2026)

El paquete local ahora incorpora la migración `0006_user_security_lifecycle`
y estos endpoints protegidos:

- `PATCH /api/admin/users/<id>` cambia rol, empresa y estado activo; cada cambio
  incrementa `auth_version` e invalida las sesiones anteriores.
- `POST /api/admin/users/<id>/reset-password` emite una contraseña temporal,
  la revela una sola vez y obliga al usuario a cambiarla.
- `POST /api/auth/password` valida la contraseña actual y exige una nueva de al
  menos 12 caracteres; después revoca la sesión.
- `GET /api/voice/ice-config` entrega STUN y, solo si están configurados
  `WEBRTC_TURN_URLS` y `WEBRTC_TURN_SHARED_SECRET`, credenciales TURN efímeras.
  La clave compartida nunca se devuelve al navegador.
- `GET /api/outbox/<event_id>/fulfillment-status` consulta el resultado final
  de un evento local en Azure y marca expresamente los estados simulados. El
  despacho reconoce el acuse `queued_duplicate`, que Azure usa al recibir un
  evento repetido de forma idempotente.

Estos cambios quedaron registrados como desplegados gradualmente en ambas instancias AWS como revisión
`20261008-azure-fulfillment-status`. El paquete se conserva en S3 como
`releases/tangamandapio/portal-20261008-azure-fulfillment-status-29d65428.tar.gz`;
la versión anterior permanece en el directorio de backup de cada EC2. La
migración invalida las sesiones
anteriores; los usuarios deben volver a iniciar sesión. El frontend actual no
consume todavía `ice-config` y no existe un servidor TURN configurado. La
interfaz desplegada tampoco tiene controles para editar o resetear usuarios:
esos flujos están en la API y requieren integrarse en la fuente React
recuperada/reconstruida antes de que el usuario final los use.

El ALB y ambas EC2 quedaron saludables tras el despliegue. La nueva consulta
protegida de estado WMS respondió `401` sin sesión (esperado). El 8 de octubre,
la clave ordinaria `default` de Azure se guardó en AWS Parameter Store como
`SecureString` (`/tangamandapio/azure/function-key`, versión 1). Se validó la
coincidencia con la configuración de ambas EC2 sin imprimir el valor, se hizo
el reinicio gradual y ambas instancias regresaron a `healthy`; las dos
consultaron el evento sintético en Azure y recibieron HTTP 200 con
`simulated_completed`. El Worker WMS continúa en modo demostración y no mueve
inventario.

La fuente React/CSS correspondiente al bundle actual no está incluida en este
checkout ni en el paquete de release consultado en S3: este solo contiene
`static/assets` compilados, sin `src/`, `web/` ni source map. El historial local
solo conserva una interfaz anterior. No compilar `app/web` sobre `current/static`
hasta reconstruir y validar las vistas actuales de telefonía, administración y
estilos.

## Reconstrucción verificada — 9 de octubre de 2026

El artefacto estable anterior se publicó en `tangamandapio-live-20261005` tras
recrear el stack: estado `UPDATE_COMPLETE`, dos instancias EC2 y ambos destinos
del ALB saludables. `/health` respondió 200 con `database=ok`; RDS quedó cifrada
y privada. El ALB continúa solo en HTTP, sin dominio ni certificado confiable.

Se verificó login del administrador y autorización: el portal devuelve estado
de salud `ok`, `/erp` y sus archivos CSS/JS responden 200, y el panel carga
`erp_admin`, tres productos, buzón interno y WMS conectado. El despliegue
`20261009-erp-internal-mail` quedó activo tras un change set sin reemplazos ni
cambios a RDS. La evidencia integral está en
[`CIERRE_NUBE_2026-10-09.md`](../../evidence/current/CIERRE_NUBE_2026-10-09.md).

## ERP y correo interno — revisión 9 de octubre de 2026

El módulo `/erp` vive en la misma sesión, protección CSRF y PostgreSQL RDS.
Incluye maestros de clientes/proveedores y productos, ventas, compras y
recepción, cuentas por cobrar/pagar, gastos básicos, roles ERP independientes
y correo interno con bandeja, enviados y lectura. El admin pudo abrir los
endpoints de resumen, catálogo y directorio de correo; la cuenta inicial es el
único usuario corporativo disponible en esta base reconstruida.

El paquete ahora admite un relay SMTP configurable (`ERP_SMTP_*`) y registra
si el relay aceptó una copia; el mensaje original se conserva en el buzón del
portal incluso cuando SMTP falla. El stack AWS descrito arriba no tiene esas
variables configuradas, así que allí sigue en modo portal-only. El receptor
Mailpit de Compose es solo un sink local de pruebas, no se publica en AWS ni
envía a Internet. La entrega pública requiere dominio verificado, direcciones
de buzón reales y secretos SMTP; las cuentas `.local` actuales solo sirven en
el entorno de laboratorio. No hay buzones IMAP ni adjuntos. Las existencias
siguen siendo propiedad del WMS Azure. El inventario y el consumidor Azure son
de demostración, no un WMS comercial ni contabilidad legal.

## Recursos locales no redistribuidos

El paquete local puede contener música e imágenes suministradas para la interfaz.
Se excluyen del repositorio público hasta confirmar derechos de redistribución;
la aplicación conserva sus fondos de reserva si no están presentes. No subir
tokens temporales de AWS Academy ni archivos de credenciales.

## Centro de plataforma local

La página independiente `/platform` agrega una vista de operación y seguridad
para Administración y Operaciones TI, con telemetría CloudWatch opcional y
controles de edición/restablecimiento para usuarios. Las métricas no se
simulan: se muestran como no configuradas si faltan permisos o identificadores.
La guía y la política de solo lectura están en
[PLATFORM_CONSOLE.md](PLATFORM_CONSOLE.md); consulta el mapa actual antes de
afirmar el estado de publicación y prueba del panel.
