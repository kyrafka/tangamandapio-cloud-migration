# Pruebas del proyecto

[Verificación operativa del 22/11](Verificacion_Operativa_2026-11-22.json) del portal, ALB, RDS, WMS, respaldo y suscripciones.

| Prueba | Resultado | Evidencia |
|---|---|---|
| Pedido AWS–Azure | Evento correlacionado entre ERP, cola, Blob e Insights. | [Registro del pedido](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json) |
| Autoescalado | 2 → 3 → 2 por carga en el ensayo del 22/11. | [Medición del ASG](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-AUTOSCALING-RATE-REFERENCE-2026-11-22.json) |
| Conmutación privada | Primer HTTPS 200 en 2,64 y 2,60 s en las dos EC2 del ensayo. | [Registro de conmutación](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-WMS-FAILOVER-RUBRIC-2026-11-19.json) |
| Roles del ERP | Acceso y restricciones comprobados en navegador. | [Prueba por rol](https://github.com/kyrafka/tangamandapio-cloud-migration/blob/bf864d8df0e954d0bba72a7c5098dafc525f2419/evidence/current/aws/AWS-PORTAL-ROLES-BROWSER-2026-11-19.json) |

Capturas, pruebas funcionales y alcance en el informe entregado por separado.
