# Integración WMS de demostración en Azure

Esta Function App recibe eventos sintéticos del portal, conserva evidencia y los procesa con una cola. Implementa un **ledger persistente de inventario ficticio para laboratorio**: recibe SKU/cantidad, valida el saldo y descuenta existencias demo una sola vez por evento. No está conectado a un almacén ni ERP real.

## Flujo

1. `GET /api/wms/inventory` devuelve el catálogo y saldo actual del laboratorio. La primera lectura crea el ledger en `inventory/state.json` dentro del contenedor privado de evidencia. El endpoint requiere clave Function.
2. `POST /api/fulfillment/events` recibe `event_id`, `event_type: "order.created"` y el pedido. Para descontar stock debe incluir `order.items: [{"sku":"SKU-ARROZ-001","quantity":2}]`. Requiere la clave Function; si `WMS_SHARED_TOKEN` está configurado, también `X-WMS-Token`.
3. La identidad administrada escribe el evento inmutable en Blob y luego publica `{event_id, sha256}` en Queue. Si Queue falla, AWS puede reintentar el mismo evento; otro contenido con el mismo ID devuelve `409`.
4. `process_fulfillment_message` valida el SHA-256, serializa cambios con un lease de Blob y guarda el saldo junto a los IDs procesados mediante ETag/If-Match. Reentregar el mismo ID no vuelve a descontar.
5. Resultado: `demo_fulfillment_completed` si hay saldo; `rejected_insufficient_stock` si falta stock (sin descontar ninguna línea); `awaiting_items` en eventos históricos sin SKU/cantidad. El resultado auditable se conserva en `fulfillment/{event_id}.json`.
6. `GET /api/fulfillment/events/{event_id}` devuelve el resultado o `{"status":"pending"}`. Requiere clave Function.

El catálogo seed es ficticio: arroz premium, azúcar rubia y aceite vegetal. Las cantidades iniciales y precios son datos académicos. El portal expone un botón “Generar pedido demo” restringido a Administración y Operaciones TI; el pedido y líneas quedan en AWS y el outbox antes de cruzar a Azure.

`GET /api/health` es una sonda pública mínima. La Function usa Managed Identity para Blob y Queue; no se deben colocar claves de Storage ni claves Function en el código o en Git.

## Configuración

- `AzureWebJobsStorage`: conexión usada por el runtime y el trigger de Queue.
- `AzureWebJobsFeatureFlags=EnableWorkerIndexing`: necesario para indexar los decoradores del modelo Python v2 usado por `function_app.py`.
- `ENABLE_ORYX_BUILD=true` y `SCM_DO_BUILD_DURING_DEPLOYMENT=true`: habilitan la instalación remota de `requirements.txt` en Linux.
- `WMS_QUEUE_NAME`: nombre de la cola de fulfillment.
- `AZURE_QUEUE_ACCOUNT_URL`, `AZURE_BLOB_ACCOUNT_URL`, `EVIDENCE_CONTAINER`: endpoints y contenedor de datos.
- `WMS_SHARED_TOKEN`: opcional; guárdalo como secreto de Key Vault/App Setting protegido.

La identidad administrada necesita permisos mínimos de lectura/escritura para el contenedor y envío/lectura/eliminación de mensajes en la cola. El trigger de Queue se conecta mediante `AzureWebJobsStorage`. La entrega es al menos una vez; el lease del Blob serializa el ledger compartido entre ejecuciones concurrentes.

## Pruebas

Las pruebas unitarias están en `app/azure_function_tests`. Ejecutar con el entorno Python del proyecto:

```powershell
app\.venv\Scripts\python.exe -m unittest discover -s app\azure_function_tests -v
```

Las pruebas unitarias no llaman recursos reales ni alteran el ledger de Azure. Un chequeo de punta a punta debe leer stock inicial, crear un evento sintético con líneas, esperar `demo_fulfillment_completed`, confirmar el saldo reducido exactamente una vez y repetir el mismo event ID para verificar idempotencia. No compartir claves Function.

## Pendiente antes de tratarlo como WMS real

Conectar un WMS real requiere contrato aprobado, catálogo fuente de verdad, autenticación del destino, reservas/despacho, deduplicación de negocio, compensación, alertas y pruebas de concurrencia. No se debe presentar `demo_fulfillment_completed` como despacho real ni como saldo de un ERP.
