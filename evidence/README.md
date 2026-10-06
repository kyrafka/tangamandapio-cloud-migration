# Evidencias del núcleo vigente

## Clasificación

| Ubicación | Uso permitido |
|---|---|
| `current/aws/baseline-before-core/` | Línea base reciente de Tangamandapio; demuestra solo lo que su propio registro afirma y no reemplaza nuevas pruebas CUR-AWS. |
| `current/aws/`, `current/azure/` | Evidencias nuevas aptas para el informe y la sustentación. OCI quedó fuera de alcance del entregable. |
| `legacy/andemarket-historical/` | Antecedentes de otro nombre/alcance. Se pueden rescatar como procedimiento, pero no se presentan como evidencia vigente. |

## Convención nueva

`CUR-{NUBE}-{NN}`: por ejemplo, `CUR-AWS-04_alb-health.png` o `CUR-AZ-03_function-evento.png`.

Cada evidencia debe registrar: fecha, región, recurso, configuración, prueba, resultado y estado de limpieza. Nunca incluir credenciales, claves, identificadores de cuenta ni datos personales.

La secuencia concreta de fotos por tomar se mantiene en [CAPTURAS_PENDIENTES.md](current/CAPTURAS_PENDIENTES.md). Los dos ciclos temporales fueron cerrados; ese archivo y el [plan de reanudación](../core/07_plan_reanudacion_y_mejoras.md) determinan qué se debe reproducir antes de declarar disponibilidad actual.

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
| AZ-PORTAL-01 a 04 | Capturas reales del ciclo previo de portal Azure | Inventario, Function en ejecución, Health 200 y Fulfillment 202 con Blob/Queue 201; conservar como antecedente, no como foto del r2 |

Los registros visuales de Azure se guardan como PNG dentro de `current/azure/screenshots/`. Están rotulados como consultas autenticadas de CLI, por lo que no se confunden con capturas del portal. El grupo `rg-tangamandapio-261001r2-wus` fue eliminado al cierre; las imágenes prueban el ciclo temporal y no un inventario vigente.

## Índice de AWS — 02/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AWS-03 | Validación CloudFormation, despliegue temporal y prueba funcional | Health 200, pedido 201, recuperación 200, dos targets healthy |
| CUR-AWS-06 | Infraestructura AWS CLI | ALB, ASG, RDS, S3 y observabilidad verificados antes de la revocación de sesión |
| CUR-AWS-08 | Prueba funcional AWS CLI | Resultados HTTP reales contra el ALB temporal |
| CUR-AWS-10 | Publicación B2B versionada | Validación IaC, diagnóstico del rollback inicial, corrección y `UPDATE_COMPLETE` de la actualización gradual |

Tras reiniciar el laboratorio el 02/10, la consola de CloudFormation muestra cero pilas de Tangamandapio y el DNS del ALB de la ejecución anterior no resuelve. Los registros AWS anteriores se conservan como evidencia técnica del ciclo temporal; no se presentan como prueba de un stack actualmente activo. El reprovisionamiento y sus nuevas capturas quedan pendientes de cargar una credencial AWS Academy vigente.
