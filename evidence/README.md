# Índice de evidencias del proyecto

El único resumen del inventario vivo es
[MAPA_ESTADO_ACTUAL_2026-10-08.md](current/MAPA_ESTADO_ACTUAL_2026-10-08.md)
(corte 19:48 CDT). Las bitácoras Chrome/cierre conservan cortes anteriores; las
pruebas locales más nuevas están en
[PRUEBAS_LOCALES_2026-10-08.md](current/PRUEBAS_LOCALES_2026-10-08.md).

## Clasificación

`current/` significa carpeta de trabajo/evidencias del proyecto, no que cada
archivo o captura ahí sea vigente. Revisa siempre fecha, hora y nota de
precedencia de cada registro. Evidencia de despliegue anterior permanece válida
para ese corte, pero no prueba el inventario actual.

| Ubicación | Uso permitido |
|---|---|
| `current/aws/baseline-before-core/` | Línea base reciente de Tangamandapio; demuestra solo lo que su propio registro afirma y no reemplaza nuevas pruebas CUR-AWS. |
| `current/aws/`, `current/azure/` | Evidencias nuevas aptas para el informe y la sustentación. OCI quedó fuera de alcance del entregable. |
| `legacy/andemarket-historical/` | Antecedentes de otro nombre/alcance. Se pueden rescatar como procedimiento, pero no se presentan como evidencia vigente. |

## Mapa de evidencias de todo el proyecto

| Tema | Fuente principal | Cómo interpretarla |
|---|---|---|
| Alcance, empresa ficticia y decisiones de arquitectura | [`core/00_registro_maestro.md`](../core/00_registro_maestro.md), [`core/04_matriz_rubrica.md`](../core/04_matriz_rubrica.md), [`core/09_propuesta_cloud_aws_azure.md`](../core/09_propuesta_cloud_aws_azure.md) | Requisitos y propuesta; no equivalen a despliegue. |
| Diagrama multicloud | [`arquitectura_aws_examen.drawio`](../arquitectura_aws_examen.drawio), [`arquitectura_aws_examen.svg`](../arquitectura_aws_examen.svg) | Diseño objetivo; no constituye inventario de recursos. |
| AWS — publicación y pruebas de octubre 1–2 | [`CUR-AWS-03`](current/aws/CUR-AWS-03_despliegue_y_prueba_2026-10-01.md), [`CUR-AWS-10`](current/aws/CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md), [artefacto release](../app/aws_release/README.md) | Registros técnicos históricos y paquete; revisar la fecha/ciclo antes de sostener estado actual. Los PNG `CUR-AWS-06/08` son tarjetas resumen, no screenshots de AWS. |
| Azure — WMS | [`CUR-AZ-09`](current/azure/CUR-AZ-09_validacion_v5_2026-10-02.md), [código Function](../app/azure_function/README.md) | Health/evento/idempotencia demostrados en ciclo pasado; el worker da resultado `simulated_completed`, no actualiza inventario real. |
| Portal, roles y brechas | [Mapa de estado actual](current/MAPA_ESTADO_ACTUAL_2026-10-08.md), [bitácora histórica web](../app/WEB_STATUS_AND_GAPS_2026-10-08.md), [manual portal y telefonía](../core/08_manual_evolucion_portal_y_telefonia_ip.md) | El mapa es la referencia vigente; la bitácora conserva cortes previos y no debe leerse como lista actual de pendientes. |
| Voz/WebRTC y grabaciones | [Pruebas AWS release](../app/aws_release/tests), [migraciones de voz](../app/aws_release/current/migrations) | Pruebas de backend/local y S3 simulado; no prueba llamada real entre dos navegadores ni graba conversaciones reales. |
| Pruebas locales | [`PRUEBAS_LOCALES_2026-10-08.md`](current/PRUEBAS_LOCALES_2026-10-08.md) | Actualización posterior: 59 aprobadas, auditorías de dependencias limpias, build aislado, CloudFormation/Terraform válidos y smoke local p95 345.66 ms; no son prueba de todas las funciones live. |
| Observación visual Chrome y validación live del 08/10 | [`REVISION_CHROME_2026-10-08.md`](current/REVISION_CHROME_2026-10-08.md), [`CAPTURAS_PENDIENTES.md`](current/CAPTURAS_PENDIENTES.md) | AWS CloudFormation mostró el stack actual (51 recursos) y el ALB tuvo 2 destinos Healthy; Azure aceptó, procesó y permitió consultar un evento sintético. El registro escrito existe; los nuevos PNG crudos de Chrome siguen pendientes de archivo. |

## Convención nueva

`CUR-{NUBE}-{NN}`: por ejemplo, `CUR-AWS-04_alb-health.png` o `CUR-AZ-03_function-evento.png`.

Cada evidencia debe registrar: fecha, región, recurso, configuración, prueba, resultado y estado de limpieza. Nunca incluir credenciales, claves, identificadores de cuenta ni datos personales. Identificar siempre si una imagen es una captura directa, una tarjeta/resumen creado a partir de CLI o un diagrama de diseño.

