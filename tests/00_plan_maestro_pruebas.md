# Plan maestro de pruebas AWS–Azure

**Corte vigente:** 16/10/2026, 06:10 UTC. Los antecedentes conservan su fecha;
una prueba histórica no sustituye una revalidación cuando hubo cambios.

## Estado actual

- Antes del último cambio de credenciales, AWS Academy autenticó en `default`
  (cuenta `841113066612`); CloudFormation seguía `UPDATE_COMPLETE` y una
  detección fresca terminó `IN_SYNC` a las 05:00:46 UTC. El token nuevo
  compartido después fue rechazado por STS (`InvalidClientTokenId`), así que la
  CLI no puede hacer una relectura adicional en este corte. Una nueva llamada
  STS aislada con el último token también fue rechazada; no se guardó y no se
  modificaron recursos.
- La verificación pública más reciente (05:44–05:58 UTC) cambia el estado
  operativo: dominio HTTPS con TLS válido, pero `/` y `/health` responden 503.
  El ALB directo confirma 503 en 443 y 301 en 80→443. Por eso el estado 2/2 de
  instancias y destinos sanos que sigue corresponde a la última lectura
  autenticada de 05:00, no a una condición vigente confirmada. El estado del
  ASG/target group y la causa del 503 quedan pendientes de lectura con credencial
  aceptada. Detalle:
  [corte de disponibilidad 05:58](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0547UTC.md).
- La última lectura AWS autenticada (05:00 UTC) vio ACM `ISSUED` hasta
  30/04/2027, ASG deseado/mínimo 2, máximo 5 y 2/2 instancias/destinos sanos.
  Ese inventario es histórico frente al 503 observado después; no demuestra
  salud actual del target group.
- A las 05:02:29 UTC el dominio HTTPS `/health` devolvió `200`; la respuesta
  pública mostró HSTS. La última lectura AWS autenticada verificó HTTP→HTTPS
  (`301`). Azure CLI reporta el grupo `Succeeded` y la Function `Running` /
  HTTPS-only; GET `/api/health` devolvió 200 con TLS verificado. HEAD dio 404
  en el corte 05:09; se corrigió y publicó a las 05:15. A las 05:18 GET y HEAD
  devolvieron 200 con TLS verificado y HEAD sin cuerpo. Terraform posterior:
  `No changes`.
- A las 05:37 UTC pasó de nuevo el E2E compensado ERP local→Azure después del
  despliegue de health: guardas 401/400, venta/reposición sintéticas,
  reconciliación ERP y saldo ficticio de vuelta a la línea base; poison count
  cero antes/después. Application Insights reportó dos ejecuciones correctas
  del worker y cero fallidas en la ventana de 20 minutos (conteo agregado).
  No fue tráfico originado desde EC2/RDS.
- Entre 05:45 y 05:47 UTC se repitió el E2E local→Azure: Function `Running`,
  salud 200, guardas 401/400, venta y reposición demo completadas, saldo
  restaurado y poison count cero antes/después. Los eventos quedan en auditoría
  Azure; la prueba no usó EC2 ni RDS.
- A las 05:57 UTC, el plan Terraform de `azure-rebuild` consultó el backend
  remoto y terminó `No changes`; no se ejecutó `apply`. AWS no se pudo planear
  ni consultar por el rechazo de STS.
- A las 06:00 UTC, ARM enumeró diez recursos en el grupo de reconstrucción
  Azure: Function, plan, Storage, Key Vault, Log Analytics, Application
  Insights, dos alertas métricas y dos Action Groups.
- A las 06:04 UTC, AWS STS rechazó el token recién proporcionado
  (`InvalidClientTokenId`); no se actualizó el perfil local ni se mutó AWS.
- A las 06:09 UTC, el E2E compensado local→Azure volvió a pasar: outbox
  entregado, venta `demo_fulfillment_completed`, recepción
  `demo_restock_completed`, ledger ficticio restaurado, salida 0. IDs de
  auditoría `evt-0cf05101ca0942a09ff51610ba99ab4c` y
  `evt-795a36230f7843c7978b675dbae3d58d`. No es origen EC2/RDS.
- La sonda de las 06:10 UTC devolvió HTTP 503 para el health público del portal
  (Cloudflare) y HTTP 200 para la Function Azure.
- La puerta integral local a las 05:37 aprobó 216 pruebas Python, 14 Node,
  build/auditorías, CloudFormation y Terraform `fmt`/`validate`, sin mutaciones
  cloud.
