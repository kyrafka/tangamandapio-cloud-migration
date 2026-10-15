# Prueba viva compensada ERP → Azure — 15/10/2026

## Resultado

El smoke protegido `tests/run_live_azure_erp_smoke.py` terminó con
`LIVE_E2E=PASSED` contra la Function `tangama-wms-261008` en `Azure for
Students` (suscripción `Enabled`). La Function estaba `Running` y configurada
`HTTPS-only`; su `/api/health` devolvió HTTP 200.

La prueba comprobó:

- Ingreso sin clave → HTTP 401; fuente no autorizada con clave → HTTP 400; el
  ID rechazado no quedó persistido.
- Venta ERP de un SKU sintético → outbox entregado en el primer intento,
  Azure Queue/Function respondió `demo_fulfillment_completed` y el ERP
  reconcilió `completed_demo`.
- Recepción compensatoria → outbox entregado en el primer intento, Azure
  respondió `demo_restock_completed` y el ERP reconcilió `received_demo`.
- El saldo del ledger ficticio terminó exactamente en la línea base capturada
  al inicio.
- La consulta de metadatos de poison queue indicó cero antes y después; no se
  leyeron ni eliminaron mensajes.

IDs sintéticos para correlación: venta
`evt-5d32a672df1547debcbfa7afdd6ea7d9`; recepción
`evt-686bfd834d874c70a9dce99b66ff4352`. Los eventos válidos permanecen en el
almacenamiento de auditoría de Azure.

## Límites

La prueba ejecutó `app/aws_release/current` localmente con SQLite temporal; no
salió de la instancia EC2 desplegada. Confirma el procesamiento real de Azure
y la integración del release local, pero no la ruta productiva ALB/EC2→Azure,
la conectividad privada multinube, ni un WMS/ERP comercial. La sesión de
trabajo no reveló ni guardó la clave de Function.