La secuencia concreta de capturas por tomar se mantiene en [CAPTURAS_PENDIENTES.md](current/CAPTURAS_PENDIENTES.md). Las imágenes de octubre 1–2 corresponden a ciclos anteriores; los registros del ciclo posterior y sus límites están en [el estado del portal](../app/WEB_STATUS_AND_GAPS_2026-10-08.md) y la [revisión visual de Chrome](current/REVISION_CHROME_2026-10-08.md). No inferir disponibilidad actual de imágenes históricas.

## Índice de Azure — 01/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AZ-01 | Terraform aplicó el vertical WMS temporal en West US | Infraestructura creada; 12 recursos |
| CUR-AZ-02 | Diagnóstico y corrección de empaquetado Linux | Antecedente; no prueba el flujo WMS completo |
| CUR-AZ-03 | Plan de cierre e inventario final del ciclo inicial | Ejecutado; evidencia histórica en CUR-AZ-08 |
| CUR-AZ-05 | Inventario Azure CLI | Function `Running`, recursos PaaS y dos rutas registradas |
| CUR-AZ-06 | Health WMS autenticado | HTTP 200 y CORS limitado al portal |
| CUR-AZ-07 | WMS extremo a extremo | Health 200; evento 202; Blob privado de 430 bytes, Queue y entrega del outbox local verificados |
| CUR-AZ-08 | Cierre Azure inicial | Grupos del primer ciclo eliminados; consulta por prefijo sin resultados en ese momento |
| CUR-AZ-09 | Validación actual del WMS r2 | Function actual, Health 200, Fulfillment 202 y reintento idempotente 200 registrados sin claves |
| AZ-PORTAL-01 | Captura real del inventario en el portal del ciclo previo | PNG disponible; antecedente, no inventario activo |
| AZ-PORTAL-02 a 04 | Vistas descritas en `LIVE_PORTAL_2026-10-01.md` | No hay PNG de esas tres vistas en el repositorio; tratar los resultados escritos como registro, no captura adjunta |

Los registros visuales de Azure se guardan como PNG dentro de `current/azure/screenshots/`. Están rotulados como consultas autenticadas de CLI, por lo que no se confunden con capturas del portal. El grupo `rg-tangamandapio-261001r2-wus` fue eliminado al cierre; las imágenes prueban el ciclo temporal y no un inventario vigente.

## Índice de AWS — 02/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AWS-03 | Validación CloudFormation, despliegue temporal y prueba funcional | Health 200, pedido 201, recuperación 200, dos targets healthy |
| CUR-AWS-06 | Infraestructura AWS CLI | ALB, ASG, RDS, S3 y observabilidad verificados antes de la revocación de sesión |
| CUR-AWS-08 | Prueba funcional AWS CLI | Resultados HTTP reales contra el ALB temporal |
| CUR-AWS-10 | Publicación B2B versionada | Validación IaC, diagnóstico del rollback inicial, corrección y `UPDATE_COMPLETE` de la actualización gradual |

Tras reiniciar el laboratorio el 02/10, el stack `tangamandapio-live-20261001` de ese ciclo quedó cerrado. En el corte visual posterior del 08/10, CloudFormation mostró `tangamandapio-live-20261005`, 51 recursos y dos destinos `Healthy`; el inventario vivo más reciente está en `current/MAPA_ESTADO_ACTUAL_2026-10-08.md`. La pila separada `tangamandapio-voice-recordings` figuró `CREATE_COMPLETE` en la revisión Chrome, pero no se revalidó en el corte más reciente. Las tarjetas PNG del 01/10 no prueban el ciclo actual y siguen pendientes capturas crudas nuevas de Chrome/consola.

### Aclaración de formato

`CUR-AWS-06_stack_operativo_2026-10-01.png` y
`CUR-AWS-08_prueba_funcional_2026-10-01.png` son **tarjetas visuales resumidas**
basadas en consultas AWS CLI registradas en sus documentos acompañantes. No son
capturas crudas de Chrome, CloudShell ni la consola. La revisión visual en Chrome
del 08/10 está descrita en `current/REVISION_CHROME_2026-10-08.md`; los PNG no
pudieron archivarse desde la sesión actual, así que el nuevo set sigue pendiente.

### Aclaración de formato Azure

`AZ-PORTAL-01_inventario_2026-10-01.png` sí es una captura directa del portal
Azure del ciclo histórico descrito en `current/azure/LIVE_PORTAL_2026-10-01.md`.
Los PNG `CUR-AZ-05` a `CUR-AZ-08` son **tarjetas visuales** creadas a partir de
resultados Azure CLI; no son capturas del terminal ni del portal. La vista
Azure observada el 08/10 y el evento sintético E2E también están en
`current/REVISION_CHROME_2026-10-08.md`: POST `202`, Queue worker `Succeeded`
(93 ms), estado GET `200 simulated_completed`. El monitor registró 9 éxitos y 5
errores en 30 días; se inspeccionó un error antiguo de checksum Blob/Queue y se
dejó intacto. La observación está documentada, pero no hay un PNG nuevo de
Chrome archivado.
