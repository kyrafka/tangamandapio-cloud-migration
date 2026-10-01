# CUR-AWS-01 — Despliegue y prueba funcional real

**Fecha:** 30/09/2026  
**Región:** `us-east-1`  
**Stack:** `tangamandapio-live-20260930`  
**Estado al cierre del registro:** recursos aún activos mientras se solicita la autorización de cierre.

## Evidencia verificable

CloudFormation reportó `CREATE_COMPLETE` después de ejecutar el change set validado de 37 cambios.

La prueba se hizo contra el Application Load Balancer temporal, sin exponer el endpoint privado de la base de datos:

| Prueba | Resultado observado |
|---|---|
| `GET /health` | `HTTP/1.1 200 OK`; respuesta `status=ok` y `database=ok`. |
| `POST /api/orders` | `HTTP/1.1 201 CREATED`; se creó el pedido de prueba con id `1`. |
| `GET /api/orders` | `HTTP/1.1 200 OK`; recuperó el mismo pedido desde PostgreSQL. |
| Targets del ALB | 2 destinos en estado `healthy`. |
| RDS PostgreSQL | Estado `available`, no público, cifrado, retención de backup de 1 día. |
| S3 de activos | Las cuatro opciones de Public Access Block se verificaron en `true`. |
| Observabilidad | Dashboard `tangamandapio-operations` presente y alarma `tangamandapio-high-cpu` en `OK`. |

## Captura asociada

Se tomó una captura visual de CloudShell durante la ejecución de la prueba funcional (HTTP 200, HTTP 201 y HTTP 200). La imagen se conserva en el registro de la sesión; este archivo conserva el resultado textual para trazabilidad y evita guardar datos temporales innecesarios.

## Límites honestos

- La demostración opera por HTTP temporal; no se afirma TLS/WAF implementado.
- RDS usa una sola AZ y un NAT Gateway por control de costo de laboratorio; no se presenta como alta disponibilidad productiva.
- La ampliación de métricas que existe en la plantilla local posterior no se declara desplegada en esta ejecución de contingencia.

## Cierre pendiente

La eliminación del stack, que incluye ALB, NAT, EC2, RDS y bucket del proyecto, requiere confirmación inmediata del propietario antes de ejecutarse. Después se verificará que no queden recursos facturables del proyecto.
