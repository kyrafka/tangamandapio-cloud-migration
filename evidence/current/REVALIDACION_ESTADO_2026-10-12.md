# Revalidación del estado actual — corte 13/10/2026

## Corte más reciente — 00:22 America/Chicago, 13/10/2026

- AWS STS aceptó las credenciales nuevas en `default`. El inventario posterior a
  la prueba temporal muestra cero EC2, ALB y RDS del proyecto; el único stack
  CloudFormation activo sigue siendo el de AWS Academy.
- La prueba aislada de recuperación RDS terminó `PT-DR-SNAPSHOT-RESTORE=PASSED`:
  restauró el snapshot cifrado y privado, activó el secreto maestro administrado
  por RDS y eliminó la instancia/subnet group temporales. El snapshot fuente
  sigue `available`. No se leyó SQL ni se midió RTO/RPO; véase
  [la evidencia de restauración](aws/AWS-DR-RESTORE-2026-10-13.md).
- La simulación de `rds:ModifyDBInstance` sin contexto había dado
  `implicitDeny`; con región, motor, clase y almacenamiento correctos dio
  `allowed`, y la operación real de rotación completó. No se volvió a cambiar
  infraestructura permanente.
- La compuerta local completa pasó 79 pruebas unitarias, auditorías de
  dependencias, build frontend, validación CloudFormation/Terraform y dos
  pruebas mock de la compuerta VPN.
- Azure for Students aparece habilitada y el endpoint público
  `/api/health` respondió HTTP 200. La consulta de administración de Function
  se demoró y se canceló; por tanto `Running` no se revalidó en este corte. La
  ausencia de VNet/VPN se verificó por última vez el 12/10, no hoy.

**Pendiente inmediato:** ejecutar una sonda SQL desde una red autorizada para
comparar los datos restaurados, medir RTO/RPO y después desplegar el portal
permanente. La conexión privada AWS–Azure continúa sin desplegarse.

## Resultado

No se aplicaron cambios de infraestructura ni se iniciaron/pararon recursos
cloud. Se hizo una prueba funcional Azure→Queue/Blob: escribió eventos
sintéticos y modificó temporalmente el ledger ficticio; la recepción
compensatoria devolvió el stock a su valor inicial. Los eventos sintéticos de
auditoría permanecen en Azure.

### AWS Academy — corte previo 22:52; sustituido por el corte más reciente

#### Actualización con credenciales nuevas — 22:52 America/Chicago

- El usuario confirmó que el Learner Lab estaba encendido y proporcionó una
  terna nueva. Se actualizó `default`; STS aceptó la sesión.
- Las lecturas de inventario ya funcionaron. Hay un stack Academy en
  `CREATE_COMPLETE`, pero no es el portal Tangamandapio. No hay EC2 ni ALB del
  proyecto, ni RDS en línea.
- Se conserva el snapshot manual PostgreSQL cifrado del 09/10, en estado
  `available` (20 GiB). El secreto maestro guardado anteriormente fue eliminado
  durante el apagado; se requiere una estrategia explícita de rotación antes
  de restaurar. No se cambió el snapshot y no se desplegó infraestructura.
- Evidencia detallada: [inventario actualizado](aws/AWS-INVENTARIO-2026-10-12.md)
  y [autenticación](aws/AWS-REVALIDACION-STS-2026-10-12.md).
- Se rotó la clave de `receive_fulfillment_event` en Azure y se sincronizó la
  versión nueva en `tangamandapio/azure/function-key` de AWS Secrets Manager;
  la comparación Azure↔AWS se verificó en memoria y no se registró el valor.
  La anterior se invalidó después de una exposición transitoria en una salida
  de diagnóstico local; no debe reutilizarse.
  Una solicitud sintética con JSON vacío devolvió el `400` de validación
  esperado, no un `401`: confirma autenticación, sin guardar ningún evento.
- La compuerta local volvió a aprobar: 74 pruebas unitarias, auditorías de
  dependencias, build frontend, CloudFormation y validación/formato Terraform.
  No despliega recursos.
