# Checklist de capturas vigentes

**Regla de integridad:** guardar cada imagen con el identificador indicado dentro de la carpeta de la nube correspondiente. No usar una imagen de `legacy/andemarket-historical` como si fuera evidencia de Tangamandapio. No mostrar cuentas, claves de Function, tokens, URLs firmadas ni credenciales.

## Corte de evidencias — 08/10/2026

El inventario más reciente está en [MAPA_ESTADO_ACTUAL_2026-10-08.md](MAPA_ESTADO_ACTUAL_2026-10-08.md) (19:48 CDT). Este archivo es un índice de capturas pendientes, no una fuente independiente de conteos cloud. Las verificaciones visuales anteriores se conservan como cortes históricos.

La consola AWS se abrió en Chrome y se vieron el stack y el target group; Azure mostró la Function y ejecuciones en Application Insights. Las imágenes de esa sesión se mostraron en conversación, pero no se archivaron como PNG crudos. Por eso las capturas directas de inventario AWS y monitor Azure siguen pendientes, con encabezados de identidad ocultos.

Las capturas crudas actuales de inventario AWS y monitor Azure siguen pendientes
de exportarse desde el portal, con encabezados de cuenta/identidad ocultos. Las
imágenes históricas más abajo no sustituyen esta captura.

## Corte visual previo en Chrome — 08/10/2026 (supersedido)

La revisión actualizada está en
[REVISION_CHROME_2026-10-08.md](REVISION_CHROME_2026-10-08.md). En esta sesión
sí se vio el inventario real AWS (51 recursos, `UPDATE_COMPLETE`, dos destinos
`Healthy`) y se probó el flujo Azure con un evento sintético hasta
`simulated_completed`. Las observaciones quedaron en Markdown; **no se archivó
ningún PNG nuevo**. No presentar las capturas históricas como si fueran de este
ciclo.

Pendiente capturar desde Chrome y guardar manualmente con encabezados/IDs
personales ocultos:

| Archivo sugerido | Vista necesaria | Alcance de la prueba |
|---|---|---|
| `evidence/current/aws/screenshots/CUR-CHROME-AWS-01_portal_login_2026-10-08.png` | Portada del portal en el ALB. | Solo disponibilidad de la interfaz. No demuestra login ni salud del stack. |
| `evidence/current/aws/screenshots/CUR-CHROME-AWS-02_inventario_2026-10-08.png` | CloudFormation con Recursos (51) y `UPDATE_COMPLETE`; complementar con target group. | Captura nueva pendiente: ocultar encabezado con IDs de cuenta/usuario. La consola sí cargó; el archivo PNG no quedó guardado. |
| `evidence/current/azure/screenshots/CUR-CHROME-AZ-01_function_overview_2026-10-08.png` | Información general de `tangama-wms-fn` y lista de funciones. | Captura directa; ocultar cuenta, suscripción y datos personales. |
| `evidence/current/azure/screenshots/CUR-CHROME-AZ-02_monitoring_2026-10-08.png` | Invocaciones del worker y detalle de la ejecución sintética, sin IDs personales. | Captura nueva pendiente; el registro Markdown confirma la prueba y el panel muestra además fallos históricos que deben conservarse para diagnóstico. |

## AWS — estado histórico y ciclo actual

