# Revisión visual del proyecto en Google Chrome — 08/10/2026

Esta nota concilia la documentación previa con las comprobaciones realizadas en
Chrome el 8 de octubre. El inventario AWS y la prueba Azure se verificaron en
vivo; se distinguen los estados de infraestructura de la evidencia funcional.
El mapa posterior de las 19:48 CDT está en
[MAPA_ESTADO_ACTUAL_2026-10-08.md](MAPA_ESTADO_ACTUAL_2026-10-08.md) y prevalece
para el inventario vivo; esta revisión conserva el corte visual anterior.

## Observaciones

| Superficie revisada | Observación visible | Qué permite afirmar | Qué no demuestra |
|---|---|---|---|
| Portal público de Tangamandapio en AWS | Cargó la portada y el panel de acceso desde el ALB. | La interfaz web respondió en el hostname en el momento de la revisión. | No demuestra por sí solo login ni que el certificado del hostname sea de confianza. |
| AWS Academy Learner Lab | Se inició el laboratorio; la interfaz mostró **Ready** y aproximadamente 3 h 58 min disponibles. | El entorno temporal quedó disponible para consultar recursos. | El tiempo de laboratorio no es una medición del costo final de AWS. |
| AWS CloudFormation — `tangamandapio-live-20261005` | Estado `UPDATE_COMPLETE`; panel Recursos mostró **51 recursos**. Incluye VPC/subredes, rutas/NAT/IGW, ALB y listeners, ASG/Launch Template, RDS, S3, WAF, Secrets Manager, Backup, CloudWatch (dashboard/logs/alarms) y SNS. | La consola sí cargó el inventario real del stack en `us-east-1`; los estados visibles de recursos fueron `CREATE_COMPLETE` o `UPDATE_COMPLETE`. | `UPDATE_COMPLETE` no implica por sí solo que cada servicio de aplicación esté sano; se contrastó con el target group. |
| AWS EC2 — target group `tangamandapio-tg` | **2 destinos registrados, 2 Healthy, 0 Anómalo**, HTTP:8080, repartidos en `us-east-1a` y `us-east-1b`. | Los dos nodos web estaban aprobando la comprobación de salud del ALB. | No sustituye una prueba de carga ni verifica por sí solo todas las operaciones de la aplicación. |
| CloudFormation — `tangamandapio-voice-recordings` | Estado `CREATE_COMPLETE`. | La pila separada para almacenamiento de grabaciones existe en la cuenta del laboratorio. | No se verificó aquí que contenga grabaciones ni el ciclo de una llamada real. |
| Azure Portal — Function App `tangama-wms-fn` | Vista general: **En ejecución**, Linux, West US, Consumption `Y1`, cuatro funciones habilitadas: `fulfillment_status`, `health`, `process_fulfillment_message` y `receive_fulfillment_event`. | Se confirmó la app y su inventario de funciones desde el portal. | “En ejecución” no demuestra procesamiento; por eso se ejecutó además el flujo sintético descrito abajo. |
| Azure — prueba sintética de `receive_fulfillment_event` | El POST de `evt-20261008-liveprobe-01` devolvió **HTTP 202 Accepted**, `status=queued`; los registros de ejecución mostraron `queued_event` y ejecución exitosa. | El endpoint recibió y puso en cola el evento de prueba. | El flujo es de demostración y no afecta inventario real. |
| Azure — monitor de `process_fulfillment_message` y consulta de estado | Application Insights/Invocaciones mostró el worker ejecutado a las **09:10:18**, `Succeeded`, ~93 ms, `DequeueCount: 1`; el log identificó `simulated_fulfillment_completed` para el mismo evento. `fulfillment_status` devolvió **HTTP 200**, `simulated_completed`, `mode=demo-only`. | Se comprobó que el mensaje recorrió la cola, fue procesado y pudo consultarse después. | No representa despacho ni cambio de existencias reales. El monitor también mostraba **9 éxitos y 5 errores** en 30 días; un error inspeccionado era un mensaje anterior con checksum del Blob distinto al de la cola, reintentado hasta `DequeueCount: 5`. Se dejó intacto para no borrar evidencia/mensajes. |

## Integridad y privacidad

- No se abrieron ni revelaron valores de configuración, claves, tokens o
  cadenas de conexión. La vista de configuración de Azure se dejó sin cambiar.
- La vista general de Azure contiene datos de cuenta/suscripción en el encabezado
  y el panel de resumen. No se incorpora una captura sin anonimizar.
- Se tomó una captura real del portal desde Chrome durante la revisión, pero el
  mecanismo de esta sesión solo la expuso como imagen temporal y no ofreció una
  ruta aprobada para archivarla en el repositorio. Un intento de abrirla como
  `data:` fue rechazado por la política del navegador; no se intentó eludir esa
  restricción. Por tanto **no se marca como PNG archivado**.
- Los nombres de archivo sugeridos para las capturas reales nuevas se encuentran
  en [CAPTURAS_PENDIENTES.md](CAPTURAS_PENDIENTES.md). Las imágenes existentes
  descritas como “registro visual” o “tarjeta visual” no son capturas crudas de
  Chrome/terminal; se clasifican por su origen en [../README.md](../README.md).

## Conclusión de corte

El stack AWS está presente en CloudFormation y sus dos destinos del ALB están
`Healthy`. Azure no solo aparece en ejecución: el evento sintético fue aceptado,
consumido por Queue y consultado como `simulated_completed`. Queda una deuda de
observabilidad/limpieza: cinco fallos históricos en el monitor; el mensaje
inspeccionado corresponde a una discrepancia Blob/checksum anterior. No se
eliminó ni alteró. El WMS sigue siendo una simulación académica, no un sistema de
inventario real.

Las capturas visibles en Chrome no quedaron archivadas como PNG en el
repositorio; por tanto no se presenta ninguna imagen histórica como captura
nueva. La lista de capturas directas aún pendientes está en
[CAPTURAS_PENDIENTES.md](CAPTURAS_PENDIENTES.md).
