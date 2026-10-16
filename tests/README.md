# Pruebas reproducibles de Tangamandapio S.A.C.

## Puerta local completa — 16/10/2026, 02:55 UTC

`run_local_quality.ps1 -ValidateTerraform` terminó `QUALITY_GATE=APROBADA`
sin llamadas de escritura a la nube: 209 pruebas unitarias, build Vite,
auditoría de dependencias sin vulnerabilidades conocidas, validación
CloudFormation y Terraform `fmt`/`init`/`validate` más cinco tests mock. Las
pruebas de navegación por rol (8) y CSV de catálogo (6) también pasaron. La
evidencia conjunta de cloud y esta puerta está en
[`CLOUD-REVALIDATION-2026-10-16-0255UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0255UTC.md).

## Evidencia viva más reciente — 16/10/2026, 02:31–02:40 UTC

Con opt-in explícito, `run_live_aws_portal_azure_e2e.ps1` pasó en modo `full`
contra `alb-origin-https`: RDS `ok`, venta/recepción demo compensadas y stock
ficticio 10→10, permisos API de Comercial/Operaciones, importación de catálogo,
dos eventos entregados y 24 lecturas 200 (concurrencia 6, p95 399.77 ms). El
modo `admin-modules` también pasó: Finanzas creó y liquidó una operación
sintética de S/ 0.05, correo entregó dentro del portal sin relay SMTP externo,
y poison queue reportó conteo 0 sin exponer mensajes. Estas pruebas dejaron
registros QA persistentes; no hicieron pagos ni cambiaron stock físico. La
revalidación de HTTPS/Azure/red/DR está en
[`CLOUD-REVALIDATION-2026-10-16-0240UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0240UTC.md).

El FQDN proxied requiere además login y revisión visual de navegador; el probe
automatizado de login recibió 403 de Cloudflare, mientras que el mismo smoke
directo al ALB con TLS válido pasó. No se probó WebRTC entre dos navegadores en
esta ejecución.

La carpeta separa pruebas locales gratuitas de pruebas que requieren una sesión temporal del laboratorio. Ningún script inicia AWS Academy ni crea recursos sin una autorización explícita.

## Puerta local (sin costo cloud)

Desde PowerShell, en la raíz:

```powershell
.\tests\run_local_quality.ps1
```

La puerta ejecuta las suites API base, Azure Functions y release AWS; compila
Python, analiza la sintaxis de los scripts PowerShell/Bash, prueba el mapeo de
peers BGP, bloquea los scripts de red sin aprobación de costo/limpieza y
verifica el preflight VPN AWS con trece escenarios mock (incluido fallo cerrado
si no puede inspeccionar el stack, CIDR/route table/ASN/IP asociada incorrectos y cambios
que requieren aprobación, más DNS privado optativo con hostname/IP completos), dos pruebas del timeout del smoke Azure y el
round-trip gzip/Base64 de la sonda SQL;
también exige opt-in para el restore RDS. Si sus
validadores están instalados, audita dependencias (`pip-audit`, `pnpm audit`)
y valida las plantillas CloudFormation. También construye el frontend en
`app/web/dist` si están instalados pnpm y sus dependencias (sin reemplazar los
archivos servidos por Flask). La compuerta ejecuta además ocho pruebas Node de
la matriz de navegación por rol, incluido el cierre por defecto para roles
desconocidos. Para actualizar lo que sirve Flask localmente, ejecutar
`pnpm run build` desde `app/web`; ese paso escribe en `app/src/static`, no en el
paquete separado `app/aws_release/current`. Para validar formato y esquema
Terraform en los entornos locales sin crear recursos, usar
`.\tests\run_local_quality.ps1 -ValidateTerraform`.

El gate Terraform también valida el root nuevo
`iac/environments/azure-flex-private`: tres pruebas mock comprueban costo
cerrado por defecto, Private Endpoint/DNS en el plan privado y acuse obligatorio
para el bootstrap público. No accede a Azure ni crea recursos.

La suite `tests/cloud` verifica el preflight de solo lectura para Tailscale:
sesión de ambos clouds, VPC/VNet exactas, CIDR no solapados, cliente online y
presencia booleana de una clave efímera. Las pruebas usan mocks; no registran
nodos, consultan claves reales ni crean rutas cloud.

