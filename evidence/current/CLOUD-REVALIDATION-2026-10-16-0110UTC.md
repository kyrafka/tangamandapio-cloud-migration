# Revalidación post-v18 — 16/10/2026, 01:10 UTC

Este corte supersede el estado de salud del informe 01:05 UTC; la causa del
503 de AWS continúa sin diagnóstico por falta de permiso de lectura.

## Dominio y AWS

El dominio negocia TLS correctamente y HTTP redirige a HTTPS con `301`. A las
01:02 UTC la portada, `/health`, `/ready` y `/platform` respondieron `503` por
HTTPS. El portal no está operativo aunque el certificado y el redirect sí lo
están.

AWS STS autenticó en la cuenta Academy `841113066612`, pero
`cloudformation:DescribeStacks` devolvió `AccessDenied` por el explicit deny
`voc-cancel-cred`. No se pudo confirmar target health, ASG, RDS ni drift y no se
intentó sortear la política. CloudFormation había completado la actualización
v18 a las 00:42:53 UTC; una comprobación posterior del origen ALB mostró 503. No
se modificó infraestructura durante esta revalidación.

## Azure: Function, procesamiento y alertas

La Function `tangama-wms-261008` figura `Running`, `httpsOnly=true`, en West US;
`/api/health` devolvió `200`. El E2E sintético local→Azure comprobó las guardas
`401` sin clave y `400` para productor no autorizado (sin persistir esos probes),
una venta `demo_fulfillment_completed` y una recepción compensatoria
`demo_restock_completed`. El ledger ficticio regresó exactamente a su saldo
inicial. Poison count fue 0 antes y después; se consultó solo metadato, sin leer
ni eliminar mensajes. Los dos eventos válidos permanecen en auditoría Blob.

Application Insights, consulta agregada de las 24 horas previas, mostró 22
solicitudes: 2 eventos aceptados `202`, 2 ejecuciones de
`process_fulfillment_message` con `resultCode=0`, 1 rechazo `400` esperado de la
prueba de origen no autorizado y 0 respuestas `5xx`. También hubo consultas de
salud/estado e inventario demo. Esto acredita procesamiento de la Function y
telemetría Azure; el productor fue una app local con SQLite temporal, no AWS/RDS.

Las alertas métricas `tangama-wms-fn-5xx` y `tangama-wms-fn-latency` están
habilitadas y enlazadas al Action Group `tangama-ops-ag`: `Http5xx > 0` (severity
2) y `HttpResponseTime` promedio `> 5` (severity 3). El usuario había confirmado
la recepción de alerta y recuperación en una prueba previa; no se provocó un
nuevo incidente artificial en este corte.

El flujo WMS es una simulación académica funcional, no inventario físico. Los
eventos válidos de prueba quedan en el log de auditoría Azure.

## Pruebas locales y sincronización

La puerta local aprobó 209 pruebas, frontend/build, CloudFormation, validación
Terraform, mocks de red y auditoría de dependencias. El commit
`e936c332073b31c709f5c1067a06b582812842f9` sincronizó la matriz, plan maestro y
el corte previo con GitHub; la ejecución de Actions terminó `success` a las
01:08:59 UTC.
El presente corte agrega telemetría Azure y está pendiente de su propia corrida
de Actions después de publicarse. Estas verificaciones no sustituyen
el smoke AWS autenticado de v18.

## Pendientes

1. Restaurar permiso legítimo de lectura AWS y diagnosticar el 503 consultando
   target group, ASG y registros; no desplegar a ciegas.
2. Con el portal sano, repetir login, Admin/Comercial/Operaciones, transacciones
   sintéticas, reconciliación AWS→Azure y las dos páginas del outbox v18 (30+15).
3. Revisar drift AWS/Terraform; RDS sigue documentado Single-AZ con backup de un
   día. Hay restore aislado previo con RTO/RPO observados, no failover probado.
4. Desplegar/validar conectividad privada AWS–Azure solo con permisos, costo y
   configuración revisados. HTTPS público no sustituye una VPN/ruta privada.
5. Ejecutar prueba representativa de carga/autoscaling, guardar evidencias
   visuales de AWS/Azure, importar CSV desde navegador y completar las pruebas
   WebRTC/consentimiento, SMTP externo si permanece en alcance, y costos reales.

La matriz de criterios está en
[`core/04_matriz_rubrica.md`](../../core/04_matriz_rubrica.md) y el plan
operativo en [`tests/00_plan_maestro_pruebas.md`](../../tests/00_plan_maestro_pruebas.md).
