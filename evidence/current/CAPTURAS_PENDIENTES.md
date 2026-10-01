# Checklist de capturas vigentes

**Regla de integridad:** guardar cada imagen con el identificador indicado dentro de la carpeta de la nube correspondiente. No usar una imagen de `legacy/andemarket-historical` como si fuera evidencia de Tangamandapio. No mostrar cuentas, claves de Function, tokens, URLs firmadas ni credenciales.

## AWS primero cuando AWS Academy vuelva a funcionar

La evidencia AWS se toma solo después de que el estado del laboratorio esté verde y CloudShell pueda usar credenciales temporales. El fallo actual `CREATE_FAILED` del entorno Vocareum se registra como incidente, no como una prueba de la infraestructura Tangamandapio.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AWS-03_laboratorio_y_region.png` | AWS Academy en ejecución y CloudShell; región `us-east-1`. | Laboratorio listo y sesión temporal vigente. |
| `CUR-AWS-04_inventario_inicial.png` | CloudShell con inventario antes de desplegar: VPC, EC2, ALB, RDS y stacks. | Inventario de partida del proyecto; ocultar identificador de cuenta si aparece. |
| `CUR-AWS-05_cloudformation_validate.png` | `aws cloudformation validate-template` sobre `iac/cloudformation/aws-lab.yaml`. | Plantilla de Tangamandapio validada. |
| `CUR-AWS-06_stack_create_complete.png` | CloudFormation con el stack `tangamandapio-*`, estado `CREATE_COMPLETE` y recursos. | Despliegue temporal confirmado; no usar nombres de AndeMarket. |
| `CUR-AWS-07_salud_infraestructura.png` | Salida de ALB, RDS, S3 Public Access Block y CloudWatch. | Dos targets `healthy`; RDS privada/cifrada; cuatro bloqueos S3 en `true`; alarma/dashboards disponibles. |
| `CUR-AWS-08_prueba_funcional.png` | Una consola única con `GET /health`, `POST /api/orders` y `GET /api/orders`. | HTTP `200`, `201`, `200`; pedido persistido desde PostgreSQL. |
| `CUR-AWS-09_cierre_y_costo_cero.png` | Tras la autorización de borrado: stack inexistente y laboratorio terminado. | No quedan ALB, NAT, EC2, RDS, S3 ni stack de Tangamandapio ejecutándose. |

### Orden seguro AWS

1. Capturar `03` a `05` antes de crear recursos.
2. Crear el stack temporal, esperar `CREATE_COMPLETE` y capturar `06` a `08`.
3. Revisar juntos los recursos facturables antes de eliminarlos.
4. Pedir confirmación inmediata antes de borrar el stack; recién entonces capturar `09`.

## Azure después de corregir el WMS

Azure no necesita levantar máquinas virtuales. Ya se guardaron dos registros visuales de consultas Azure CLI autenticadas: inventario actual y Health HTTP 200. La prioridad pendiente es repetir el evento WMS completo y conservar la evidencia de Blob, Queue, Monitor y cierre.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AZ-04_terraform_apply.png` | Terraform con `fmt`, `validate` y `apply` del vertical WMS temporal. | Recursos del grupo, sin secretos ni nombres de cuenta. |
| `CUR-AZ-05_inventario_cli_2026-10-01.png` | Consulta Azure CLI autenticada con Function, Storage, Key Vault, Application Insights y Log Analytics. | Guardada: inventario real actual del vertical Azure. |
| `CUR-AZ-06_health_cli_2026-10-01.png` | Prueba autenticada de `HttpHealth` y CORS limitado al portal. | Guardada: HTTP `200` y `status=ok`. |
| `CUR-AZ-07_fulfillment_blob_queue.png` | Evento WMS aceptado y verificación de Blob privado más mensaje de Queue. | Flujo idempotente exitoso; no imprimir claves de Function. |
| `CUR-AZ-08_monitor.png` | Application Insights/Azure Monitor después de la prueba. | Invocación correcta, latencia y ausencia de error 5xx en la ejecución corregida. |
| `CUR-AZ-09_cierre_inventario_cero.png` | Azure CLI o Portal tras eliminar ambos grupos temporales. | Inventario cero y control de costos cerrado. |

## Estado al 30/09/2026

- AWS Academy: entorno detenido por `CREATE_FAILED` del stack administrado de Vocareum; no se realiza despliegue hasta recuperarlo.
- Azure: infraestructura temporal creada; `HttpHealth` respondió HTTP 200 y CORS quedó limitado al portal. El empaquetado Windows fue reemplazado por código fuente para compilación remota Linux y el TTL de Queue se corrigió en la fuente. `HttpFulfillment` sigue pendiente de prueba integral con Blob/Queue antes de poder declararse aprobado.
- Ninguna captura pendiente debe reemplazarse con una evidencia histórica o con una imagen diseñada.
