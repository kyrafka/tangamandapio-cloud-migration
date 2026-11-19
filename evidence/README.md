# Evidencia del proyecto

Esta carpeta conserva capturas y resultados con fecha. Cada archivo acredita solo lo que describe y el entorno donde se tomó; una captura antigua no demuestra el estado actual de una nube.

## Corte vigente — 19/11/2026

El [registro operativo](../iac/ESTADO_REAL_2026-11-19.md) reúne TLS, permisos,
conmutación, respaldo, escalado y costos. Para la defensa del flujo de pedidos,
abre el [resultado del portal](current/aws/AWS-PORTAL-ORDER-TRACKING-2026-11-19.json)
y busca el mismo identificador de evento en la
[evidencia de Azure](current/azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json).
La [consulta privada de colas](current/azure/AZURE-WMS-QUEUE-STATUS-2026-11-19.json)
registra el resultado autenticado, el rechazo sin clave y los conteos.

## Corte histórico — 16/11/2026

La reconsulta de las 18:12 UTC quedó en
[`current/CLOUD-RECHECK-2026-11-16-1812.json`](current/CLOUD-RECHECK-2026-11-16-1812.json).
Confirma cuenta/rol, dos EC2 de aplicación en `us-east-2`, ausencia de ruta
`10.20.1.4/32`, RDS/ALB, ACM aún pendiente, dos suscripciones SNS sin confirmar,
presupuesto/gasto consultados y dos routers Azure encendidos. La enumeración
de EC2 fuera de `us-east-2` está bloqueada por una SCP; la salida local de
Tailscale está `NoState` y sus nombres en caché no se cuentan como routers
activos.

[`current/aws/AWS-ASG-SCALE-2-5-2026-11-16-cloud.json`](current/aws/AWS-ASG-SCALE-2-5-2026-11-16-cloud.json)
consolida la cuenta/región observada, el escalado automático 2→4→5→2, el
estado final 2/2 del ASG y destinos, las cinco alarmas y el resultado de dos
pruebas HTTP. La carga larga de 300.000 peticiones registró 1,47% de errores
(umbral 1%); el chequeo de 3.000 peticiones tuvo cero errores. La detección de
deriva de CloudFormation terminó `IN_SYNC`/0. No equivale a 3.000 usuarios ni
prueba operaciones transaccionales o tráfico privado a Azure.

El estado multinube de ese corte se describe en
[`../iac/ESTADO_REAL_2026-11-16.md`](../iac/ESTADO_REAL_2026-11-16.md). La ruta
AWS→Azure, el respaldo PostgreSQL→Blob y la confirmación de alertas siguen
pendientes; el registro de octubre que aparece abajo es evidencia histórica.

## Corte anterior — 29/10/2026

[`current/azure/AZURE-LIVE-CHECK-2026-10-29.json`](current/azure/AZURE-LIVE-CHECK-2026-10-29.json) reúne el estado HTTPS del portal, la denegación de inventario AWS, una recepción Azure Queue/Function con replay idempotente y la lectura de gateway/Storage. No contiene claves ni payload completo. El evento cambia el ledger sintético una unidad. No es evidencia de PostgreSQL cross-cloud, de login/roles, de túnel AWS→Flex ni de autoescalado.

El reintento de AWS a las 21:27 UTC está en [`current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json`](current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json). El usuario confirmó que el cambio de cuenta fue intencional: el inventario histórico pertenece a la cuenta anterior. STS autenticó en la nueva, pero cinco consultas de solo lectura recibieron denegación explícita; no se cambió la nube ni se inició una prueba desde EC2.

## Capturas versionadas

Las capturas históricas disponibles están en:

- `current/aws/screenshots/`: consola/estado operativo de AWS del 01/10/2026.
- `current/azure/screenshots/`: consultas de inventario, salud, recorrido WMS y cierre del 01/10/2026.

Son evidencia de ese corte, no un inventario vigente. No contienen claves privadas ni credenciales de laboratorio.

## Resultados automatizados

Los archivos JSON en `current/` conservan resultados de pruebas sintéticas y de carga. Revise la fecha, ruta y concurrencia antes de compararlos; una carga de lectura o de loopback no demuestra capacidad transaccional para 3,000 usuarios.

## Bitácora local

La bitácora maestra y los registros cronológicos detallados se conservan en el equipo de trabajo y no se publican en GitHub. El estado vigente resumido para el repositorio está en [README](../README.md), [IaC](../iac/README.md) y la [matriz de criterios](../core/04_matriz_rubrica.md).

## Capturas nuevas

Antes de publicar capturas de consola, revisa que no muestren sesiones, correo personal, identificadores de cuenta, direcciones IP, tokens ni datos que no deban ser públicos. La documentación no convierte una observación visual en una validación de servicio.
