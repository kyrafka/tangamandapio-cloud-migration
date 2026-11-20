# Checklist de capturas vigentes

## Recorrido para la defensa del 20 de noviembre de 2026

Abre el [portal de Tangamandapio](https://tangamandapio.kendellnm.me/), la consola de AWS en **Ohio (us-east-2)** y el portal de Azure en la suscripción del proyecto. Guarda cada PNG con los nombres de la tabla. Mantén visibles el nombre del recurso, la fecha y el resultado. Recorta correos, IDs de cuenta o suscripción, contraseñas, claves, tokens y enlaces de descarga firmados.

| Paso y archivo | Dónde entrar y qué hacer | Qué debe verse |
| --- | --- | --- |
| 1. `01-portal-admin.png` | Entra al portal con Administración. Abre **Administración → Pruebas técnicas**. Opcionalmente repite con una cuenta de Ventas para `01b-portal-ventas.png`. | Menú y rol tras el inicio de sesión. En Ventas, abre el ERP y verifica que **Administración** queda restringida. |
| 2. `02-pedido-wms.png` | Abre **Seguimiento de pedidos** y elige el pedido sintético `SEGUIMIENTO-DEMO-20261119-151352`. Pulsa **Verificar en almacén**. En **Administración → Pruebas técnicas**, pulsa **Comprobar WMS** y guarda `02b-wms-en-vivo.png`. | El pedido procesado, su ID de evento y los estados del flujo. En la segunda imagen se ven la latencia y los conteos de ambas colas, que pueden estar en cero. |
| 3. `03-azure-trazas.png` y `03b-azure-blob.png` | Abre **Application Insights → tangama-wms-ai → Logs**. Elige un intervalo que incluya el 19/11 desde las 15:14 UTC y ejecuta la consulta de abajo. Luego abre **Storage accounts → sttangama261030r → Containers → fulfillment-events** y busca el mismo evento en los objetos de entrada y de resultado. | La misma ID en ambas trazas, con el registro de Queue seguido por el de resultado. En Blob se ven el archivo original y el de la carpeta `fulfillment/`. Si Azure deniega el acceso al contenedor, conserva la captura de las trazas y el [registro de objetos](azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json). |
| 4. `04-aws-stack.png` y `04b-aws-targets.png` | Abre **CloudFormation → Stacks → tangamandapio-live-20261116 → Events**. Luego entra a **EC2 → Target Groups → tangamandapio-tg → Targets**. | El estado de la pila, la última actualización y dos destinos `Healthy` tras estabilizarse. |
| 5. `05-aws-rds.png` | Abre **RDS → Databases → tangamandapio-postgres → Configuration**. | Estado `Available`, `Multi-AZ` habilitado y retención de un día. Puedes tomar una segunda captura de **Maintenance & backups** si la retención aparece allí. |
| 6. `06-aws-waf.png` y `06b-aws-registro-waf.png` | Abre la ACL regional del ALB en **AWS WAF → Web ACLs → Rules**. Luego abre **CloudWatch → Log groups → aws-waf-logs-tangamandapio-alb → Logs Insights** y ejecuta la consulta de abajo. | Las cuatro reglas y un registro real, con fecha, método, ruta y acción. La consulta proyecta solo esos campos. |
| 7. `07-escalado.png` y `07b-alarmas.png` | Abre **EC2 → Auto Scaling Groups → tangamandapio-asg → Activity** y amplía el período al día de la prueba. En **CloudWatch → Alarms** entra a una alarma de Tangamandapio y abre **History**. | Cambios de capacidad y retorno a dos. La alarma debe mostrar nombre, métrica y estado. La captura del correo SNS se toma aparte si el mensaje está disponible. |
| 8. `08-respaldo-y-restore.png` y `08b-copia-azure.png` | En **Administración → Pruebas técnicas**, abre la sección de restauración/RPO. En **Administración → Respaldos**, muestra el catálogo. En Azure abre **Storage → Containers → tangama-postgres-backups**. | El resultado fechado del ensayo, las 20 tablas restauradas, el RPO observado y el objeto de copia elegido. Para evidencia de ejecución abre también el comando de restauración en **AWS Systems Manager → Run Command → Command history** con el ID del [registro](aws/AWS-AZURE-POSTGRES-SCHEDULE-2026-11-19.json). |
| 9. `09-ruta-privada.png` | En **Administración → Pruebas técnicas**, muestra el ensayo fechado de conmutación. Puedes agregar **VPC → Route Tables → Routes**, filtrando por el destino privado `10.20.1.4/32`. | Tiempo de recuperación por EC2, conmutación al respaldo y regreso al principal. El estado mostrado corresponde al ensayo documentado. |
| 10. `10-aws-costos.png` y `10b-azure-costos.png` | Abre **AWS Billing → Budgets** y **Azure Cost Management → Budgets → tangamandapio-demo-usd25**. | Presupuesto, gasto, moneda y período de cada nube. Anota la hora de consulta porque los valores se actualizan de forma diferida. |

En **Logs** de Application Insights usa esta consulta. Si generas un pedido de demostración nuevo, reemplaza la ID en las dos búsquedas de Azure y conserva esa misma ID en las capturas.

```kusto
traces
| where message contains "evt-dce8944d04a64ea78484bf226ca876ef"
| where message contains "queued" or message contains "result_written"
| project timestamp, message
| order by timestamp asc
```

En **CloudWatch Logs Insights**, con el grupo del WAF seleccionado, usa esta consulta. Abre `/ready` en el portal antes de consultar si necesitas un registro reciente.

```text
fields @timestamp, httpRequest.httpMethod, httpRequest.uri, action
| filter httpRequest.uri = "/ready"
| sort @timestamp desc
| limit 10
```

El recorrido usa lecturas y evidencia existente. Para la defensa, el paso de escalado puede mostrar la actividad ya registrada. Si el docente pide una ejecución en vivo, inicia solo el nivel 3 desde **Administración → Prueba de escalado**, captura el tercer destino sano y espera a que la capacidad vuelva a 2.

## Entrega del 19/11/2026

| Captura pendiente | Qué debe verse | Registro del resultado |
|---|---|---|
| Trazas WMS | Application Insights, vista Logs. Mostrar los estados `queued` y `result_written` del mismo identificador sintético de pedido. | [Trazas de Azure](azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json) |
| Restauración | Mostrar la verificación de huellas y la consulta de las 20 tablas en el PostgreSQL aislado. La consola de Blob puede mostrar la copia de origen. | [Restauración](aws/AWS-AZURE-POSTGRES-SCHEDULE-2026-11-19.json) · [RPO](aws/AWS-POSTGRES-RPO-MARKERS-2026-11-19.json) |
| Presupuesto de Azure | Cost Management → Budgets, con gasto, presupuesto de USD 25 y período. Ocultar el identificador de la suscripción. | [Corte y desglose de costos](COSTOS-2026-11-19.md) |

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
