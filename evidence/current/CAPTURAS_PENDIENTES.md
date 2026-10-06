# Checklist de capturas vigentes

**Regla de integridad:** guardar cada imagen con el identificador indicado dentro de la carpeta de la nube correspondiente. No usar una imagen de `legacy/andemarket-historical` como si fuera evidencia de Tangamandapio. No mostrar cuentas, claves de Function, tokens, URLs firmadas ni credenciales.

## AWS — ciclo temporal cerrado por reinicio de laboratorio

La sesión temporal de AWS Academy permitió validar y desplegar la infraestructura de Tangamandapio. El 02/10/2026, tras reiniciar el laboratorio, CloudFormation mostró `Pilas (0)` al filtrar Tangamandapio y el DNS del ALB temporal dejó de resolver. Por eso, las capturas anteriores son evidencia técnica del ciclo ya finalizado, no del estado actual. El siguiente ciclo debe empezar con una credencial AWS Academy vigente, validación IaC y nuevas capturas completas; no reutilizar imágenes antiguas como si el nuevo stack ya estuviera activo.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AWS-03_laboratorio_y_region.png` | Sesión temporal de AWS Academy y región `us-east-1`. | Sesión autenticada usada para el despliegue vigente. |
| `CUR-AWS-04_inventario_inicial.png` | Inventario previo a Tangamandapio (VPC, EC2, ALB, RDS y stacks). | Partida limpia; identificadores de cuenta ocultos. |
| `CUR-AWS-05_cloudformation_validate.png` | `aws cloudformation validate-template` sobre `iac/cloudformation/aws-lab.yaml`. | Plantilla de Tangamandapio validada antes de crear recursos. |
| `CUR-AWS-06_stack_operativo_2026-10-01.png` | CloudFormation, ASG, ALB y RDS del stack vigente. | Stack operativo; dos nodos saludables; componentes de la arquitectura presentes. |
| `CUR-AWS-07_salud_infraestructura.png` | ALB, RDS, S3 Public Access Block y CloudWatch. | Dos targets `healthy`; RDS privada/cifrada; cuatro bloqueos S3 en `true`; alarmas y dashboard disponibles. |
| `CUR-AWS-08_prueba_funcional_2026-10-01.png` | Portal B2B y prueba `GET /health`, `POST /api/orders`, `GET /api/orders`. | HTTP `200`, `201`, `200`; pedido persistido desde PostgreSQL. |
| `CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md` | Registro técnico de la publicación B2B, rollback controlado y actualización final. | `UPDATE_COMPLETE`; `/health` 200 durante el recambio. No sustituye las capturas del siguiente ciclo. |
| `CUR-AWS-09_cierre_y_costo_cero.png` | Tras la autorización de borrado: stack inexistente y laboratorio terminado. | No quedan ALB, NAT, EC2, RDS, S3 ni stack de Tangamandapio ejecutándose. |

### Orden seguro AWS (vigente)

1. Actualizar la credencial temporal local desde AWS Academy y verificarla con una consulta de identidad.
2. Validar IaC, publicar el artefacto y crear un nuevo stack; antes de continuar, capturar `03` a `07` para el nuevo ciclo.
3. Probar Health, login/roles y pedidos contra el ALB nuevo; guardar `08` sin mostrar secretos.
4. Solo después de una autorización posterior, eliminar el stack temporal y capturar `09` con el inventario cero.

## Azure — ciclo WMS cerrado

Azure no necesita máquinas virtuales. El grupo `rg-tangamandapio-261001r2-wus` fue eliminado tras el ciclo de pruebas; la consulta autenticada confirmó que ya no existe. Las capturas Azure guardadas demuestran ese ciclo temporal, pero no se presentan como inventario activo. Un próximo ciclo debe volver a desplegar el vertical antes de tomar nuevas imágenes de portal.

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
| `CUR-AZ-09_validacion_v5_2026-10-02.md` | Registro técnico del ciclo actual r2 y sus tres respuestas HTTP. | Health `200`, evento `202` y repetición idempotente `200`; tomar también la captura del portal del grupo r2 si se requiere evidencia visual actual. |

## Estado de cierre al 04/10/2026

- AWS: el stack del ciclo anterior fue probado en `us-east-1`, pero no existe una pila de Tangamandapio tras el reinicio de laboratorio del 02/10. Se debe reprovisionar antes de reclamar disponibilidad actual.
- Azure: el ciclo temporal confirmó `HttpHealth` HTTP 200 y `HttpFulfillment` HTTP 202; sus registros confirmaron Blob 201, Queue 201 y ejecución correcta con identidad administrada. Después de conservar las evidencias, se eliminó el grupo. Un nuevo despliegue requiere nuevas capturas antes de afirmar disponibilidad actual.
- Ninguna evidencia debe reemplazarse con material histórico de AndeMarket ni con una imagen presentada como si fuera una captura de portal. Los PNG CLI se rotulan como registros visuales autenticados y las capturas de portal se guardan por separado.
