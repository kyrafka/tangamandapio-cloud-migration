# Revalidación de nube y flujo — 15/10/2026, 04:10 UTC

Comprobación con el laboratorio AWS renovado. No se desplegó infraestructura ni
se alteró configuración de recursos. Sí se ejecutó el E2E autorizado con
registros de negocio sintéticos y compensación de stock del ledger demo.

## AWS

- STS aceptó el perfil local default en la cuenta Academy 841113066612.
- CloudFormation tangamandapio-live-20261013 figura UPDATE_COMPLETE y su último
  estado de drift visible es IN_SYNC. El registro anterior ubica la detección
  completa más reciente a las 02:36 UTC; no se inició otra detección.
- Auto Scaling Group tangamandapio-asg: mínimo 2, deseado 2, máximo 5 y dos
  instancias InService.
- ALB tangamandapio-alb está activo; sus dos destinos están healthy. La portada
  y /health devolvieron HTTP 200 antes y después del E2E.
- RDS tangamandapio-postgres está available, cifrada, privada, 20 GB,
  Single-AZ y con un día de retención automática de backups.
- Listener actual: HTTP/80 solamente. No se habilitaron dominio ni HTTPS.
- Siete alarmas métricas tienen acciones habilitadas: seis están OK y la alarma
  TargetTracking AlarmLow figura INSUFFICIENT_DATA. No se afirma que todas las
  alarmas estén en estado OK.

## Azure y backend de Terraform

- La suscripción Azure for Students está Enabled y
  https://tangama-wms-261008.azurewebsites.net/api/health devolvió HTTP 200.
  La consulta de estado ARM de la Function no terminó en esta sesión; Running
  se había confirmado directamente a las 02:58 UTC y el plan vivo posterior
  volvió a leer los recursos sin diferencias.
- El backend remoto tiene los blobs azure-rebuild.tfstate (65,672 bytes) y
  azure-tfstate-bootstrap.tfstate (16,233 bytes). El contenedor no permite
  acceso anónimo; la cuenta requiere Entra ID (shared-key deshabilitado),
  HTTPS y TLS 1.2. La propiedad de red pública de la cuenta está Enabled, por
  lo que esto no se describe como un endpoint de red privado.
- Terraform plan contra los dos estados remotos terminó sin cambios: tanto
  azure-rebuild como azure-tfstate-bootstrap coinciden con sus configuraciones.
  No se ejecutó apply.

## E2E y calidad

- tests/cloud/run_live_aws_portal_azure_e2e.ps1 concluyó LIVE_E2E_PASSED desde
  una EC2 mediante SSM. La prueba se autenticó como Admin, importó/validó un SKU
  sintético, completó una venta completed_demo y una recepción received_demo,
  confirmó dos eventos outbox entregados por Azure y dejó el ledger demo en
  10→10.
- La matriz de autorización viva confirmó Comercial: ventas 200 y
  administración/outbox/inventario 403; Operaciones: outbox/inventario 200 y
  ventas/administración 403.
- 24 lecturas autenticadas: 24/24 HTTP 200, concurrencia 6, p95 277.17 ms.
  La carga se ejecutó contra loopback de una EC2, no a través del ALB y no
  demuestra capacidad para 3,000 usuarios.
- tests/run_local_quality.ps1 -ValidateTerraform terminó QUALITY_GATE=APROBADA:
  165 pruebas Python, 14 Node, 40 transacciones aisladas, build Vite,
  auditorías de dependencias sin vulnerabilidades conocidas, CloudFormation
  validado y Terraform fmt/validate/pruebas mock aprobados. La puerta local no
  realizó cambios en la nube.
- El branch codex/aws-v11-deploy-sync está sincronizado con 39617c9. GitHub
  Actions para ese commit terminó success.

## Brechas que siguen abiertas

El WMS/ledger de Azure sigue siendo demostrativo, no inventario empresarial.
No se probó la interfaz autenticada por navegador ni la importación CSV desde
archivo; tampoco carga de escrituras de negocio por ALB/RDS ni capacidad de
3,000 usuarios. Falta evidencia independiente de entrega actual de las alertas
por correo. No hay conectividad privada AWS–Azure; el preflight anterior fue
rechazado por una SCP de AWS Academy. WebRTC bidireccional entre navegadores y
dominio/HTTPS confiable siguen pendientes. El almacenamiento del state usa
contenedor privado y Entra, pero el endpoint de la cuenta sigue público y debe
restringirse con red privada o firewall cuando exista un runner autorizado.

## Revalidación adicional — 15/10/2026

Con el token temporal renovado, STS autenticó de nuevo la cuenta Academy. Se
añadió al E2E el permiso de consulta de alertas y se volvió a ejecutar contra
el portal desplegado: Admin vio 2 suscripciones SNS confirmadas y ninguna
pendiente; Comercial y Operaciones recibieron 403. No se modificaron
suscripciones ni se enviaron correos. La misma prueba completó la venta y
recepción sintéticas hacia Azure, dejó el ledger en 10→10 y tuvo 24/24 lecturas
RDS HTTP 200 (concurrencia 6, p95 2,005.03 ms por loopback de EC2). Véase el
[reporte sanitizado de permisos y alarmas](aws/AWS-ALARM-SUBSCRIPTIONS-ROLE-SMOKE-2026-10-15.md).
