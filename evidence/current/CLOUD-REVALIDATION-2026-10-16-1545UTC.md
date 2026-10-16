# Revalidación AWS–Azure — 16/10/2026

**Cierre final verificado: 16/10/2026, 16:04 UTC.** El stack está en estado
normal tras apagar los componentes temporales de mayor costo.

## Release y pruebas locales

- AWS Academy `841113066612`, stack `tangamandapio-live-20261013`.
- Artefacto portal v19 `20261016-webrtc-ice-config-v19-python312`; SHA-256
  `e5ab7874feafd8f22ad2c0d631acbd3448188479616d42fbc1f7bb649c1e12d8`.
- `tests/run_local_quality.ps1 -ValidateTerraform`: aprobado, 230 pruebas
  unitarias, compilación y auditorías; CloudFormation validado, Terraform
  `fmt`/`validate` y pruebas de costo/red aprobados. Sin escrituras cloud desde
  ese gate.
- Azure Function `tangama-wms-261008`: `/api/health=200`; Terraform con
  `rebuild.tfvars.example` y `alert-recipients.local.tfvars`: `No changes`
  (sin `apply`). El worker WMS conserva su alcance de ledger sintético.

## Despliegue AWS y verificación funcional

- CloudFormation aplicó v19 y terminó `UPDATE_COMPLETE`. Se verificó
  `IN_SYNC`/0 recursos con drift tras cada actualización.
- El rolling sustituyó los dos nodos uno por uno, respetando la capacidad
  mínima 2. Los nuevos volúmenes raíz EBS conservaron `Encrypted=true`; las
  instancias entraron en SSM y el servicio web quedó activo.
- Smoke autenticado, de solo lectura, directo al ALB con SNI/certificado del
  dominio: `LIVE_ADMIN_READONLY_SMOKE_PASSED`; tres ejecuciones: antes del
  failover, después del failover y después de la reversión. En todas: 24/24
  lecturas HTTP 200, p95 182.52 ms, 248.37 ms y 260.77 ms, respectivamente;
  Comercial obtiene 200 solo en ventas y 403 en rutas restringidas; Operaciones
  obtiene 200 solo en outbox/inventario y 403 en ventas restringidas. Bandeja
  con 65/65 eventos entregados, 0 pendientes y dos suscripciones de alertas
  confirmadas.
- HTTP público respondió 301 hacia HTTPS; HTTPS público y conexión directa al
  origen ALB con verificación TLS respondieron 200 en `/health`.
- Después del rolling final, ASG/target group volvieron a 2/2 sanos y
  `/ready=200`. Todos los volúmenes raíz creados durante los rolling updates
  conservaron `Encrypted=true`.

## Pruebas temporales aprobadas

- WAF regional `tangamandapio-alb`, asociado al ALB. Reglas: AWS Managed Common,
  Known Bad Inputs y límite de 1,000 solicitudes por IP. El origen directo
  respondió 200 para `/health`; una consulta con carga XSS respondió 403 y el
  muestreo de WAF atribuyó el bloqueo a
  `AWSManagedRulesCommonRuleSet/CrossSiteScripting_QUERYARGUMENTS`.
- RDS cifrada, privada y con retención de backup de 1 día. Se habilitó Multi-AZ
  para la prueba; RDS emitió `Multi-AZ instance failover started` a las
  15:37:20 UTC y `Multi-AZ instance failover completed` a las 15:37:54 UTC.
  Después quedó `available`; `/ready` respondió 200 y el smoke autenticado
  volvió a pasar. La salida `AvailabilityZone` tardó en reflejarse; AWS indica
  que la consola puede tardar después de completar un failover.
- Se revirtió por CloudFormation a `DatabaseMultiAZ=false`, `EnableWaf=false`,
  `ManageWafAssociation=false`. El stack final está `UPDATE_COMPLETE`; RDS está
  `available`, Single-AZ, cifrada, privada y con retención de un día. No quedan
  Web ACL regionales del proyecto. Detección de drift final:
  `DETECTION_COMPLETE`, `IN_SYNC`, 0 recursos con drift.

## Estado final IaC y Azure

- Parámetros vivos CloudFormation conservan el release v19, WAF deshabilitado y
  Single-AZ. El procedimiento de despliegue validado solo prepara change sets y
  preserva parámetros sensibles; los overrides operativos están cubiertos por
  pruebas mock.
- Azure Function volvió a `/api/health=200`. Terraform 1.16.0, con los dos
  var-files locales protegidos, terminó `No changes` (exit 0); no se aplicaron
  cambios en Azure.
- Gate local integral: 230 pruebas unitarias, build, auditorías, validación de
  CloudFormation, `terraform fmt`/`validate`, pruebas de costo/red y matrices de
  acceso, todo aprobado.

## Alcance serverless

Azure Functions es la función serverless del proyecto y es un servicio válido
de Azure. No hay AWS Lambda ni API Gateway propios del proyecto; el portal AWS
usa ALB + EC2 Auto Scaling. No se deben atribuir al proyecto las Lambdas
administrativas del laboratorio Academy.
