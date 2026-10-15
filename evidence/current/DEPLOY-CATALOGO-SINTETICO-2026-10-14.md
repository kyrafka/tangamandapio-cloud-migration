# Despliegue del catálogo sintético — 14/10/2026

## Resumen

Se publicó el catálogo sintético y sus controles de importación a las versiones
vigentes de AWS y Azure. Los cambios no alteran datos físicos ni infraestructura
de base de datos/red. El ledger de inventario sigue siendo demostrativo.

## AWS

- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`.
- Release: `20261014-synthetic-catalog-v10-python312`.
- Artefacto en bucket privado versionado, SSE-S3, SHA-256
  `c365c7005ba5e7f9108395f5716ef7504d706f810028dba6199144767da5b246`.
- Detección de deriva: `IN_SYNC`, cero recursos desviados.
- SSM verificó en ambas EC2 el mismo `BUILD_REVISION` y hashes de `app.py`,
  `erp_service.py` y `requirements.lock` que el paquete fuente.
- Dos destinos activos del balanceador sanos; `/`, `/health`, `/ready` y `/api`
  devolvieron HTTP 200. `/api/admin/users` anónimo devolvió 401; `/metrics`
  devolvió 404.
- RDS no cambió y permanece cifrada, privada, Single-AZ y con retención de
  backups de un día.

## Azure

- Function `tangama-wms-261008`: `Running`, HTTPS-only; health HTTP 200.
- Terraform aplicó el paquete
  `364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d`.
- El plan posterior terminó `No changes`. El cambio fue limitado al paquete de
  Function y al Blob versionado por contenido; no creó red privada ni otros
  recursos de plataforma.
- Un cambio de metadatos de un SKU existente por la ruta viva de catálogo
  conservó el saldo `on_hand`.
- Una venta sintética y recepción compensatoria recorrieron Queue/Function; el
  saldo del ledger regresó a la línea base. Ese smoke usó la aplicación local y
  SQLite como productor, no las EC2/RDS.

## E2E posterior del portal desplegado — 14/10/2026, 12:09 America/Chicago

Desde una instancia EC2 administrada por SSM se inició sesión en el portal v10
con la cuenta QA admin resuelta en memoria desde Parameter Store. No se expuso
ni transmitió la contraseña por el ALB HTTP público. El portal confirmó rol
admin y WMS `demo-inventory-ledger`; la importación autenticada del SKU
`SKU-QA-V10-20261014` quedó aceptada y conservó el saldo inicial de 10. Una
venta de una unidad terminó `completed_demo`; una recepción de una unidad
terminó `received_demo`. Ambos eventos outbox quedaron `delivered`, y la lectura
final a través del portal confirmó saldo 10 (línea base 10). Esto demuestra el
flujo portal desplegado → base de datos de la aplicación/outbox → Azure Queue y
Function → conciliación. La carga se hizo por API autenticada ejecutada desde
EC2; una carga manual del CSV desde navegador sigue pendiente.

## Calidad local

La compuerta local quedó aprobada: 155 pruebas Python, 8 pruebas Node, build
Vite, análisis de dependencias sin vulnerabilidades conocidas, CloudFormation
validado y Terraform validado/formateado. La validación IaC incluyó mocks y no
ejecutó operaciones cloud.

La plantilla trae 12 SKU sintéticos y permite preparar hasta 500 filas. El
flujo esperado es editar el XLSX, guardar/exportar a CSV UTF-8, previsualizar,
validar y confirmar la importación autenticada. Los saldos iniciales solo se
aplican a SKU nuevos; actualizar un SKU existente no pisa su saldo.

## Pendiente

- Hacer una importación del CSV desde el navegador AWS v10 con sesión de usuario
  y verificar visualmente la lectura persistida. La importación API autenticada
  y el recorrido portal/outbox/Azure ya pasaron en vivo.
- Sin VPN/conectividad privada AWS–Azure; la integración usa HTTPS público.
- Dominio y HTTPS confiable del portal siguen diferidos. WebRTC en dos
  navegadores reales también sigue sin prueba.
- Inventario ficticio de ledger, no WMS comercial; sin datos reales de
  distribuidores.

No se guardaron credenciales o claves de función en este informe.

## Reconciliación final posterior a la prueba — 14/10/2026, 12:13 America/Chicago

Una detección nueva de deriva en CloudFormation terminó `DETECTION_COMPLETE`,
`IN_SYNC`, cero recursos desviados. La pila AWS permaneció `UPDATE_COMPLETE` y
los dos destinos activos del target group respondieron `healthy`. El plan
Terraform de Azure refrescó el estado real y terminó `No changes`; Azure CLI
confirmó la Function `Running` y `httpsOnly=true`, y su endpoint de salud siguió
devolviendo HTTP 200. La prueba de reconciliación IaC no aplicó cambios.

## Repetición E2E y lectura concurrente cloud — 14/10/2026, 12:16 America/Chicago

Se repitió desde la misma EC2 administrada por SSM el flujo autenticado del
portal v10: SKU sintético `SKU-QA-V10-20261014`, saldo 10 antes/después, venta
`completed_demo`, recepción compensatoria `received_demo` y dos eventos outbox
entregados. Sin escrituras adicionales de inventario, a continuación se
ejecutaron 24 lecturas autenticadas de pedidos, compras y outbox con concurrencia
6; todas respondieron HTTP 200 y el p95 observado fue 304.09 ms. Es una
referencia acotada de una instancia de aplicación conectada a la base de datos,
directo por loopback; no atraviesa el ALB, no prueba escalado del ASG y no
representa 3,000 usuarios ni un SLA.
