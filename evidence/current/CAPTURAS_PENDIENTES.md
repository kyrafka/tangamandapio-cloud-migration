# Checklist de capturas vigentes

**Regla de integridad:** guardar cada imagen con el identificador indicado dentro de la carpeta de la nube correspondiente. No usar una imagen de `legacy/andemarket-historical` como si fuera evidencia de Tangamandapio. No mostrar cuentas, claves de Function, tokens, URLs firmadas ni credenciales.

## AWS — despliegue vigente 01/10/2026

La sesión temporal de AWS Academy ya permitió validar y desplegar la infraestructura vigente. El incidente anterior `CREATE_FAILED` del entorno Vocareum queda separado como antecedente y no se usa como evidencia de Tangamandapio.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AWS-03_laboratorio_y_region.png` | Sesión temporal de AWS Academy y región `us-east-1`. | Sesión autenticada usada para el despliegue vigente. |
| `CUR-AWS-04_inventario_inicial.png` | Inventario previo a Tangamandapio (VPC, EC2, ALB, RDS y stacks). | Partida limpia; identificadores de cuenta ocultos. |
| `CUR-AWS-05_cloudformation_validate.png` | `aws cloudformation validate-template` sobre `iac/cloudformation/aws-lab.yaml`. | Plantilla de Tangamandapio validada antes de crear recursos. |
| `CUR-AWS-06_stack_operativo_2026-10-01.png` | CloudFormation, ASG, ALB y RDS del stack vigente. | Stack operativo; dos nodos saludables; componentes de la arquitectura presentes. |
| `CUR-AWS-07_salud_infraestructura.png` | ALB, RDS, S3 Public Access Block y CloudWatch. | Dos targets `healthy`; RDS privada/cifrada; cuatro bloqueos S3 en `true`; alarmas y dashboard disponibles. |
| `CUR-AWS-08_prueba_funcional_2026-10-01.png` | Portal B2B y prueba `GET /health`, `POST /api/orders`, `GET /api/orders`. | HTTP `200`, `201`, `200`; pedido persistido desde PostgreSQL. |
| `CUR-AWS-09_cierre_y_costo_cero.png` | Tras la autorización de borrado: stack inexistente y laboratorio terminado. | No quedan ALB, NAT, EC2, RDS, S3 ni stack de Tangamandapio ejecutándose. |

### Orden seguro AWS (vigente)

1. Conservar los registros de preflight y validación efectuados antes de crear el stack.
2. Capturar `06` a `08` con el stack actualizado y el portal funcional.
3. Verificar que la actualización CloudFormation termine antes de eliminar.
4. Después de las evidencias, eliminar el stack temporal y capturar `09` con el inventario cero.

## Azure — vertical WMS actual

Azure no necesita máquinas virtuales. Ya se guardaron tres registros visuales de consultas Azure CLI autenticadas: inventario, Health y flujo WMS extremo a extremo. La prioridad restante es Monitor y cierre de inventario cero.

| ID y archivo sugerido | Qué debe verse en la captura | Resultado que debe quedar legible |
|---|---|---|
| `CUR-AZ-04_terraform_apply.png` | Terraform con `fmt`, `validate` y `apply` del vertical WMS temporal. | Recursos del grupo, sin secretos ni nombres de cuenta. |
| `CUR-AZ-05_inventario_cli_2026-10-01.png` | Consulta Azure CLI autenticada con Function, Storage, Key Vault, Application Insights y Log Analytics. | Guardada: inventario real actual del vertical Azure. |
| `CUR-AZ-06_health_cli_2026-10-01.png` | Prueba autenticada de `HttpHealth` y CORS limitado al portal. | Guardada: HTTP `200` y `status=ok`. |
| `CUR-AZ-07_wms_end_to_end_2026-10-01.png` | Evento WMS aceptado y verificación de Blob privado más mensaje de Queue. | Flujo idempotente exitoso; no imprimir claves de Function. |
| `CUR-AZ-08_monitor.png` | Application Insights/Azure Monitor después de la prueba. | Invocación correcta, latencia y ausencia de error 5xx en la ejecución corregida. |
| `CUR-AZ-09_cierre_inventario_cero.png` | Azure CLI o Portal tras eliminar ambos grupos temporales. | Inventario cero y control de costos cerrado. |

## Estado al 01/10/2026

- AWS: stack vigente desplegado en `us-east-1`; ALB con dos targets saludables, RDS privada y prueba real de pedidos superada. La actualización controlada de la interfaz debe terminar antes del cierre.
- Azure: `HttpHealth` respondió HTTP 200; `HttpFulfillment` registró un evento, rechazó el duplicado de forma idempotente y se verificaron Blob y Queue. El empaquetado Linux remoto y TTL de Queue se corrigieron.
- Ninguna evidencia debe reemplazarse con material histórico de AndeMarket ni con una imagen presentada como si fuera una captura de portal. Los PNG CLI se rotulan como registros visuales autenticados.
