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

La secuencia concreta de fotos por tomar se mantiene en [CAPTURAS_PENDIENTES.md](current/CAPTURAS_PENDIENTES.md). AWS tiene prioridad hasta terminar su actualización controlada y limpieza posterior. Azure cuenta desde el 01/10/2026 con inventario, Health y flujo completo Blob/Queue verificados.

## Índice de Azure — 01/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AZ-01 | Terraform aplicó el vertical WMS temporal en West US | Infraestructura creada; 12 recursos |
| CUR-AZ-02 | Diagnóstico y corrección de empaquetado Linux | Antecedente; no prueba el flujo WMS completo |
| CUR-AZ-03 | Cierre e inventario final | Pendiente de autenticación CLI y destrucción verificada |
| CUR-AZ-05 | Inventario Azure CLI | Function `Running`, recursos PaaS y dos rutas registradas |
| CUR-AZ-06 | Health WMS autenticado | HTTP 200 y CORS limitado al portal |
| CUR-AZ-07 | WMS extremo a extremo | Health 200; evento 202; duplicado 200; Blob y Queue privados verificados |

Los registros visuales de Azure se guardan como PNG dentro de `current/azure/screenshots/`. Están rotulados como consultas autenticadas de CLI, por lo que no se confunden con capturas del portal. Sólo queda pendiente el inventario cero de cierre cuando se autorice eliminar los recursos temporales de Azure.

## Índice de AWS — 01/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AWS-03 | Validación CloudFormation, despliegue temporal y prueba funcional | Health 200, pedido 201, recuperación 200, dos targets healthy |
| CUR-AWS-06 | Infraestructura AWS CLI | ALB, ASG, RDS, S3 y observabilidad verificados antes de la revocación de sesión |
| CUR-AWS-08 | Prueba funcional AWS CLI | Resultados HTTP reales contra el ALB temporal |

La credencial de AWS Academy fue cancelada después de obtener las pruebas. El cierre de recursos queda explícitamente pendiente hasta obtener una nueva sesión válida; no se marca como completado ni se sustituye con evidencia histórica.
