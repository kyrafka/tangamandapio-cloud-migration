# Integración WMS de demostración en Azure

Esta Function App recibe eventos sintéticos del portal, conserva evidencia y los procesa con una cola. Implementa un **ledger persistente de inventario ficticio para laboratorio**: recibe SKU/cantidad, valida el saldo y descuenta existencias demo una sola vez por evento. No está conectado a un almacén ni ERP real.

## Flujo

1. `GET /api/wms/inventory` devuelve el catálogo y saldo actual del laboratorio. La primera lectura crea el ledger en `inventory/state.json` dentro del contenedor privado de evidencia. El endpoint requiere clave Function.
2. `POST /api/wms/catalog` agrega o actualiza entre 1 y 500 SKU sintéticos. Un SKU nuevo inicia con `initial_stock`; cambiar nombre, unidad o precio nunca sobrescribe el saldo actual. La ruta usa la misma autenticación Function y coordina concurrencia con lease y ETag del Blob.
3. `POST /api/fulfillment/events` recibe `event_id`, `event_type: "order.created"` y el pedido. Para descontar stock debe incluir `order.items: [{"sku":"SKU-ARROZ-001","quantity":2}]`. Requiere la clave Function; si `WMS_SHARED_TOKEN` está configurado, también `X-WMS-Token`.
4. La identidad administrada escribe el evento inmutable en Blob y luego publica `{event_id, sha256}` en Queue. Si Queue falla, AWS puede reintentar el mismo evento; otro contenido con el mismo ID devuelve `409`.
5. `process_fulfillment_message` valida el SHA-256 y vuelve a comprobar que el tipo del sobre y del payload sea compatible antes de tocar existencias; un tipo desconocido o inconsistente se rechaza sin mutar el saldo. Serializa cambios con un lease de Blob y guarda el saldo junto a los IDs procesados mediante ETag/If-Match. Reentregar el mismo ID no vuelve a descontar.
6. Resultado: `demo_fulfillment_completed` si hay saldo; `rejected_insufficient_stock` si falta stock (sin descontar ninguna línea); `awaiting_items` en eventos históricos sin SKU/cantidad. El resultado auditable se conserva en `fulfillment/{event_id}.json`.
7. `GET /api/fulfillment/events/{event_id}` devuelve el resultado o `{"status":"pending"}`. Requiere clave Function.
8. Los mensajes fallidos se reintentan hasta cinco entregas (`host.json`); tras
   exceder el máximo, Azure Queue los mueve a `fulfillment-events-poison`.
   `GET /api/wms/poison-queue` requiere clave Function y devuelve solo el conteo
   aproximado, nunca cuerpos ni metadata personal del mensaje.

El catálogo seed trae 12 SKU de alimentos, con precios y saldos sintéticos de propósito académico. Administración y los roles con permiso `master:write` pueden mantenerlo en ERP → Maestros e importar CSV UTF-8 preparado con la plantilla Excel, hasta 500 SKU por carga. La validación completa sucede antes de guardar; el saldo inicial solo se usa para códigos nuevos. Ventas descuentan y recepciones incrementan este ledger sintético una vez por evento. No representa existencias físicas ni un WMS externo.

`GET /api/health` es una sonda pública mínima. La Function usa Managed Identity para Blob y Queue; no se deben colocar claves de Storage ni claves Function en el código o en Git.

## Configuración

- `AzureWebJobsStorage`: conexión usada por el runtime y el trigger de Queue.
- `AzureWebJobsFeatureFlags=EnableWorkerIndexing`: necesario para indexar los decoradores del modelo Python v2 usado por `function_app.py`.
- `ENABLE_ORYX_BUILD=false` y `SCM_DO_BUILD_DURING_DEPLOYMENT=false`: el ZIP incluye sus dependencias y no solicita un build en Kudu.
- `WMS_QUEUE_NAME`: nombre de la cola de fulfillment.
- `WMS_POISON_QUEUE_NAME`: nombre de la cola poison que se observa.
- `AZURE_QUEUE_ACCOUNT_URL`, `AZURE_BLOB_ACCOUNT_URL`, `EVIDENCE_CONTAINER`: endpoints y contenedor de datos.
- `WMS_SHARED_TOKEN`: opcional; guárdalo como secreto de Key Vault/App Setting protegido.

`host.json` fija `maxDequeueCount=5`, `visibilityTimeout=60 s` y lotes pequeños.
La identidad administrada necesita Blob Data Contributor en el contenedor de
eventos, Queue Data Contributor en la cola principal, Queue Data Reader en la
cola poison y Blob Data Reader en el contenedor privado de paquetes. Linux
Consumption carga el ZIP desde `WEBSITE_RUN_FROM_PACKAGE` usando
`WEBSITE_RUN_FROM_PACKAGE_BLOB_MI_RESOURCE_ID=SystemAssigned`; no se usa SAS
persistente. Terraform publica cada release como Blob inmutable por SHA-256.
Después de cada actualización de la URL externa del paquete se reinicia la
Function y se sincronizan los triggers. El trigger de Queue se conecta mediante
`AzureWebJobsStorage`. La entrega es al menos una vez; el lease del Blob
serializa el ledger compartido entre ejecuciones concurrentes.

## Pruebas

Las pruebas unitarias están en `app/azure_function_tests`. Ejecutar con el entorno Python del proyecto:

```powershell
app\.venv\Scripts\python.exe -m unittest discover -s app\azure_function_tests -v
```

Las pruebas unitarias no llaman recursos reales ni alteran el ledger de Azure. Un chequeo de punta a punta debe leer stock inicial, crear un evento sintético con líneas, esperar `demo_fulfillment_completed`, confirmar el saldo reducido exactamente una vez y repetir el mismo event ID para verificar idempotencia. No compartir claves Function.

## Pendiente antes de tratarlo como WMS real

Conectar un WMS real requiere contrato aprobado, catálogo fuente de verdad, autenticación del destino, reservas/despacho, deduplicación de negocio, compensación, alertas y pruebas de concurrencia. No se debe presentar `demo_fulfillment_completed` como despacho real ni como saldo de un ERP.