Las suites API local y release AWS incluyen pruebas de rate limiting de
autenticación: bloqueo HTTP
429 con `Retry-After`, persistencia al crear otra instancia de Flask contra la
misma base, limpieza del contador tras login correcto y actualización atómica
ante fallos concurrentes. La variante release también verifica que no se
almacene el usuario en claro y su migración 0008 limpia contadores heredados.
La validación es local y no acredita configuración IAM, MFA ni protección WAF
desplegada.

La suite de API incluye pruebas CSRF de sesión anónima y autenticada: bloquea
escrituras sin cabecera, rechaza un `Origin` ajeno, acepta la cabecera ligada a
la sesión, y verifica la rotación al autenticar y salir. También se verifica en
el runtime Docker local que el bundle React envíe la cabecera y que el endpoint
de logout responda `403` sin token y `204` con token válido. No es una prueba de
autenticación de roles en navegador ni de configuración de proxy en producción.

`PasswordManagementTestCase` verifica el cambio obligatorio de clave inicial y
temporal, el cambio propio con comprobación de clave actual y longitud mínima,
la invalidación de sesiones por versión, la restricción para no auto-restablecer
al administrador, la respuesta temporal de una sola entrega, que la auditoría
no exponga el secreto y la migración aditiva de una base SQLite anterior. La
prueba de runtime del 13/10 confirma que el portal local sirve el bundle con
“Mi cuenta”, “Cambiar contraseña”, “Restablecer” y “Clave temporal”; no se hizo
una prueba de interacción manual en navegador ni una validación del release AWS.

El workflow remoto en `.github/workflows/quality-gate.yml` ejecuta además un
smoke test de salud/rendimiento local. Python se instala y audita desde
`app/requirements-ci.lock`, una resolución exacta con hashes que cubre los
manifiestos de ejecución y las herramientas de validación. Al cambiar un
manifiesto, hay que regenerar el lock con `pip-tools` y revisar el diff.
La puerta también comprueba que las versiones bloqueadas satisfagan los rangos
declarados por cada manifiesto.

Para regenerarlo conscientemente desde `app/`:

```powershell
.\.venv\Scripts\pip-compile.exe --generate-hashes --allow-unsafe --strip-extras --output-file requirements-ci.lock requirements-ci.txt
```

Luego ejecutar la puerta local completa y revisar `git diff` antes de aceptar
la actualización.
Dependabot propone actualizaciones revisables; no aplica código o infraestructura
por sí mismo. Ver el [manual de herramientas profesionales](../core/11_herramientas_profesionales_y_calidad.md).

La carga local o contra el ALB se ejecuta con:

```powershell
python .\tests\performance\load_test.py --url http://HOST/health --requests 100 --concurrency 10 --output evidencia-perf.json
```

El 13/10 se ejecutó en Docker local contra `/health`: 100 solicitudes con
concurrencia 10 (p95 303.93 ms, 0 errores) y 1000 con concurrencia 50 (p95
68.34 ms, 0 errores). Los resultados brutos están en
[`LOCAL-LOAD-BASELINE-2026-10-13.json`](../evidence/current/LOCAL-LOAD-BASELINE-2026-10-13.json)
y [`LOCAL-LOAD-STRESS-2026-10-13.json`](../evidence/current/LOCAL-LOAD-STRESS-2026-10-13.json).
Es una referencia del endpoint de salud en un contenedor y una máquina local;
no demuestra escalado automático, capacidad de ventas, alta disponibilidad en
dos zonas ni rendimiento de AWS.

El 14/10 se hizo una lectura de carga pequeña contra el ALB vivo (sin escribir
datos): 100 GET a `/health`, concurrencia 10, 3.043 s, p95 851.9 ms, 0 errores.
La muestra confirma que el health check respondió bajo ese perfil; no mide
ventas ni comportamiento del ASG. El resultado está en
[`AWS-PERF-HEALTH-2026-10-14.json`](../evidence/current/aws/AWS-PERF-HEALTH-2026-10-14.json).

Para medir el flujo transaccional del release sin tocar datos reales, se puede
ejecutar:

```powershell
.\app\.venv\Scripts\python.exe .\tests\performance\transactional_load_test.py --requests 40 --concurrency 8
```