- El E2E desplegado AWS→Azure completó venta/compra sintéticas y dejó el saldo
  demo 10→10; el outbox quedó 51/51 entregado, cero pendiente. La prueba Admin
  de solo lectura ejecutó 24 GET autenticados, concurrencia 6, p95 217.69 ms;
  los permisos API Comercial/Operaciones dieron los 200/403 esperados.
- RDS sigue disponible, cifrada y privada, Single-AZ con un día de backup.
  PT-DR-01 pasó en esta sesión: restore aislado, RTO 289 s, RPO observado ≤10 s,
  marcador verificado y recursos temporales limpiados. Failover/Multi-AZ no se
  probó.
- En la consulta de 04:24 UTC, las cinco alarmas estaban `OK`. La alarma de
  5xx no recibió datapoints y los faltantes cuentan como `NonBreaching`, así que
  su estado no demuestra que haya observado tráfico. El ciclo sintético de SNS
  y recepción/recuperación ya pasó el 14/10.
- Pruebas sintéticas históricas demostraron scale-out e in 2↔3; falta carga
  transaccional medida a través del ALB. No se afirma capacidad para 3,000
  usuarios.
- La prueba Admin de solo lectura ejecutó 24 GET autenticados al origen ALB con
  concurrencia 6: 24/24 HTTP 200, p95 217.69 ms. Es un smoke pequeño, no un
  benchmark de capacidad ni una prueba de 3,000 usuarios.
- En una sonda reciente, Python `urllib` recibió 403 de Cloudflare (3/3; la
  corrida anterior fue 25/25), mientras `curl` e `Invoke-WebRequest` al mismo
  health recibieron 200. No se cambió ni se sorteó la regla del proxy. La
  métrica de latencia de esas respuestas 403 no representa rendimiento del
  origen.
- WAF regional no está desplegado. No existe ruta privada AWS–Azure: AWS
  Academy denegó Customer Gateway por SCP y no hay VNet Azure del proyecto.
- El template local CloudFormation usa defaults v18 y los parámetros efectivos
  del stack también son v18; el template guardado en AWS conserva tres defaults
  de artefacto v16. La comparación no encontró diferencias de recursos; no se
  forzó una actualización vacía. Terraform está validado localmente, sin `apply`.
- La evidencia agregada de Azure consultada mostró 4 recepciones 202 y 4
  ejecuciones correctas de la Function (`resultCode=0`) en una hora; un 400
  esperado por origen inválido y ningún fallo observado en esos eventos. El
  poison queue quedó en cero por consulta de metadatos, sin leer ni eliminar
  mensajes. No se correlacionaron los conteos con IDs de evento ni se disparó
  una alarma por métrica real.
- El control de Chrome se detuvo con Escape durante la recuperación de AWS
  Academy; no hay recorrido visual nuevo de módulos/CSV en este corte. WebRTC
  entre dos navegadores tampoco está probado recientemente.
- La revisión de rúbrica sigue ambigua: la hoja del proyecto suma 18.5 aunque
  declara 20; el PDF general es otro instrumento con máximos que suman 90. No
  se combinan las escalas ni se inventa una nota.
- La compuerta local recién repetida pasó 215 pruebas unitarias, 14 Node,
  frontend/build, auditorías, CloudFormation, Terraform y cinco pruebas mock;
  no aplicó cambios cloud. GitHub Actions para `b1d36a9` también pasó sus tres
  trabajos (run `38851449937`).

## Matriz de pruebas

