# Plan maestro de pruebas AWS Azure

| ID | Área | Caso | Criterio | Estado |
|---|---|---|---|---|
| PT-AWS-01 | Funcional | GET `/health`, POST/GET órdenes | HTTP 200, pedido persistido | Históricamente aprobado en AWS |
| PT-AWS-02 | Disponibilidad | Revisar ALB y destinos | Dos destinos healthy | Históricamente aprobado en AWS |
| PT-AWS-03 | Datos | RDS privada y S3 cifrado | Sin acceso público; AES256 | Históricamente aprobado en AWS |
| PT-IAC-01 | IaC | `terraform fmt`, `init`, `validate`, `plan` | Sin error y sin secretos | `fmt`, `init` y `validate` aprobados; `plan` pendiente de credenciales |
| PT-MC-01 | Integración | Evento AWS a Azure Function | Mismo `event_id` y hash | Pendiente de despliegue Azure |
| PT-MC-02 | WMS | Function publica tarea en Queue y Blob | Tarea/objeto único y log | Pendiente de despliegue Azure |
| PT-MC-03 | Resiliencia | Azure no disponible | Pedido AWS queda creado; outbox reintenta | Pendiente de integración |
| PT-SEC-01 | Seguridad | Token inválido y ruta no autorizada | 401/403 sin secreto expuesto | Pendiente |
| PT-DR-01 | Recuperación | Restaurar snapshot/objeto | RTO/RPO medidos | Pendiente |
| PT-COST-01 | Cierre | Destruir infraestructura temporal | Inventario sin recursos facturables | Pendiente para Azure; aprobado históricamente AWS |

Cada prueba final requiere captura de pantalla real, fecha, nube, región, servicio, configuración, resultado esperado y resultado observado.