`PT-PERF-02` crea sesiones de prueba, ejecuta `POST /api/orders` y lee cada
pedido de vuelta; verifica además que el pedido, su evento outbox y el estado
pendiente queden persistidos. La base es SQLite temporal y se elimina al salir;
el script no abre un listener HTTP, no acepta un hostname objetivo y desactiva
la entrega a Azure, correo, grabaciones, métricas y alarmas. La ejecución de
las 05:11 del 14/10 registró 40/40 pedidos creados y leídos, 40/40 eventos
outbox pendientes, cero errores, p95 550.73 ms y 53.18 transacciones/s. El
resultado bruto está en
[`LOCAL-TRANSACTIONAL-LOAD-2026-10-14-0511.json`](../evidence/current/LOCAL-TRANSACTIONAL-LOAD-2026-10-14-0511.json).
Para guardar una nueva captura, pasar `--output` con una ruta aún inexistente
(el script evita sobrescribir evidencia).
Esta prueba valida concurrencia del handler y persistencia en SQLite dentro del
proceso Flask; no mide el socket HTTP, Gunicorn, PostgreSQL/RDS, ALB, red,
autoscaling, multi-AZ ni capacidad de producción. No es directamente comparable
con el benchmark HTTP de salud anterior.
La misma comprobación de 40 transacciones/concurrencia 8 se ejecuta dentro de
`tests/run_local_quality.ps1` y del workflow `.github/workflows/quality-gate.yml`
con un umbral de p95 más amplio de 5 s para reducir sensibilidad al runner.

## E2E Azure en vivo (mutación sintética compensada)

`run_live_azure_erp_smoke.py` prueba el artefacto local
`app/aws_release/current` → outbox → Azure Queue/Function → reconciliación. No
ejecuta el portal en EC2 ni escribe en RDS. Solo debe usarse con la suscripción
de laboratorio autorizada y cuando el inventario esté marcado como
`demo-inventory-ledger`/`is_real_erp=false`:

```powershell
$env:TANGAMA_LIVE_AZURE_SMOKE = 'I_ACKNOWLEDGE_DEMO_STOCK_MUTATION'
python .\tests\run_live_azure_erp_smoke.py
Remove-Item Env:TANGAMA_LIVE_AZURE_SMOKE
```

El arnés captura el saldo de `SKU-ARROZ-001`, exige metadatos de cola poison
disponibles y conteo cero antes de empezar, vende una unidad y crea la
recepción compensatoria. Comprueba los resultados de ambos eventos, la
reconciliación ERP, el saldo final igual a la línea base y el conteo cero de la
cola poison al final. Antes de mutar, también verifica 401 sin Function key,
400 para fuente no autorizada y que el ID rechazado siga `pending`. Solo
consulta metadatos; no lee, reintenta ni elimina mensajes. Si la cola poison no
está vacía o sus metadatos no están disponibles, se detiene antes de enviar el
evento. Una corrida exitosa conserva los eventos
sintéticos en la auditoría Azure, aunque elimina la SQLite y los socios
temporales locales. La clave de Function solo se mantiene en memoria y no se
imprime. Esta prueba muta temporalmente el ledger ficticio y por eso queda fuera
de la compuerta local gratuita.

## Pruebas AWS con el laboratorio encendido

### E2E desde el portal AWS desplegado hasta Azure

`cloud/live_aws_portal_azure_e2e.py` se ejecuta solo mediante
`cloud/run_live_aws_portal_azure_e2e.ps1`, dentro de una EC2 `Online` por SSM.
Requiere una sesión AWS Academy vigente y el opt-in explícito siguiente:

```powershell
$env:RUN_LIVE_AWS_ERP_E2E = 'I_ACKNOWLEDGE_SYNTHETIC_RDS_AND_AZURE_WRITES'
./tests/cloud/run_live_aws_portal_azure_e2e.ps1
Remove-Item Env:RUN_LIVE_AWS_ERP_E2E
```

