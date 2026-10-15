# Release Azure — validación del tipo de evento — 13/10/2026

## Objetivo

Endurecer el consumidor del WMS de laboratorio para que vuelva a validar el
tipo del evento ya persistido. El trabajador solo acepta `order.created` y
`purchase.received`; si el tipo no está admitido o difiere entre el sobre y el
payload, registra un rechazo y no aplica cambios al saldo. El endpoint de
entrada ya validaba esta condición; la defensa nueva cubre también el límite
Queue → consumidor.

## Pruebas y publicación

- `tests/run_local_quality.ps1 -ValidateTerraform` terminó
  `QUALITY_GATE=APROBADA`: 120 pruebas unitarias, auditorías de dependencias,
  build frontend, lint CloudFormation, `terraform fmt/validate` y pruebas mock.
- El ZIP reproducible quedó en
  `artifacts/azure_function_package-20261013-event-guard-v1.zip`, SHA-256
  `0E1F153FF4130175844346A2874F09E58015388B43DF7B54611752400E8B7211`.
- El plan previo mostró únicamente un Blob de paquete nuevo, actualización en
  sitio de la Function y retiro del Blob de release anterior. No hubo
  reemplazos de infraestructura. El Storage conserva soft delete de Blob
  habilitado por siete días (`allowPermanentDelete=false`).
- Terraform aplicó el plan: 1 recurso agregado, 1 actualizado y 1 retirado.
  El único objeto retirado fue el paquete anterior, recuperable durante la
  retención de siete días; no se tocaron inventario, eventos ni colas.
- El plan posterior terminó `No changes` (salida 0), por lo que el estado
  administrado quedó sincronizado con esta configuración.

## Verificación viva

La Function `tangama-wms-261008` quedó `Running`, `httpsOnly=true`; el setting
`DEPLOYMENT_PACKAGE_SHA256` coincide con el ZIP y `/api/health` respondió 200
con `status: ok`. Un POST autenticado de prueba con el evento sintético
`evt-guard-20261013-02` y `event_type=inventory.adjusted` devolvió HTTP 400 con
el mensaje esperado de tipo no compatible. El rechazo ocurre en la validación
antes de solicitar identidad administrada, persistir Blob o publicar Queue; no
se ejecutó ningún movimiento de inventario. Las claves de Function no se
registraron en la evidencia.

## Recorrido funcional y cola poison — corte 13/10/2026

Después del release pasó un segundo E2E vivo: el ERP del artefacto AWS corrió
como proceso local, creó una venta que se entregó por outbox a Azure
Queue/Function y reconcilió el resultado; la compra de compensación repuso el
SKU al saldo leído antes de la prueba. No se usó EC2 ni se cambió RDS.

- Venta: `evt-cfc7353b1e8e4708a7449e7bd160b3aa` →
  `demo_fulfillment_completed`.
- Reposición compensatoria: `evt-265c43727d0e4b51ba51e49527e3ccfd` →
  `demo_restock_completed`.
- El smoke verificó que el saldo final coincidiera exactamente con la línea
  base; la base SQLite temporal se limpió y los dos eventos sintéticos quedan
  en la auditoría Azure.
- `GET /api/wms/poison-queue` devolvió `status=ok`, conteo aproximado `0` y
  `payloads_exposed=false`; no se leyeron ni borraron mensajes.
- En la revalidación local siguiente, `/api/health` volvió a responder HTTP 200.
- La lectura ARM finalizada a las 20:14 confirmó la Function `Running`,
  `httpsOnly=true` y hostname `tangama-wms-261008.azurewebsites.net`.

## Alcance no demostrado

El inventario sigue siendo un ledger sintético de laboratorio (`demo-inventory-ledger`),
no un WMS comercial ni existencias físicas. Este release no cambia ese alcance,
no acredita una conexión privada AWS–Azure y no modifica el estado AWS. La
lectura de CloudFormation continúa denegada por `voc-cancel-cred`; véase la
[revalidación cloud](../CLOUD-REVALIDATION-2026-10-13.md).