- Ese secreto es un cambio de integración cloud; no se creó el stack del portal.
  RDS y el procedimiento de recuperación aún requieren resolver el secreto
  maestro eliminado antes de restaurar el snapshot.

- `aws sts get-caller-identity` autentica como una sesión del laboratorio en la
  cuenta terminada en `06612`.
- Las consultas `cloudformation list-stacks` y `ec2 describe-instances` son
  rechazadas por denegaciones explícitas de la política `voc-cancel-cred`.
- La automatización de Windows detuvo el acceso al navegador antes de mostrar
  AWS Academy; por tanto no se pudo observar ni pulsar **Start Lab** en esta
  revisión. La aceptación de STS no prueba que el laboratorio esté iniciado ni
  que permita operar los servicios.
- Estado del lab y del inventario AWS: **no verificados en este corte**. No se
  afirma que esté encendido.

### Azure

- Suscripción seleccionada: `Azure for Students` (`Enabled`).
- Resource Group: `rg-tangamandapio-rebuild-wus`, región `westus`.
- Function App `tangama-wms-261008`: `Running`; inventario de funciones incluye
  `health`, `receive_fulfillment_event`, `fulfillment_status`,
  `demo_inventory`, `poison_queue_status` y `process_fulfillment_message`.
- `terraform plan -detailed-exitcode -lock=false -var-file=rebuild.tfvars.example`
  en `iac/environments/azure-rebuild` terminó con código 0:
  `No changes. Your infrastructure matches the configuration.` No se ejecutó
  `apply`.
- Prueba directa de solo lectura: `GET
  https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200 y
  `{"status": "ok", "service": "tangamandapio-wms"}`.
- Esto acredita disponibilidad del endpoint de salud, no un WMS real, un pedido
  originado por AWS ni conectividad privada AWS–Azure.

#### Smoke test ERP→Azure — 22:37 hora local (-05:00)

Se repitió `tests/run_live_azure_erp_smoke.py` con opt-in explícito. El artefacto
local `app/aws_release/current` creó una venta sintética de una unidad; el
outbox la entregó a la Queue y la Function completó el evento como
`demo_fulfillment_completed`. El ERP reconcilió la venta. Después, una recepción
compensatoria recorrió el mismo flujo, terminó como `demo_restock_completed` y
el test verificó que el stock ficticio volvió exactamente al baseline. Resultado
`LIVE_E2E=PASSED`. Es una integración del artefacto local con Azure; **no** se
originó desde una instancia AWS desplegada ni prueba la VPN privada.

### Validación local

Se ejecutó `tests/run_local_quality.ps1 -ValidateTerraform`:

- 74 pruebas unitarias aprobadas (API base: 28; Azure Functions: 21; release
  AWS: 25).
- Auditoría de dependencias Python y frontend: sin vulnerabilidades conocidas.
- CloudFormation validada; Terraform con formato y `validate` aprobados en los
  entornos incluidos en la compuerta.
- Build de producción del frontend aprobado.
- Guardas de seguridad de destrucción y de pruebas live aprobadas mediante
  mocks/opt-in; la compuerta no realizó operaciones cloud.
- La IaC de la VPN se endureció con una compuerta central de costo antes de
  crear el Resource Group/IPs/gateway. `terraform test -no-color` aprobó dos
  casos mock: rechazo sin aprobación y plan del gateway BGP activo-activo con
  aprobación. No se desplegó la VPN.

## Pendiente inmediato

Al corte 00:22 del 13/10 no quedó ninguna instancia temporal activa. La prueba
restauró y limpió RDS correctamente, pero no verificó la integridad lógica de
las tablas. La sonda SQL, el RTO/RPO, el despliegue permanente, la red privada
AWS–Azure y las capturas actuales de consola siguen pendientes. Dominio/HTTPS
confiable y pruebas WebRTC entre dos navegadores continúan diferidos.
