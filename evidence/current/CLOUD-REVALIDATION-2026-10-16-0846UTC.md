# Revalidación cloud — 16/10/2026, 08:43–08:46 UTC

## Estado vivo

- AWS STS aceptó la sesión de laboratorio en la cuenta `841113066612`.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`, última
  actualización `2026-10-16T00:27:59Z`, drift `IN_SYNC`.
- ASG: mínimo/deseado 2, máximo 5; dos EC2 `InService`/`Healthy`. Ambos discos
  raíz están `in-use` y `Encrypted=true` con la misma clave KMS. No se solicitó
  ni se aplicó una excepción sin cifrado.
- HTTPS del portal `/health`: 200. HTTP redirige a HTTPS con 301.
- Azure for Students está `Enabled`; el proveedor `Microsoft.Network` está
  registrado. No hay VNets del proyecto en la suscripción.

## Pruebas vivas

- `admin-readonly` por el origen ALB HTTPS con validación TLS/SNI:
  `LIVE_ADMIN_READONLY_SMOKE_PASSED`; 59/59 eventos del outbox entregados,
  cero pendientes, 24/24 GET HTTP 200 a concurrencia 6 (p95 585.97 ms), y
  permisos esperados: Comercial ventas 200 y rutas Admin/Operaciones 403;
  Operaciones outbox/inventario 200 y ventas/Admin 403. Dos suscripciones SNS
  confirmadas, cero pendientes. No escribió datos ni disparó alarmas.
- E2E sintético AWS→Azure por origen ALB HTTPS:
  `LIVE_E2E_PASSED`; catálogo importado, venta `completed_demo`, compra
  `received_demo`, dos eventos entregados y ledger demo exactamente 10→10.
  El smoke también verificó 24/24 GET HTTP 200 (concurrencia 6, p95 225.67 ms)
  y la matriz de autorización Comercial/Operaciones. La escritura se limitó a
  registros de prueba sintéticos y su recepción compensatoria; no cambió stock
  físico.
- Prueba de autorización VPN sin crear recursos: `CreateVpnGateway --dry-run`
  devolvió `DryRunOperation` (acción permitida); `CreateCustomerGateway
  --dry-run` devolvió `UnauthorizedOperation` por un `explicit deny` en una
  Service Control Policy de AWS Organizations. Esta denegación bloquea el lado
  AWS de la VPN IPsec administrada. No se crearon gateways, VNet, rutas ni
  túneles y no se inició gasto de VPN.

## Qué queda demostrado y qué no

El estado HTTPS/encriptación está operativo; la prueba de cifrado confirma que
no era necesario aprobar un disco raíz sin cifrar. La aplicación vuelve a
completar ventas y recepciones sintéticas entre AWS y Azure y los permisos API
de los dos roles probados conservan el 200/403 esperado. El smoke de lecturas
Admin es corto y su p95 observado fue 585.97 ms; el E2E paralelo midió
225.67 ms. Estos valores no representan una prueba de carga sostenida.

La interconexión privada no se puede desplegar en este AWS Academy: el
`explicit deny` de `ec2:CreateCustomerGateway` lo impide incluso con una sesión
válida. Azure aún no tiene la VNet necesaria. No se debe reportar una VPN
activa ni intentar sortear la SCP. Siguen pendientes la recuperación transitoria
viva del outbox, carga sostenida/escalado por carga, inspección visual completa
por rol y CSV, WebRTC entre dos navegadores, WAF, failover Multi-AZ y medición
atribuible de costos Azure. El WMS conserva su alcance de inventario sintético.

No se aplicó IaC ni se cambió configuración cloud en esta pasada.
