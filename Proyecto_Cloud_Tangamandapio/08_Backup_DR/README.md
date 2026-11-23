# Respaldo y recuperación

- [Copia cifrada programada](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/iac/cloudformation/aws-azure-postgres-backup.yaml)
- [Restauración aislada de 20 tablas en 35,108 s](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-AZURE-POSTGRES-SCHEDULE-2026-11-19.json)
- [Medición del RPO de 15 h 39 min 44 s](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-POSTGRES-RPO-MARKERS-2026-11-19.json)
- [Ensayo aislado posterior con 21 tablas](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/azure/AZURE-PORTAL-SCHEDULED-RECOVERY-2026-11-21.json)

## Evidencia para el criterio 9

La rúbrica evalúa la estrategia de respaldo, el RTO/RPO y una recuperación probada. El respaldo programado y cifrado en Azure Blob se restauró en PostgreSQL aislado. En el ensayo posterior se levantó el ERP con los datos restaurados y se verificaron dos pedidos.

La recuperación en una segunda región queda como mejora adicional. En la cuenta evaluada, una política de AWS Organizations limitó el uso de RDS fuera de Ohio. [Registro de la restricción y del ensayo](../../iac/ESTADO_REAL_2026-11-19.md).
