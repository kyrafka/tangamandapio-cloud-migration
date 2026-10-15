# Plan maestro de pruebas AWS Azure

**Actualizado:** 14/10/2026, corte de las 07:49 America/Chicago. Los estados
distinguen pruebas locales de validaciones vivas; un E2E histórico conserva su
alcance y fecha, no se presenta como ejecución actual.

AWS STS sigue devolviendo `ExpiredToken`; el último inventario del plano de
control confirmado es el corte de 06:46. Los GET de salud del ALB y pruebas de
seguridad/rendimiento anteriores son evidencia fechada, no un chequeo actual;
el POST/GET autenticado contra AWS no se repitió. En Azure, el grupo y el health
se revalidaron a las 07:16–07:18 y el plan Terraform terminó `No changes`, sin
`apply`. A las 07:43–07:44 el smoke E2E local/SQLite comprobó 401 sin key, 400
para productor no autorizado y que el probe no se persistiera; después completó
venta→Queue/Function→reconciliación→recepción compensatoria. El ledger demo
volvió a la línea base, poison count fue cero antes/después y no se leyeron
mensajes. Application Insights mostró seis respuestas 202, un rechazo 400 y
seis ejecuciones del worker `resultCode=0` para tres corridas. La compuerta
local terminó aprobada con 140 pruebas Python, 8 Node, rendimiento, build,
auditorías e IaC. Los eventos válidos quedan en auditoría Azure; no cambió
infraestructura ni se tocó AWS/RDS.
El 503 de 02:45 se conserva como histórico, supersedido por health 200.

| ID | Área | Caso | Criterio | Estado |
|---|---|---|---|---|
| PT-AWS-01 | Funcional/seguridad | GET `/health`; rutas de negocio sin sesión; POST/GET órdenes con sesión válida | Salud 200, rutas protegidas 401/403 y pedido persistido | Últimos smoke HTTP previos: `/health` 100/100 HTTP 200 y `/api/admin/users` anónimo 401. No son revalidación de este corte; el POST/GET autenticado cloud no se repitió porque AWS STS expiró. El 503 de 02:45 es histórico, supersedido. |
| PT-AWS-02 | Disponibilidad | Revisar ALB y destinos | Dos destinos healthy | Parcial: 20/20 GET secuenciales devolvieron 200 desde dos marcadores de backend, pero el plano de control sigue sin acceso (`ExpiredToken`), así que no se confirmó configuración ASG ni estado formal `Healthy` del target group. |
| PT-PERF-01 | Rendimiento | `/health` en Docker local y smoke de salud tras el ALB | p95 < 2000 ms, error ≤ 1 % | Local: 1000/1000, concurrencia 50, p95 68.34 ms, 0 errores. ALB 14/10: 100/100, concurrencia 10, p95 851.9 ms, 0 errores. Solo salud; no prueba transacciones ni autoscaling. |
| PT-AWS-03 | Datos | RDS privada y S3 cifrado | Sin acceso público; cifrado en reposo | La última lectura disponible confirmó RDS `available`, privada/cifrada, Single-AZ/backup 1 día y buckets AES256. En la revalidación 02:20 no se pudo renovar el inventario por `AccessDenied`; la restauración separada sigue documentada en PT-DR-01. |
| PT-IAC-01 | IaC | Formato/validación CloudFormation y Terraform; plan seguro | Sin errores, secretos ni reemplazos no revisados | Gate local 14/10 07:49: 140 pruebas Python + 8 Node, build, auditorías, CloudFormation y Terraform fmt/validate/mock. Azure `azure-rebuild`: plan normal `No changes` 07:18, sin `apply`. AWS sin plan vivo por `ExpiredToken`; drift no revalidado. |
| PT-MC-01 | Integración | Evento ERP→Azure Function originado desde AWS | Evento correlacionado y respuesta autenticada | Parcial: hay un E2E histórico desde EC2 (02:32), pero el más reciente (07:43) corrió desde ERP local/SQLite hacia Azure. Telemetría muestra seis solicitudes 202, un rechazo 400 y seis worker `resultCode=0` para tres corridas locales. No acredita origen AWS ni ruta privada en este corte. |
| PT-MC-02 | WMS | Function publica tarea en Queue y Blob | Evento idempotente, registro y estado | Aprobado para el ledger demo: venta y reposición compensatoria terminaron con stock restaurado. Smoke consultó poison metadata y encontró cero antes/después, sin leer mensajes. No es inventario de un WMS empresarial real. |
| PT-MC-03 | Resiliencia | Azure no disponible; outbox AWS reintenta | Pedido durable y reintento automático observable | Parcial: la prueba unitaria simuló dos timeouts, comprobó que pedido y outbox persisten, que se respeta el backoff y que el tercer intento se marca entregado. Pendiente inyectar la falla en el portal desplegado y observar recuperación real; poison queue Azure tuvo una prueba sintética separada. |
| PT-SEC-01 | Seguridad | Rutas protegidas y matriz autenticada de roles | 401/403 apropiado, privilegio mínimo, sin secretos expuestos | Matriz local de API cubre roles y rutas. En AWS la API admin anónima devuelve 401, pero `/metrics` sigue público y `/api` incluye `instance`; roles autenticados cloud siguen pendientes y v6 aún no se despliega. |
| PT-DR-01 | Recuperación | Restore privado/cifrado, marcador SQL, conteos y limpieza | RTO/RPO observados y sin temporales | Aprobado en ejecución viva repetida: marcador y 14 tablas coinciden; RTO 289 s, RPO superior observado 14 s; copia y snapshot temporales eliminados, RDS principal y snapshot fuente preservados. |
| PT-NET-01 | Red multinube privada | AWS–Azure IPsec/BGP o alternativa aprobada | Túneles/rutas privadas y tráfico entre subredes | Pendiente por permisos: el 14/10 `Describe*Vpn*` y `CreateCustomerGateway --dry-run` fueron denegados; el grupo Azure dedicado no existe. No se creó infraestructura. La integración HTTPS pública histórica no sustituye una VPN. Preflight y gates mock aprobados localmente. |
| PT-COST-01 | Costos/limpieza | Ver inventario y costo; retirar solo temporales | Sin residuos temporales; consumo comprendido | Copias temporales PT-DR-01 y la prueba VPN fueron limpiadas. Se mantienen activos los recursos principales por solicitud del usuario; coste acumulado/forecast no verificado en este corte. SNS tiene dos suscripciones confirmadas y las cinco alarmas notifican cambios de estado; no se probó envío artificial. |

Cada prueba final requiere evidencia real fechada, nube/región, configuración,
resultado esperado y observado. Las capturas Chrome/consola de inventario y
monitor Azure siguen pendientes; los registros CLI de esta revalidación no las
sustituyen.