| ID | Prueba | Estado verificado | Qué falta |
|---|---|---|---|
| PT-HTTPS-01 | Dominio, TLS y redirect | HTTPS `/health` 200; respuesta con HSTS; última lectura confirmó redirect HTTP→HTTPS | Captura actual de Chrome/ACM cuando se reanude el navegador. |
| PT-AWS-01 | Salud y disponibilidad | Stack `UPDATE_COMPLETE`/`IN_SYNC` a las 05:00 UTC; última lectura autenticada ALB y ASG 2/2 sanos | Renovar credenciales válidas para nueva inspección CLI y captura de consola/inventario. |
| PT-AWS-02 | Login y roles | API Admin, Comercial y Operaciones pasó 200/403 por TLS | Recorrido visual autenticado completo. |
| PT-WMS-01 | ERP→AWS→Azure→ledger sintético | E2E desplegado por SSM/ALB/Azure; venta y compra sintéticas, ledger 10→10 | Repetición visual del flujo desde el portal. |
| PT-OUTBOX-01 | Historial paginado | 51/51 eventos entregados leídos sin omisiones, cero pendientes | Comprobar tabla y paginación en recorrido visual. |
| PT-RETRY-01 | Reintento y poison | Guards y metadata poison probados en Azure; outbox durable | Falla controlada y recuperación observada en el portal desplegado, sin borrar evidencia. |
| PT-DR-01 | Backup/restore/failover | Restore aislado: RTO 289 s, RPO observado ≤10 s; marcador y limpieza verificados | Failover Multi-AZ no probado; origen Single-AZ y backup de un día. |
| PT-NET-01 | Red privada AWS–Azure | E2E usa HTTPS público | VNet/ruta privada ausente; SCP bloquea Customer Gateway en AWS Academy. |
| PT-PERF-01 | Carga y escalado | Escalado sintético 2↔3 histórico; 24 GET al origen ALB, concurrencia 6, 24/24 HTTP 200, p95 217.69 ms | Carga sostenida y representativa, medir escalado/capacidad; no se afirma soportar 3,000 usuarios. |
| PT-SEC-01 | Seguridad y navegador | TLS, controles de rol por API; SNS y auditoría existentes | WAF ausente; validar vistas/CSV visualmente; no atribuir el 403 a la app sin origen confirmado. |
| PT-AZ-MON-01 | Invocaciones y alertas | E2E 05:37 y App Insights: 2 workers `resultCode=0`, 0 fallidos agregado; poison metadata=0 | Captura actual de monitor e invocación, correlación directa por ID y alarma de métrica real. |
| PT-IAC-01 | CloudFormation/Terraform | Validación local; detección fresca de drift `IN_SYNC` a las 05:00:46 UTC | Reconciliar defaults de artefacto v16/v18 en el siguiente cambio efectivo; no desplegar un cambio vacío. |
| PT-APP-01 | CSV, correo y finanzas | Módulos con datos sintéticos y mensajería interna portal-only | CSV e interacción ERP en navegador; SMTP externo no forma parte del correo portal-only. |
| PT-RTC-01 | WebRTC | Controles mute/cámara implementados | Prueba de audio/video bidireccional entre dos navegadores. |
| PT-COST-01 | Costos | AWS con créditos Academy que compensan el consumo medido | Importe Azure fiable y atribución por proyecto. |
| PT-DOC-01 | Evidencia/entrega | 216 pruebas Python, 14 Node, CloudFormation/Terraform y E2E Azure documentados; CI `b1d36a9` es un corte anterior | Capturas recientes del inventario AWS y monitor Azure; estado CI del commit nuevo y defensa oral. |

## Secuencia de cierre

1. Si la sonda Python a través de Cloudflare sigue siendo necesaria, revisar la
   regla del proxy con su administrador; el test al origen ALB ya separa el
   rendimiento de la app del 403 del proxy. No desactivar controles a ciegas.
2. Completar recorrido Chrome de roles, módulos ERP y carga CSV cuando el control
   de ventana pueda identificar la URL activa.
3. Definir objetivo de capacidad y correr carga sostenida de bajo impacto por
   ALB con datos sintéticos, límites aprobados, reconciliación y limpieza
   documentada; observar el escalado gradualmente.
4. Reconciliar template local/deployed en la próxima actualización CloudFormation
   efectiva y generar change set; revisar cada reemplazo antes de ejecutarlo.
5. Revisar costo/permiso antes de Multi-AZ, WAF o VPN; no crear rutas privadas si
   la SCP/ausencia de VNet sigue bloqueando el diseño.
6. Capturar evidencia AWS/Azure, terminar prueba WebRTC si sigue en el alcance y
   pedir al docente aclaración de rúbrica/ponderación.

La validación E2E, recuperación, HTTPS y estado de Function de este corte se registra en
[`CLOUD-E2E-DR-2026-10-16-0500UTC.md`](../evidence/current/CLOUD-E2E-DR-2026-10-16-0500UTC.md).
La corrección de la sonda y su validación viva se registra en
[`AZURE-HEALTH-HEAD-DEPLOY-2026-10-16-0519UTC.md`](../evidence/current/azure/AZURE-HEALTH-HEAD-DEPLOY-2026-10-16-0519UTC.md).
La puerta local y el E2E compensado posteriores están en
[`QA-LOCAL-2026-10-16-0537UTC.md`](../evidence/current/QA-LOCAL-2026-10-16-0537UTC.md) y
[`AZURE-ERP-E2E-2026-10-16-0537UTC.md`](../evidence/current/azure/AZURE-ERP-E2E-2026-10-16-0537UTC.md).
La revalidación previa y el smoke de lectura siguen en
[`CLOUD-REVALIDATION-2026-10-16-0400UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0400UTC.md).
El smoke autenticado y la sonda de lectura del 16/10 se registran en
[`AWS-READONLY-LOAD-2026-10-16-0424UTC.md`](../evidence/current/aws/AWS-READONLY-LOAD-2026-10-16-0424UTC.md).
