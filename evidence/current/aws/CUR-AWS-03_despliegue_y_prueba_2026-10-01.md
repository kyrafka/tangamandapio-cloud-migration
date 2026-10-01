# CUR-AWS-03 — Despliegue y prueba funcional de Tangamandapio

**Fecha:** 01/10/2026

**Región:** `us-east-1`
**Stack temporal:** `tangamandapio-live-20261001`

## Validaciones ejecutadas antes de la revocación de sesión

| Verificación | Resultado observado |
|---|---|
| Plantilla | `aws cloudformation validate-template` aprobó `iac/cloudformation/aws-lab.yaml`. |
| CloudFormation | El stack inicial alcanzó `CREATE_COMPLETE`. |
| Balanceo y escalamiento | ALB con dos destinos `healthy`; Auto Scaling `min=2`, `desired=2`, `max=4`. |
| Base de datos | RDS PostgreSQL `available`, `PubliclyAccessible=false`, cifrada, retención de 1 día y Single-AZ declarada como limitación de laboratorio. |
| Seguridad S3 | Los cuatro controles de Public Access Block respondieron `true`. |
| Observabilidad | Dashboard `tangamandapio-operations` y cuatro alarmas presentes en estado `OK`. |
| Prueba HTTP | `GET /health` devolvió `200` con `status=ok` y `database=ok`; `POST /api/orders` devolvió `201`; `GET /api/orders` devolvió `200` y recuperó los pedidos en PostgreSQL. |
| Portal web | El portal B2B se abrió detrás del ALB y mostró estado de plataforma `ok`, base de datos `ok` y los pedidos persistidos. |

## Corrección de interfaz

Se actualizó la plantilla para servir `styles.css` y `app.js` como recursos propios y conservar CSP con `script-src 'self'` y `style-src 'self'`. Antes de que la credencial fuera cancelada se verificaron dos targets de la versión actualizada en estado `healthy` y la prueba HTTP volvió a responder correctamente.

## Control de costos pendiente

Después de capturar las evidencias, AWS Academy aplicó una denegación temporal `voc-cancel-cred` a la sesión local. Por esa razón no fue posible confirmar el estado final de la actualización ni emitir `delete-stack` desde esa credencial. Esta denegación ocurrió después de las pruebas funcionales y no invalida sus resultados.

Cuando el laboratorio emita una nueva sesión válida, la secuencia obligatoria es:

1. Ejecutar `describe-stacks` y confirmar que no hay operación en progreso.
2. Ejecutar `delete-stack` para `tangamandapio-live-20261001`.
3. Esperar la eliminación y verificar inventario cero de ALB, NAT, EC2, RDS, S3 y CloudFormation.

Las imágenes asociadas son `screenshots/CUR-AWS-06_stack_operativo_2026-10-01.png` y `screenshots/CUR-AWS-08_prueba_funcional_2026-10-01.png`. Son registros visuales de consultas autenticadas de AWS CLI, no capturas de la consola de AWS.
