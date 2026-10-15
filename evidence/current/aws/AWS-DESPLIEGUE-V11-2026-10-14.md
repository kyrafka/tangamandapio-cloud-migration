# Intento de despliegue v11 — 14/10/2026

## Resultado vigente — 15/10/2026, 00:34 UTC

**v11 desplegado y verificado.** El perfil AWS `default` autenticó por STS en
la cuenta académica `841113066612`. CloudFormation
`tangamandapio-live-20261013` terminó `UPDATE_COMPLETE` a las 00:14:03 UTC; la
detección de drift terminó `IN_SYNC` a las 00:15:27. El release
`20261014-landing-loading-v11-python312`, SHA-256
`ef3ffe5c7ff3a20e63084ea350e060dfc11bd3bf4dd44024e4d1f0d1ad557ba3`, está
publicado en el bucket privado versionado con cifrado SSE-S3.

SSM confirmó en las dos instancias `InService` que `BUILD_REVISION` es v11,
`systemd` está activo y el health local responde 200. El ALB tiene exactamente
dos targets `healthy`; `/`, `/health` y `/ready` respondieron HTTP 200. El ASG
quedó con mínimo/deseado 2 y máximo 5, sin nodos terminando. La detección de
drift se comprobó después del cambio. RDS y la red no formaron parte del change
set; RDS sigue disponible, privada/cifrada, 20 GB, Single-AZ y un día de backup.
Las cinco alarmas CloudWatch están `OK` con acciones habilitadas. El endpoint
sigue en HTTP: dominio y HTTPS no se activaron.

La red se revalidó después del rollout: VPC `10.10.0.0/16`, dos subredes
públicas del ALB, dos privadas de aplicación con NAT y dos aisladas para RDS.
Los grupos de seguridad dejan el ingreso en cadena ALB:80→app:8080→DB:5432;
no hay acceso entrante directo a las instancias ni a PostgreSQL desde Internet.

## Historial del intento inicial v11 (superado por el resultado vigente)

El primer intento de actualizar el ASG usó `AutoScalingInstanceRefresh`, que la
SCP de AWS Academy denegó (`autoscaling:StartInstanceRefresh`). CloudFormation
lo revirtió. Se recuperó el estado estable y se reemplazó ese mecanismo por la
política nativa `AutoScalingRollingUpdate`, lote 1 y `MinInstancesInService: 2`.
El nuevo change set completó el despliegue descrito arriba. Los errores y
respuestas 503 registrados más abajo pertenecen a intentos previos, no al
estado vigente.

## Artefacto del primer intento (histórico)

## Artefacto y comprobaciones previas

- Revisión de código candidata: `20261014-landing-loading-v11-python312`.
- SHA-256: `2a83449335f28ca68d232222b7383886115460315d89699347983a8f26d5f91e`.
- Tamaño: 18,191,104 bytes.
- Objeto en bucket privado versionado: `releases/tangamandapio/portal-b2b-20261014-landing-loading-v11-python312-2a83449335f28ca68d232222b7383886115460315d89699347983a8f26d5f91e.tar.gz`.
- S3 confirmó versionado y cifrado SSE-S3; VersionId `g9CCejkNjbgr9WU54IkqMG1Rouo0vxy1`.
- `app/tests/test_app.py`: 64 pruebas aprobadas.
- `app/aws_release/current/tests`: 45 pruebas aprobadas en la puerta local
  integral más reciente.
- Empaquetado determinista: dos paquetes idénticos y hash coincidente.
- Antes de ejecutar v11, AWS CloudFormation `validate-template` aprobó la
  plantilla usada para el change set.
- La detección de drift previa terminó `IN_SYNC`.
- El change set solo modificaba recursos de capacidad/observabilidad del portal
  (ASG, Launch Template, alarma, dashboard y política de escalado); no proponía
  modificar RDS ni eliminar recursos. El ASG tenía actualización gradual,
  tamaño de lote uno y mínimo de una instancia en servicio.

## Secuencia observada

- `2026-10-14T22:24:43Z`: CloudFormation pasó a `UPDATE_IN_PROGRESS`.
- La actualización inició el reemplazo gradual con la nueva versión del
  Launch Template. El target nuevo no superó el chequeo de salud; el target
  anterior inicialmente seguía sano.
- Las solicitudes públicas a `/health` pasaron a devolver 504 y luego 503.
- AWS CLI conservó respuesta de identidad STS, pero una denegación explícita
  `voc-cancel-cred` (y restricciones SCP para varias lecturas) bloqueó
  `DescribeStacks`, eventos, inventario de Auto Scaling/EC2 y `CancelUpdateStack`.
- La consola de navegador de AWS Academy fue interrumpida con Escape; no se
  realizaron más acciones de UI en esta sesión.
