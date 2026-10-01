# CUR-AWS-02 — Revalidación visual y técnica antes del cierre

**Fecha:** 30/09/2026  
**Región:** `us-east-1`  
**Stack:** `tangamandapio-live-20260930`  
**Propósito:** confirmar el estado real inmediatamente antes de solicitar el cierre de recursos facturables.

## Capturas visuales tomadas en CloudShell

Durante esta revalidación se capturaron tres evidencias visuales en la sesión de AWS Academy:

1. `CREATE_COMPLETE` y prueba funcional: `GET /health` respondió `HTTP/1.1 200 OK`, con `database=ok`; `GET /api/orders` respondió `HTTP/1.1 200 OK` y recuperó el pedido de prueba.
2. Salud de infraestructura: dos destinos del ALB en estado `healthy`; RDS `available`, `Public=false`, `Encrypted=true`, `BackupDays=1` y `MultiAZ=false` (limitación declarada del laboratorio).
3. Seguridad y observabilidad: los cuatro campos de S3 Public Access Block en `True`; alarma `tangamandapio-high-cpu` en `OK`; dashboard `tangamandapio-operations` presente.

## Comandos verificables

```bash
aws cloudformation describe-stacks --region us-east-1 --stack-name tangamandapio-live-20260930
aws elbv2 describe-target-health --region us-east-1 --target-group-arn "$TG_ARN"
aws rds describe-db-instances --region us-east-1 --db-instance-identifier tangamandapio-postgres
aws s3api get-public-access-block --bucket "$ASSET_BUCKET"
aws cloudwatch describe-alarms --region us-east-1 --alarm-name-prefix tangamandapio-
aws cloudwatch list-dashboards --region us-east-1 --dashboard-name-prefix tangamandapio-operations
```

## Resultado

La arquitectura de demostración funcionaba al momento de la prueba. No se declara alta disponibilidad productiva: RDS es de una AZ y se usa HTTP temporal por restricciones de costo del laboratorio. El cierre del stack sigue pendiente de confirmación inmediata para eliminar ALB, NAT Gateway, EC2, RDS, S3 y los demás recursos asociados.
