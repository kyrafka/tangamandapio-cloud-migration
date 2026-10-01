# Orquestación de migración — Tangamandapio S.A.C.

Este directorio convierte el caso ficticio de Tangamandapio en una migración controlada de datacenter a nube híbrida/multicloud. No representa una migración de datos personales: todos los pedidos, archivos y eventos usados en pruebas son sintéticos.

## Principios de ejecución

1. **AWS primero:** se estabiliza el canal transaccional antes de crear el vertical operativo en Azure.
2. **Infraestructura como código:** AWS usa CloudFormation; Azure tiene Terraform preparado, pero no se aplica hasta superar las puertas AWS.
3. **Cambio reversible:** se crea y revisa un change set antes de desplegar; todo recurso de laboratorio se etiqueta y se elimina al cierre.
4. **Evidencia antes de afirmación:** un servicio solo se marca implementado después de validación, prueba y captura reales.
5. **Costo mínimo viable:** se evita añadir plataformas duplicadas (por ejemplo Zabbix) mientras CloudWatch cubra la evidencia solicitada.

## Flujo de migración

| Fase | Orquestación | Estado actual | Criterio de salida |
|---|---|---|---|
| M0 — Preflight | Inventario, validación IaC, change set y ventana de costo | AWS validada; change set creado sin recursos | Alcance y costo aprobados |
| M1 — Landing zone AWS | Red segmentada, seguridad, cómputo, datos, observabilidad | Preparada en `iac/cloudformation/aws-lab.yaml` | Stack `CREATE_COMPLETE` |
| M2 — Validación AWS | Salud ALB, pedidos RDS, S3, aislamiento, alarmas y restauración | Pendiente de recursos reales | Evidencias CUR-AWS-03 a CUR-AWS-09 |
| M3 — Azure WMS | Function, Queue, Blob, Key Vault, telemetría y RBAC | IaC disponible; ningún recurso desplegado | Despliegue Azure y prueba de evento |
| M4 — Integración | Evento de pedido AWS hacia WMS Azure con contrato, idempotencia y reintento | Diseño/local simulator solamente | Evento real trazable extremo a extremo |
| M5 — Cierre | Inventario final, eliminación, RTO/RPO y lecciones aprendidas | Pendiente | CUR-AWS-10 y cierre de costos |

## Scripts AWS

Los scripts de `orchestration/aws/` se ejecutan desde CloudShell con la sesión temporal de AWS Academy. Son intencionalmente separados para que el paso que genera cargos requiera la variable explícita `CONFIRM_EXECUTE_AWS=YES`.

```text
preflight.sh             # solo lectura: plantilla, stack e inventario etiquetado
create_change_set.sh     # crea/revisa propuesta; no crea infraestructura
execute_change_set.sh    # paso facturable protegido por confirmación
verify_platform.sh       # salud ALB y targets, sin alta de pedido
```

Las consultas de análisis posteriores se conservan en `queries/aws/`; no se presentan como resultados hasta ejecutarse contra el log group real.

## Contrato de migración funcional

1. El portal B2B en AWS acepta un pedido sintético y lo guarda en PostgreSQL.
2. El pedido se representa como un evento versionado (`order.created`).
3. Azure recibirá el evento de forma autenticada e idempotente y lo escribirá en Blob/Queue del WMS.
4. Si Azure no está disponible, el emisor debe conservar el evento y reintentarlo; no se afirma una transacción distribuida.
5. La evidencia correlaciona el pedido, el identificador del evento, los logs y el resultado del WMS.

## Puertas de seguridad y costo

- No ejecutar `execute_change_set.sh`, pruebas de escritura ni restore RDS sin confirmación inmediata del responsable.
- La prueba DR requiere `CONFIRM_COSTLY_DR_TEST=YES` y limpieza automática.
- CloudWatch, CloudTrail o logs adicionales se activan únicamente tras revisar su alcance/costo.
- Azure no se inicia hasta eliminar o cerrar de forma comprobable el stack AWS de laboratorio.

