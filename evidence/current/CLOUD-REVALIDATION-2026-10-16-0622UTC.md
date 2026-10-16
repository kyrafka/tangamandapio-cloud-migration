# Revalidación AWS — 16/10/2026, 06:13–06:22 UTC

## Estado observado

- El perfil local `default` quedó actualizado con las credenciales temporales
  entregadas por el usuario. STS las aceptó y devolvió la cuenta académica
  `841113066612` / rol `voclabs`. No se imprimieron ni copiaron secretos a la
  evidencia.
- CloudFormation `tangamandapio-live-20261013` reporta
  `UPDATE_COMPLETE`; su último cambio fue a las 00:27:59 UTC. El campo de drift
  reporta `IN_SYNC` (el timestamp de una detección nueva no se consultó en este
  corte).
- El ALB `tangamandapio-alb` está `active`, internet-facing, con DNS
  `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com`. A las 06:22 UTC,
  `https://tangamandapio.kendellnm.me/health` respondió HTTP 503 desde
  Cloudflare.
- ASG `tangamandapio-asg`: mínimo 2, deseado 2, máximo 5; **cero instancias**.
  El target group `tangamandapio-tg` tiene **cero destinos registrados**.
- Las actividades más recientes consultadas ocurrieron a las 06:07:18–06:07:20
  UTC: Auto Scaling pidió una instancia en cada una de las AZ `us-east-1a` y
  `us-east-1b`, pero ambas acabaron `terminated` con
  `Client.InternalError: Client error on launch`. CloudTrail registra
  `RunInstances` sin `errorCode` y las instancias llegaron a `pending`; la
  consulta posterior de su estado confirma la terminación. La salida de consola
  no estaba disponible y las comprobaciones de instancia quedaron
  `not-applicable`.
- **La causa raíz aún no está identificada.** Las lecturas no bastan para
  justificar un cambio de AMI, plantilla, permisos o red. No se hicieron
  mutaciones en AWS en esta revisión.
- RDS `tangamandapio-postgres` está `available`, cifrada, privada, Single-AZ y
  con retención de backup de 1 día.

## Interpretación y siguiente paso

Las credenciales funcionan; la indisponibilidad ya no se explica por STS. El
503 se explica inmediatamente por la ausencia de destinos en el target group,
pero **no** por qué falla el aprovisionamiento EC2. Mantener el portal como no
operativo. Antes de desplegar cambios, inspeccionar el motivo EC2/ASG a nivel de
cuenta/lab y los eventos de aprovisionamiento disponibles en la consola; después
corregir únicamente la causa confirmada y verificar dos nodos `InService`, dos
targets `healthy`, `/health` 200 y login/roles por el ALB.

Azure no se revalidó en esta ventana: la última prueba registrada fue el
16/10, 06:09–06:10 UTC (E2E local→Azure aprobado con ledger sintético
restaurado; health HTTP 200). Ese flujo no se originó desde EC2/RDS ni demuestra
la disponibilidad del portal AWS o una ruta privada AWS–Azure. El plan Terraform
remoto de Azure de las 05:57 UTC fue `No changes`, sin `apply`.