La prueba obtiene la contraseña QA desde `SecureString` usando el rol de la
instancia, no imprime el secreto ni lo envía por el ALB HTTP público. Exige que
Azure identifique explícitamente el ledger como demo, importa un SKU sintético,
crea una venta de una unidad y su recepción compensatoria, comprueba ambos
estados/outbox y requiere saldo final igual al inicial. Las órdenes y entradas
de auditoría de QA quedan persistidas; solo el saldo vuelve a su línea base.
Después del flujo mutante ejecuta 24 lecturas autenticadas de pedidos, compras
y outbox con concurrencia 6; en la última corrida hubo 24/24 HTTP 200 y p95
304.09 ms. La medición es loopback en una sola EC2 con base de datos, no incluye
ALB/ASG ni demuestra capacidad para 3,000 usuarios.
Revisa el resultado de SSM y el saldo antes de reintentar si una ejecución queda
en estado desconocido. El último éxito está documentado en
[`DEPLOY-CATALOGO-SINTETICO-2026-10-14.md`](../evidence/current/DEPLOY-CATALOGO-SINTETICO-2026-10-14.md).

- `pt-sto-01-s3.sh <STACK_NAME>`: requiere un stack `tangamandapio-live-YYYYMMDD` verificado; escribe, descarga, compara SHA-256 y elimina el objeto temporal.
- `pt-mon-01-alarm.sh <STACK_NAME>`: requiere el stack verificado y `DEMO_ALARM_STATE=YES`; identifica la alarma desde el recurso CloudFormation, fuerza brevemente su estado y restaura el estado anterior incluso si una lectura falla. Esto prueba la ruta operativa, no simula CPU real.
- `pt-sec-02-rds-deny.py`: espera que el endpoint privado rechace o sea inalcanzable desde Internet.
- `pt-dr-01-rds-restore.sh tangamandapio-live-YYYYMMDD`: requiere `CONFIRM_COSTLY_DR_TEST=YES` y el nombre exacto del stack. Antes de crear recursos verifica RDS privado/cifrado y una instancia SSM saludable; hace un preflight remoto de Python, boto3 y psycopg2 antes de escribir el marcador SQL temporal; toma snapshot, restaura RDS privado en los mismos subnets/SG con backups automáticos desactivados, valida marcador y conteos de tablas de negocio, mide RTO desde el pedido de restore hasta pasar la sonda SQL y estima el límite superior de RPO desde el checkpoint al snapshot. Usa el Python del entorno virtual del portal en la EC2, no el Python de sistema. Limpia snapshot/instancia/marcador al salir. Si la sesión termina a mitad, el script informa los nombres de prueba; revisarlos manualmente antes de repetir. El corte exitoso del 15/10/2026 midió RTO 260 s y límite superior de RPO 8 s; ver [checklist vigente](../evidence/current/CHECKLIST-CIERRE-2026-10-15.md).
- `pt-dr-snapshot-restore.ps1 -ConfirmCostlyTest`: restaura temporalmente el snapshot PostgreSQL manual cifrado, comprueba disponibilidad/privacidad/cifrado y activa Secrets Manager para la clave maestra después de restaurar. Conserva el snapshot fuente y elimina la instancia/subnet group temporales. **No valida SQL/datos ni mide RTO/RPO.** Requiere el lab activo y genera costo RDS durante la prueba; el corte live más reciente está en [`AWS-DR-RESTORE-2026-10-13.md`](../evidence/current/aws/AWS-DR-RESTORE-2026-10-13.md).
- `aws_release/tests/test_admin_recovery.py`: valida el restablecimiento explícito y de una sola vez por versión del secreto, la invalidación de sesiones y que no cambie la contraseña cuando el indicador está apagado. `destroy_safety_test.sh` usa AWS simulado para confirmar que una política desplegada sin retención de RDS/admin bloquea cualquier borrado antes de mutar recursos.

## Interconexión privada AWS–Azure

El diseño BGP preparado y su límite de tráfico actual están en
[`iac/environments/aws-azure-vpn/README.md`](../iac/environments/aws-azure-vpn/README.md).
La validación final requiere credenciales válidas de ambas nubes y comprobar
2 conexiones AWS, 4 túneles `UP` y 4 conexiones Azure `Connected`. El plan local
valida la sintaxis y el contrato de los peers; no aplica recursos, crea la VPN
ni incurre en costos cloud.

Antes de ejecutar: confirmar región `us-east-1`, stack exacto, saldo y ventana disponible. Al terminar, verificar CloudFormation `DELETE_COMPLETE`, cero coincidencias del proyecto y laboratorio terminado.
