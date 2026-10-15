# Revalidación cloud — 15/10/2026

## Estado comprobado

- AWS CLI `default`: STS autenticado en la cuenta académica `841113066612`.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; detección de
  drift posterior: `IN_SYNC`, cero recursos discrepantes.
- Release activo: `20261014-landing-loading-v11-python312`, artefacto con
  SHA-256 `ef3ffe5c7ff3a20e63084ea350e060dfc11bd3bf4dd44024e4d1f0d1ad557ba3`.
  Las dos EC2 `InService` reportaron por SSM la revisión exacta, servicio
  `active` y health local HTTP 200.
- ASG mínimo/deseado 2, máximo 5; exactamente dos destinos ALB `healthy`, sin
  instancias terminando. `GET /`, `/health` y `/ready` devolvieron HTTP 200.
  `GET /api/admin/users` sin sesión devolvió 401.
- VPC `10.10.0.0/16` `available`: dos subredes públicas para ALB (AZ `1a`/`1b`),
  dos privadas de aplicación con salida NAT y dos aisladas para RDS sin ruta por
  defecto. Security groups limitan el flujo a Internet→ALB:80,
  ALB→aplicación:8080 y aplicación→PostgreSQL:5432; EC2 y RDS no aceptan
  conexiones entrantes directas desde Internet. HTTPS aún no está configurado.
- RDS `available`, cifrada, privada, 20 GB, Single-AZ, retención de backup de
  un día. El change set de v11 no incluyó RDS, VPC ni grupos de seguridad.
- Las cinco alarmas CloudWatch consultadas están `OK`, con acciones habilitadas.
- Azure Function `tangama-wms-261008`: `/api/health` devolvió HTTP 200. No se
  modificó Azure ni se aplicó Terraform en esta sesión.

## Prueba funcional AWS→Azure sobre v11

El 15/10 se ejecutó por SSM en una EC2 v11 el arnés
`tests/cloud/live_aws_portal_azure_e2e.py`, con escritura expresamente limitada
a datos sintéticos y al ledger `demo-inventory-ledger`. Resultado
`LIVE_E2E_PASSED`:

- Admin autenticó como `admin` y completó la operación ERP.
- Comercial: ventas 200; administración, outbox e inventario 403.
- Operaciones: outbox e inventario 200; ventas y administración 403.
- SKU sintético importado; venta `completed_demo`; recepción compensatoria
  `received_demo`; ambos eventos outbox entregados por la integración Azure.
- El saldo del ledger demo quedó en 10 antes y después; no representa stock
  físico ni un WMS comercial.
- Carga de solo lectura a PostgreSQL/RDS: 24/24 HTTP 200, concurrencia 6,
  p95 679.98 ms. Se ejecutó dentro de EC2 por loopback, no a través del ALB;
  no demuestra capacidad para 3,000 usuarios.

El reporte JSON sin credenciales ni datos personales está en
[`AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json`](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json).

## Validación local después del despliegue

`tests/run_local_quality.ps1 -ValidateTerraform` terminó con
`QUALITY_GATE=APROBADA`: 165 pruebas unitarias Python, 14 pruebas Node, 40
transacciones aisladas, build Vite, auditoría de dependencias, CloudFormation
validado y Terraform `fmt`/`validate`/tests mock. Sin `terraform apply` ni
operaciones de nube. Véase [QA local del 15/10](QA-LOCAL-2026-10-15.md).

## Límites pendientes

El ALB sigue solo HTTP; dominio y HTTPS confiable no están configurados. No hay
conectividad privada AWS–Azure verificada. No se probó CSV manual en navegador,
WebRTC entre dos navegadores ni una carga transaccional por ALB/RDS a escala.
Los resultados de roles/ERP sí se repitieron sobre v11 mediante el smoke
autenticado anterior.

## Comprobación adicional — 15/10/2026, 00:43–00:49 UTC

Una lectura final posterior al despliegue confirmó CloudFormation
`UPDATE_COMPLETE`, drift `IN_SYNC`, ASG 2/2/5 con dos instancias `InService`, y
los dos destinos del target group `healthy`. El ALB devolvió HTTP 200 en
`/health` y `/ready`; la Function Azure respondió HTTP 200.

Además, Application Insights consultado con Azure CLI reportó 17 solicitudes
en `requests` durante las últimas 24 horas, cero fallidas; el desglose contenía
dos entradas exitosas de `process_fulfillment_message` y dos de
`receive_fulfillment_event`. Es evidencia viva de actividad del worker,
complementaria al E2E sintético, no una prueba de alerta entregada ni de WMS
comercial. El detalle reproducible está en
[`azure/AZURE-MONITOR-INVOCACIONES-2026-10-15.md`](azure/AZURE-MONITOR-INVOCACIONES-2026-10-15.md).

## Revalidación con el token nuevo — 15/10/2026, 01:30–01:37 UTC

AWS STS autenticó la sesión nueva en la cuenta Academy `841113066612`. Una
nueva detección CloudFormation concluyó `IN_SYNC` con cero recursos
discrepantes. El ASG sigue 2/2/5 con ambas EC2 `InService`; el target group
`tangamandapio-tg` tiene 2/2 destinos `healthy`. El ALB devolvió 200 en `/`,
`/health` y `/ready`; `/api/admin/users` sin sesión devolvió 401. RDS continúa
`available`, cifrada, privada, Single-AZ y con retención de backup de un día.
No se modificaron recursos AWS.

Azure CLI autenticó la suscripción `Azure for Students`; el grupo
`rg-tangamandapio-rebuild-wus` está `Succeeded`. La Function
`tangama-wms-261008` está `Running`, `httpsOnly=true`, y su `/api/health`
respondió 200. La consulta ARM de la suscripción no encontró VNets. La consulta
de red VPN pidió instalar la extensión `virtual-wan`; no se aceptó ni instaló.

Se repitió `CreateCustomerGateway --dry-run`: AWS denegó
`ec2:CreateCustomerGateway` por un `explicit deny` en la SCP de AWS Academy.
El dry-run no creó recursos. No existe conectividad privada AWS–Azure; el flujo
E2E vigente sigue usando HTTPS público hacia la Function.
