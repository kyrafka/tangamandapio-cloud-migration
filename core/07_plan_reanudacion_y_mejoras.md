# Plan de reanudación cloud — actualización 29/10/2026

Este orden busca reanudar el proyecto sin desplegar recursos a ciegas ni duplicar servicios. El inventario más reciente de AWS está bloqueado por permisos y el dominio devolvió 503; Azure tiene recursos inventariados, pero la conectividad privada no se revalidó desde AWS en la última consulta.

## Fase 1 — diagnóstico sin cambios

1. Iniciar AWS Academy, comprobar cuenta/región y consultar CloudFormation, ALB/targets, ASG, EC2, RDS, WAF, S3, Secrets Manager, alarmas y SNS.
2. Si IAM/SCP niega el inventario, detener mutaciones y obtener el estado desde una consola/identidad autorizada.
3. Comprobar Azure subscription, Function Flex, Private Endpoint, gateway P2S, rutas, DNS y logs de Function.
4. Diagnosticar el 503 del dominio desde ALB, target group, instancias y logs; no cambiar Cloudflare mientras el origen no esté claro.

## Fase 2 — reconciliar IaC y recuperación

1. Comparar el inventario AWS con `iac/cloudformation/aws-lab.yaml` y el estado remoto Terraform Azure con sus roots.
2. Validar artefactos, secretos y snapshots requeridos sin imprimirlos ni incorporarlos a Git.
3. Preparar change sets/plans y revisar reemplazos, retención y costos antes de cualquier apply.
4. Probar restauración PostgreSQL desde una copia protegida en un entorno aislado. La evidencia S3→Blob actual solo cubre un fixture sintético.

## Fase 3 — levantar y probar servicios

1. Recuperar el portal primero; validar `/health`, `/ready`, login, sesiones, roles y rutas API.
2. Revalidar desde AWS el camino privado al endpoint de WMS Flex y después crear una venta/recepción QA con el mismo ID de evento.
3. Correlacionar pedido, outbox, mensaje, ejecución Function y resultado; probar reintento idempotente y tratamiento seguro de errores.
4. Revisar métricas de RDS y pool. Solo después de resolver el cuello de botella, ejecutar carga gradual y demostrar ASG 2→3.
5. Añadir SQS/Lambda/DLQ únicamente con permiso para un rol de ejecución mínimo y si aporta al criterio; no usar el rol amplio `LabRole`.
6. Integrar Entra ID y MFA administrativo después de que los roles actuales estén validados y documentados.

## Fase 4 — evidencia y cierre

- Guardar capturas reales de las consolas AWS/Azure y las vistas del portal, retirando tokens, correos personales y datos sensibles.
- Actualizar la matriz de criterios con estado, fecha, fuente y límites; no presentar pruebas locales como pruebas cloud.
- Reconciliar README, CloudFormation, Terraform y release antes de publicar.
- Dejar dominio/HTTPS y A/V WebRTC como verificaciones separadas si siguen fuera del alcance inmediato.

## Criterio de parada

No aplicar ni borrar recursos mientras el inventario, los backups o los secretos requeridos no estén disponibles y protegidos. Una sesión STS válida no garantiza permisos de administración. Para el estado operativo y las salvaguardas consulta el [runbook AWS](01_aws_ejecucion.md), el [runbook Azure](02_azure_ejecucion.md) y [IaC](../iac/README.md).