El 02/10/2026 se cerró un ciclo temporal; esa nota histórica ya no describe el
estado observado el 08/10/2026. El laboratorio fue iniciado de nuevo y la
consola mostró `tangamandapio-live-20261005` (`UPDATE_COMPLETE`, 51 recursos),
además de la pila `tangamandapio-voice-recordings` (`CREATE_COMPLETE`). En el
target group del ALB se vieron dos destinos `Healthy` y cero anómalos. El lab
quedó activo con tiempo limitado, por lo que estos recursos pueden consumir el
presupuesto mientras continúen levantados.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AWS-03_laboratorio_y_region.png` | Sesión temporal de AWS Academy y región `us-east-1`. | Sesión autenticada usada para el despliegue vigente. |
| `CUR-AWS-04_inventario_inicial.png` | Inventario previo a Tangamandapio (VPC, EC2, ALB, RDS y stacks). | Partida limpia; identificadores de cuenta ocultos. |
| `CUR-AWS-05_cloudformation_validate.png` | `aws cloudformation validate-template` sobre `iac/cloudformation/aws-lab.yaml`. | Plantilla de Tangamandapio validada antes de crear recursos. |
| `CUR-AWS-06_stack_operativo_2026-10-01.png` | Captura histórica del stack anterior. | No es evidencia del ciclo actual; tarjeta resumen CLI, no screenshot crudo. |
| `CUR-CHROME-AWS-02_inventario_2026-10-08.png` | CloudFormation del stack actual y Recursos (51), sin encabezado identificable. | Captura real pendiente de archivar. Estado comprobado en `REVISION_CHROME_2026-10-08.md`. |
| `CUR-CHROME-AWS-03_targets_healthy_2026-10-08.png` | Target group del ALB actual, mostrando 2 `Healthy` y 0 anómalos; ocultar cuenta. | Captura real pendiente de archivar. |
| `CUR-AWS-07_salud_infraestructura.png` | ALB, RDS, S3 Public Access Block y CloudWatch. | Dos targets `healthy`; RDS privada/cifrada; cuatro bloqueos S3 en `true`; alarmas y dashboard disponibles. |
| `CUR-AWS-08_prueba_funcional_2026-10-01.png` | Portal B2B y prueba `GET /health`, `POST /api/orders`, `GET /api/orders`. | HTTP `200`, `201`, `200`; pedido persistido desde PostgreSQL. |
| `CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md` | Registro técnico de la publicación B2B, rollback controlado y actualización final. | `UPDATE_COMPLETE`; `/health` 200 durante el recambio. No sustituye las capturas del siguiente ciclo. |
| `CUR-AWS-09_cierre_y_costo_cero.png` | Tras la autorización de borrado: stack inexistente y laboratorio terminado. | No quedan ALB, NAT, EC2, RDS, S3 ni stack de Tangamandapio ejecutándose. |

### Orden seguro AWS (para conservar evidencia)

1. Capturar ahora CloudFormation/Recursos, el target group y el estado RDS con IDs personales ocultos; no reutilizar las imágenes antiguas.
2. Completar pruebas funcionales por separado si se necesitan para el informe; no inferirlas del estado de la pila.
3. Cualquier apagado o eliminación del laboratorio es un paso separado: comprobar antes qué recursos se perderán y guardar evidencia sin claves.

## Azure — estado actual y evidencia histórica

El grupo actual de la Function App `tangama-wms-fn` está en West US y la app
aparece `En ejecución` en plan Consumption Linux. La lista del portal tiene 4
funciones habilitadas. La prueba del 08/10 aceptó un evento sintético (`202`),
el worker `process_fulfillment_message` lo consumió con éxito (`93 ms`) y la
consulta devolvió `simulated_completed` (`200`). El WMS continúa siendo de
demostración y no cambia stock real. Las capturas históricas de un grupo
eliminado se conservan solo como antecedentes, no como inventario vigente.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AZ-04_terraform_apply.png` | Terraform con `fmt`, `validate` y `apply` del vertical WMS temporal. | Recursos del grupo, sin secretos ni nombres de cuenta. |
| `CUR-AZ-05_inventario_cli_2026-10-01.png` | Consulta Azure CLI autenticada con Function, Storage, Key Vault, Application Insights y Log Analytics. | Guardada: inventario real actual del vertical Azure. |
| `CUR-AZ-06_health_cli_2026-10-01.png` | Prueba autenticada de `HttpHealth` y CORS limitado al portal. | Guardada: HTTP `200` y `status=ok`. |
| `CUR-AZ-07_wms_end_to_end_2026-10-01.png` | Evento WMS aceptado y verificación de Blob privado más mensaje de Queue. | Flujo idempotente exitoso; no imprimir claves de Function. |
| `CUR-AZ-08_cierre_inventario_cero_2026-10-01.png` | Azure CLI tras eliminar ambos grupos temporales. | Completada: inventario cero y control de costos Azure cerrado. |
| `AZ-PORTAL-01_inventario_2026-10-01.png` | Grupo de recursos vigente con Storage, Key Vault, Log Analytics, Application Insights, Function App y plan. | Siete recursos, región West US. |
| `AZ-PORTAL-02_function_operativa_2026-10-01.png` | Function App en ejecución; dos funciones HTTP habilitadas. | Runtime v4, Linux, `HttpHealth` y `HttpFulfillment`. |
| `AZ-PORTAL-03_health_200_2026-10-01.png` | Panel "Prueba/ejecución" de `HttpHealth`. | HTTP `200 De acuerdo`, `status=ok`. |
| `AZ-PORTAL-04_fulfillment_202_2026-10-01.png` | Panel "Prueba/ejecución" y registros de `HttpFulfillment`. | HTTP `202 Aceptado`; Blob `201`, Queue `201` y ejecución `Succeeded`. |
| `CUR-CHROME-AZ-01_function_overview_2026-10-08.png` | Vista general de Function App con cuatro funciones habilitadas. | Captura directa pendiente; ocultar cuenta, suscripción y datos personales. |
| `CUR-CHROME-AZ-02_monitoring_2026-10-08.png` | Invocación exitosa de Queue worker y resultado `simulated_completed`; sin datos de identidad. | Captura directa pendiente. Monitor: 9 éxitos y 5 fallos históricos; un mensaje reintentado presenta error de checksum Blob/Queue. |
| `CUR-AZ-09_validacion_v5_2026-10-02.md` | Registro técnico del ciclo actual r2 y sus tres respuestas HTTP. | Health `200`, evento `202` y repetición idempotente `200`; tomar también la captura del portal del grupo r2 si se requiere evidencia visual actual. |

## Estado histórico al 04/10/2026 (superado por la revisión del 08/10)

- AWS: en ese corte previo al reinicio, el stack del ciclo anterior ya no existía.
- Azure: el grupo de recursos del ciclo anterior había sido eliminado; sus evidencias no describen el grupo actual.
- Ninguna evidencia debe reemplazarse con material histórico de AndeMarket ni con una imagen presentada como si fuera una captura de portal. Los PNG CLI se rotulan como registros visuales autenticados y las capturas de portal se guardan por separado.
