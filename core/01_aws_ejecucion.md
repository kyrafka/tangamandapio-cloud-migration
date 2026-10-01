# Fase AWS — núcleo comercial

## Objetivo

Desplegar temporalmente el canal comercial de Tangamandapio: portal B2B, API, persistencia privada y capa resiliente. La fuente IaC candidata es `iac/cloudformation/aws-lab.yaml`; debe revisarse y validarse antes de cada uso.

## Recursos que sí se levantan

| Capa | Recurso | Control esperado |
|---|---|---|
| Red | VPC `10.10.0.0/16`, 2 AZ, subredes públicas/app/DB, IGW, rutas y NAT temporal | Aplicación y BD sin IP pública |
| Entrada | ALB, health check y dos targets | ALB reparte tráfico y detecta fallos |
| Cómputo | Launch Template + ASG mínimo 2 EC2 | Reemplazo/escala horizontal |
| Datos | RDS PostgreSQL privada/cifrada | Solo AppSG puede alcanzar 5432 |
| Objetos | S3 versionado/cifrado | Comprobantes y objetos sintéticos |
| Seguridad | Security Groups, rol mínimo, Secrets Manager | Secretos fuera del código |
| Operación | CloudWatch logs, dashboard y alarmas | Métricas y evidencia visible |

No se crean VDI, directorio administrado, VM administrativa permanente ni recursos ajenos al flujo demostrable.

## Brechas que deben cerrarse en esta fase

1. Validar el portal estático y la API reales en la capa del ASG. La plantilla instala un portal B2B ligero; el código fuente Vite queda como activo de evolución, no como componente declarado desplegado.
2. Verificar `POST /api/orders` y `GET /api/orders` contra RDS en el stack vigente.
3. Implementar/mostrar HTTPS válido. Si no hay dominio/ACM disponible, registrar la limitación y no afirmar HTTPS cumplido.
4. Mantener un outbox y reintento seguro para el evento hacia Azure; no usar una transacción distribuida.
5. Ejecutar prueba de caída de un target, dashboard/alarma y recuperación de una copia.

## Secuencia obligatoria y evidencias

| ID nuevo | Acción | Resultado exigido |
|---|---|---|
| CUR-AWS-01 | Laboratorio activo, región e inventario inicial | Captura sin recursos propios o con recursos identificados |
| CUR-AWS-02 | `validate-template` | Plantilla válida |
| CUR-AWS-03 | Stack `CREATE_COMPLETE` | Inventario de recursos propios |
| CUR-AWS-04 | ALB + `/health` | HTTP 200 y 2 targets healthy |
| CUR-AWS-05 | Crear/listar pedido | Persistencia PostgreSQL real |
| CUR-AWS-06 | Intento externo a RDS | Acceso rechazado |
| CUR-AWS-07 | Retirar un target | ALB continúa respondiendo y ASG recupera capacidad |
| CUR-AWS-08 | Dashboard/alarma/log | Métrica y evento visibles |
| CUR-AWS-09 | Backup/restore | Objeto o dato recuperado y RTO/RPO medidos |
| CUR-AWS-10 | `delete-stack` e inventario final | Recursos propios eliminados y Lab terminado |

## Cierre de costos

Antes de terminar la ventana se elimina el stack, se confirma su ausencia, se revisan EC2/RDS/ALB/NAT/S3 propios y se finaliza Learner Lab. Nunca se eliminan recursos preexistentes sin identificar y sin autorización explícita.