- No se cambió Azure, Terraform, DNS ni HTTPS durante este intento.
- No se hizo commit ni push a GitHub. El repositorio tiene cambios del usuario
  y archivos sin seguimiento; deben revisarse y seleccionarse expresamente
  antes de sincronizar.

## Revalidación posterior y guardrail local

- Reconsulta posterior: STS autenticó la sesión de laboratorio, pero
  `DescribeStacks`, `DescribeStackEvents`, `DescribeTargetHealth` y
  `ValidateTemplate` devolvieron `AccessDenied` por `voc-cancel-cred`; el ALB
  seguía respondiendo HTTP 503.
- La pestaña de AWS Academy mostró `Lab status: stopping`; no se ejecutó una
  acción desde la consola. El estado “AWS Status: Ready” de Vocareum no
  contradice el estado de laboratorio “stopping”.
- La plantilla local se reforzó para futuras sustituciones: `AutoScalingInstanceRefresh`
  `Rolling`, `MinHealthyPercentage: 100`, `MaxHealthyPercentage: 125`, ASG
  `MaxSize: 5`, `DefaultInstanceWarmup: 420` y `BakeTime: 180`. Esto conserva
  capacidad saludable con margen para una instancia adicional. El
  change set v11 ya iniciado usó la política anterior; este refuerzo no está
  desplegado y no demuestra la causa raíz del fallo observado.
- `tests/aws/python_runtime_guard_test.sh` pasó y `cfn-lint` local aprobó la
  plantilla reforzada. La llamada AWS `ValidateTemplate` posterior fue
  denegada, así que queda pendiente validación remota tras recuperar el rol.
- La puerta integral local volvió a aprobar: 165 pruebas Python, 14 pruebas
  Node, 40 transacciones aisladas, auditoría de dependencias, build frontend,
  `cfn-lint`, y Terraform `fmt`/`validate`/tests (sin `apply`).
- Se detectó una diferencia de hash entre WSL y Git Bash causada por permisos
  de archivo del TAR. El empaquetador ahora normaliza archivos a 0644 y
  directorios a 0755; la prueba generó el mismo SHA en ambos shells:
  `ef3ffe5c7ff3a20e63084ea350e060dfc11bd3bf4dd44024e4d1f0d1ad557ba3`.
  El paquete portable se conserva localmente en `artifacts/` y todavía no se
  subió a S3. La plantilla local apunta a ese objeto/hash, pero ese valor no
  debe aplicarse hasta subirlo y verificarlo, y recuperar primero el estado del
  stack. El objeto legado `2a834...` que sí se usó en el intento v11 permanece
  en S3.

## Siguiente recuperación segura

1. Recuperar una sesión de laboratorio AWS con permiso de lectura y operación
   sobre el stack. No reutilizar credenciales expiradas ni copiar secretos a
   esta evidencia.
2. Consultar estado/eventos del stack, instancias y targets antes de cualquier
   acción. Si CloudFormation sigue actualizando, esperar su resolución; no
   ejecutar otro release en paralelo.
3. Confirmar `/health`, estado del stack y dos destinos sanos. Si el update
   terminó fallido o quedó degradado, revisar primero la causa de arranque del
   target nuevo y el rollback automático; preservar RDS y snapshots.
4. Solo después de recuperar un estado estable, volver a evaluar v11 y
   sincronizar al repositorio únicamente los cambios pertinentes, sin tokens,
   estados Terraform, temporales o artefactos sensibles.

## Revalidación de continuación — 14/10/2026, 23:20 UTC

- AWS STS volvió a autenticar el perfil local como una sesión `voclabs`; por
  tanto, esta respuesta no se explica por un token sintácticamente inválido.
- `cloudformation:ListStacks` devolvió `AccessDenied` con denegación explícita
  de la política `voc-cancel-cred`. No fue posible reconciliar el estado final
  de v11, ni confirmar rollback.
- La sonda HTTP anónima a `/health` del ALB devolvió `503`.
- La automatización del navegador se detuvo antes de actuar porque no pudo
  determinar con confianza la URL activa de Chrome. No se inició ni modificó
  el laboratorio desde la interfaz en esta continuación.
- `tests/run_local_quality.ps1 -ValidateTerraform` terminó con código 0:
  165 pruebas Python, 14 Node, 40 transacciones aisladas, auditoría de
  dependencias, build de frontend, `cfn-lint` y Terraform `fmt`/`validate`/
  tests aprobados. No ejecutó `terraform apply` ni escribió en la nube.
- El paquete portable `ef3ffe...` permanece local. No se subió otra versión a
  S3, no se hizo un despliegue nuevo y no se creó commit ni push a GitHub.

## Revalidación con token nuevo — 14/10/2026, 23:30 UTC

- Se actualizó el perfil local AWS `default` con el token temporal nuevo
  proporcionado por el usuario. `sts:GetCallerIdentity` autenticó en la cuenta
  académica `841113066612`; no se guardó ningún secreto en el repositorio ni
  se copió en esta evidencia.
