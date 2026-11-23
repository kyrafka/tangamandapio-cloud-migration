# Pruebas del proyecto

[Limpieza de recursos del 23/11](Limpieza_Cloud_2026-11-23.md) y comprobación posterior del portal y la ruta privada.

[Verificación operativa del 22/11](Verificacion_Operativa_2026-11-22.json) del portal, ALB, RDS, WMS, respaldo y suscripciones.

La versión `20261122-erp-form-fixes` está activa en las dos EC2. La ronda posterior al despliegue pasó **309 comprobaciones en 10 sesiones por rol**, incluidas las excepciones de JavaScript, el acceso a los módulos y las restricciones de permisos. El formulario SNS se comprobó con una dirección ya suscrita. Las escrituras de catálogo, ventas, compras y finanzas se probaron en una base aislada. [Registro de verificación del ERP](Verificacion_ERP_2026-11-22.json) · [Controles de GitHub](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/45113172324).

| Prueba | Resultado | Evidencia |
|---|---|---|
| Pedido AWS–Azure | Evento correlacionado entre ERP, cola, Blob e Insights. | [Registro del pedido](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json) |
| Autoescalado | 2 → 3 → 2 por carga en el ensayo del 22/11. | [Medición del ASG](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-AUTOSCALING-RATE-REFERENCE-2026-11-22.json) |
| Conmutación privada | Primer HTTPS 200 en 2,64 y 2,60 s en las dos EC2 del ensayo. | [Registro de conmutación](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-WMS-FAILOVER-RUBRIC-2026-11-19.json) |
| Roles del ERP | Acceso y restricciones comprobados en navegador. | [Prueba por rol](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-PORTAL-ROLES-BROWSER-2026-11-19.json) |

El informe entregado por separado reúne las capturas y el alcance de las pruebas.
