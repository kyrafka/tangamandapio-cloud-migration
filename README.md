# Tangamandapio

Proyecto integrador de Cloud Computing. El ERP de pedidos opera en AWS Ohio y se integra con un WMS privado en Azure West US.

- [**Carpeta de entrega académica**](Proyecto_Cloud_Tangamandapio/README.md). Índice numerado, diagramas, direccionamiento IP y evidencias.
- [CloudFormation para AWS](Proyecto_Cloud_Tangamandapio/04_IaC/cloudformation/README.md) y [Terraform para Azure](Proyecto_Cloud_Tangamandapio/04_IaC/terraform/README.md).
- [Portal Tangamandapio](https://tangamandapio.kendellnm.me/).

## Estado operativo verificado el 22/11/2026

| Componente | Verificación |
|---|---|
| Portal AWS | HTTPS 200 en /health y /ready. Dos destinos sanos. ASG de 2 a 5. |
| Datos AWS | RDS PostgreSQL disponible, privada, cifrada y Multi-AZ. Un día de retención administrada. |
| WMS privado | Las dos EC2 obtuvieron HTTPS 200 de la Function por el Private Endpoint 10.20.1.4. El acceso público de la Function está deshabilitado. |
| Respaldo | Systems Manager reportó Success en la ejecución diaria. La restauración se ensayó en PostgreSQL aislado. |
| Alertas | Gmail y UPeU figuran confirmados como suscriptores en SNS. |

La versión del ERP `20261122-erp-form-fixes` fue verificada en las dos EC2. Pasó 309 comprobaciones de navegador en diez sesiones por rol. [Resultados de la versión publicada](Proyecto_Cloud_Tangamandapio/06_Pruebas/Verificacion_ERP_2026-11-22.json).

Los [registros de pruebas](Proyecto_Cloud_Tangamandapio/06_Pruebas/README.md) detallan la fecha y alcance de cada ensayo. Queda por probar la recuperación regional, la promoción de RDS y la reconstrucción integral desde cuentas vacías.

## Código y operación

- [Código del ERP y WMS](app) · [IaC y orden de reconstrucción](iac/README.md) · [Pruebas automatizadas](tests/README.md).
- [Seguridad](Proyecto_Cloud_Tangamandapio/05_Seguridad/README.md) · [Monitoreo](Proyecto_Cloud_Tangamandapio/07_Monitoreo/README.md) · [Recuperación](Proyecto_Cloud_Tangamandapio/08_Backup_DR/README.md) · [Costos](Proyecto_Cloud_Tangamandapio/09_Costos/README.md).

El proyecto utiliza datos sintéticos. El informe y el manual técnico se entregan por separado.