- `tangamandapio-live-20261013` está en `UPDATE_ROLLBACK_FAILED`. Los eventos
  de CloudFormation del 14/10 22:27 UTC registran denegaciones explícitas de
  `voc-cancel-cred` para `ec2:CreateLaunchTemplateVersion` y
  `autoscaling:DescribeAutoScalingGroups` durante la actualización.
- El ASG `tangamandapio-asg` tiene mínimo/deseado 2, máximo 4, Launch Template
  versión 8, pero cero instancias. El target group
  `tangamandapio-tg` no tiene destinos registrados. El ALB está `active`, pero
  `http://tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com/health`
  responde HTTP 503. No se afirma disponibilidad del portal.
- La Function `tangama-wms-261008` responde `Running`, con `httpsOnly=true`;
  `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200
  y `{"status":"ok","service":"tangamandapio-wms"}`. No se aplicaron
  cambios en Azure.
- A esa hora todavía no se había ejecutado la recuperación ni publicado el
  paquete portable; el registro es histórico y queda supersedido por la sección
  siguiente.

## Revalidación final y release aplicado — 15/10/2026, 00:14–00:18 UTC

- El token temporal más reciente autenticó el perfil local `default` mediante
  `sts:GetCallerIdentity`; la identidad fue la cuenta académica
  `841113066612`. El secreto no se copió a la evidencia ni al repositorio.
- Se continuó el rollback bloqueado de la actualización anterior. El stack
  volvió a un estado estable y se publicó el artefacto v11 en el bucket privado
  versionado `tangamandapio-841113066612-us-east-1`, bajo una clave inmutable
  que incluye el SHA-256. `head-object` confirmó checksum y cifrado SSE-S3.
- El primer nuevo change set que dependía de `AutoScalingInstanceRefresh` fue
  rechazado por la SCP del laboratorio con `AccessDenied` para
  `autoscaling:StartInstanceRefresh`; CloudFormation revirtió ese intento.
  No se trató de un token inválido.
- Se cambió la política de actualización de la plantilla a
  `AutoScalingRollingUpdate` con tamaño de lote 1, pausa de estabilización de
  siete minutos y dos instancias mínimas en servicio. `cfn-lint`, la prueba de
  guardrail y `cloudformation:ValidateTemplate` aprobaron. El change set
  revisado solo contempló ASG, Launch Template, alarmas, dashboard y política
  de escalado; no incluyó RDS, VPC, grupos de seguridad ni eliminación de
  recursos.
- CloudFormation terminó `UPDATE_COMPLETE` a las 00:14:03 UTC. La última
  detección terminó `DETECTION_COMPLETE`/`IN_SYNC` a las 00:15:27 UTC, con cero
  recursos con drift.
- AWS SSM leyó ambas nuevas EC2 `InService`: `i-0b6f53128f86a9f04` y
  `i-0d88939c167b7f2d6`. Las dos reportaron la misma revisión v11, servicio
  `active` y health local `{"status":"ok"}`.
- La consulta final confirmó exactamente dos destinos `healthy`; las
  instancias retiradas ya no aparecen en el ASG. Quedó mínimo/deseado 2,
  máximo 5 y la portada, `/health` y `/ready` devolvieron HTTP 200.
- RDS se consultó sin cambios: `available`, cifrada, privada, Single-AZ,
  20 GB y retención de backup de un día. Las cinco alarmas CloudWatch quedaron
  en `OK` con acciones habilitadas.
- Azure no se modificó; su `/api/health` respondió 200 a las 00:17 UTC.
- Durante el rollout no se desplegó nada en Azure ni se tocaron datos de
  negocio. Después se ejecutó el smoke sintético sobre v11: roles 200/403,
  importación de SKU, venta `completed_demo`, recepción `received_demo`, dos
  eventos entregados, ledger demo 10→10 y 24/24 lecturas autenticadas 200
  (concurrencia 6, p95 679.98 ms por loopback dentro de EC2; no fue carga ALB).
  Véase [resultado JSON](AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json). Dominio,
  HTTPS confiable, VPN AWS–Azure, prueba visual por navegador y WebRTC entre dos
  navegadores siguen pendientes.
- La compuerta local posterior al despliegue terminó aprobada: 165 pruebas
  Python, 14 Node, 40 transacciones aisladas, build, auditoría,
  `cfn-lint` y Terraform fmt/validate/tests, sin `apply`. Véase
  [QA del 15/10](../QA-LOCAL-2026-10-15.md).
- No se ha creado commit ni se ha enviado el proyecto a GitHub en este corte;
  la copia de trabajo tiene cambios locales diversos y se debe sincronizar solo
  el conjunto revisado, excluyendo temporales y material personal.
