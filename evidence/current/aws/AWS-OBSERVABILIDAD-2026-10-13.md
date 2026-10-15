# Revalidación operativa y ajuste de alarma — 13/10/2026

## Corte vivo — 16:12 America/Chicago

AWS STS autenticó en la cuenta académica del laboratorio. Se preparó el change
set `codex-high-cpu-alarm-20261013` para el stack
`tangamandapio-live-20261013` y se inspeccionó antes de aplicarlo: solo modifica
`HighCPUAlarm`, sin reemplazo. El ajuste alinea la alarma con la métrica básica
de EC2 (muestras cada 5 minutos): periodo 300 s, dos períodos/dos datapoints y
`TreatMissingData=missing`. CloudFormation terminó `UPDATE_COMPLETE` a las
16:12:40; CloudWatch confirmó esos valores y el estado `OK`.

En ese primer corte la alarma tenía `ActionsEnabled=true`, pero no acciones
SNS; evaluaba estados en CloudWatch sin enviar notificaciones.

## Comprobaciones posteriores

- ALB `/health`: HTTP 200; target group: **2/2 `healthy`**.
- Azure Function `/api/health`: HTTP 200.
- Sin sesión, `/api/platform/overview`, `/api/admin/users`,
  `/api/wms/inventory` y `/api/orders` devuelven HTTP 401. No se repitió una
  prueba de login autenticado contra el admin; su cambio obligatorio de clave
  sigue siendo el control vigente.
- RDS `tangamandapio-postgres`: `available`, privado, cifrado, Single-AZ,
  retención de backup de 1 día.
- Los buckets `tangamandapio-841113066612-us-east-1` y
  `tangamandapio-files-841113066612-us-east-1` reportan cifrado AES256.
- La regla `tangamandapio-high-cpu` ahora ve CPU cada 5 minutos. CPU tuvo
  datapoints en el período consultado; los valores observados estuvieron muy
  por debajo del umbral de alarma de 70%.

## Validación local del mismo corte

`tests/run_local_quality.ps1 -ValidateTerraform` terminó con
`QUALITY_GATE=APROBADA`: 98 pruebas unitarias, build de frontend, auditoría de
dependencias sin vulnerabilidades conocidas, validación CloudFormation,
formato/validación Terraform y cinco pruebas mock de red/costo. Estas pruebas
locales no aplicaron recursos cloud ni equivalen a un test de carga multinube.

## Alcance que permanece abierto

- AWS→Azure funciona a nivel de aplicación por HTTPS público en el E2E desde
  EC2 documentado en [interoperabilidad](../azure/AZURE-AWS-INTEROP-2026-10-13.md).
  Para intercambiar esos eventos no hace falta una VPN. La VPN/VNet añadiría
  conectividad IP privada entre redes; esa parte sigue aplazada al cierre porque
  AWS Academy denegó `ec2:CreateCustomerGateway` y no se establecieron túneles.
- El ALB sigue HTTP/80, sin dominio ni certificado; se finaliza al contar con un
  dominio bajo control y validación DNS.
- Hay dos suscripciones SNS confirmadas; falta observar una alarma real (no se
  envió notificación artificial). La matriz autenticada de roles de producción,
  el reintento del outbox ante caída real de Azure y las capturas de consola
  siguen pendientes.
- El WMS es un ledger demostrativo; la base de RDS permanece Single-AZ con una
  retención de backup diaria. La recuperación puntual sí se probó con SQL y se
  documenta en [PT-DR-01](AWS-DR-RESTORE-2026-10-13.md).

## Seguimiento de notificaciones — 16:23 America/Chicago

Con los dos correos de alertas proporcionados por el usuario, se preparó y
revisó un segundo change set. Solo añadió `AlarmNotificationTopic` y modificó
las cinco alarmas para asociar el tema; no hubo reemplazos. CloudFormation
terminó `UPDATE_COMPLETE`. AWS SNS lista dos suscripciones con ARN activo (no
`PendingConfirmation`), por lo que ambas están confirmadas. Cada una de las
cinco alarmas tiene acciones habilitadas y una acción SNS; no se envió mensaje
de prueba para evitar correos innecesarios.

Tras el update, el stack quedó `IN_SYNC` con cero recursos drifted, el ALB
conservó 2/2 destinos sanos y `/health` siguió en 200; Azure `/api/health`
también devolvió 200.

## Validación local del reintento outbox — 16:31 America/Chicago

Se añadió `test_retry_worker_recovers_failed_outbox_after_backoff` a la suite
AWS del portal. En una base SQLite temporal, una orden persistida sobrevivió a
dos `TimeoutError` simulados; el barrido no reintentó antes del vencimiento del
backoff y el intento siguiente recibió ACK `queued`, dejando el evento
`delivered`, con tres intentos y `last_error` limpio. La prueba objetivo pasó.
Esto valida la lógica local, no una caída real de Azure ni la instancia
desplegada; PT-MC-03 permanece parcial hasta probarlo de forma aislada en nube.
