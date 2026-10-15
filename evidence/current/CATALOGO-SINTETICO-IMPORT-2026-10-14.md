# Catálogo sintético e importación masiva — 14/10/2026

## Alcance

El inventario es ficticio, pero sí se administra y modifica dentro del sistema:
la aplicación local contiene 12 productos de ejemplo y su ledger mantiene
saldos sintéticos. No se necesita esperar un archivo de una empresa real para
probar altas, ventas, recepciones, reintentos e idempotencia. Este saldo no
representa inventario físico.

## Flujo de carga

En ERP → Maestros, las cuentas internas con permiso `master:write` pueden bajar
la plantilla `.xlsx`, editarla con Excel y guardarla como **CSV UTF-8**. También
se ofrece el CSV directo. La interfaz previsualiza la importación antes de
confirmarla.

Campos: `sku`, `name`, `unit`, `sale_price`, `purchase_cost` e
`initial_stock`. Se admiten CSV con coma o punto y coma (incluido decimal con
coma), hasta 500 filas y 1 MB. El parser valida encabezados, formato, filas
vacías, SKU repetidos, precios y límites antes de enviar el lote.

Un SKU nuevo recibe el saldo sintético inicial indicado. Al actualizar uno ya
existente se mantienen sus existencias actuales: el archivo actualiza datos
maestros, no ajusta stock. Azure WMS conserva el `on_hand`; el ERP no mantiene
una segunda copia. La venta descuenta y la recepción incrementa el ledger una
sola vez por evento. Si WMS no responde, la importación falla cerrada y el ERP
no da por completado el lote.

En Azure Function la ruta de catálogo valida todo el lote antes de escritura,
serializa actualizaciones con Blob lease y ETag/If-Match, y la ampliación del
catálogo conserva tanto los movimientos procesados como los saldos existentes.
Los SKU importados son válidos para eventos posteriores.

## Evidencia local

- Portal Flask: 58 pruebas completas aprobadas en esta revisión y 8 pruebas
  focalizadas posteriores cubrieron el importador, el ledger local, rechazo de
  duplicados, preservación de saldo y venta de SKU nuevo.
- Azure Function: 29 pruebas unitarias aprobadas; incluyen alta/actualización
  con saldo preservado, rechazo de precio booleano, SKU dinámico y seguridad de
  idempotencia del ledger.
- CSV/UI: 6 pruebas Node aprobadas; cubren CSV regional de Excel, plantilla de
  12 filas, duplicados, formato inválido y equivalencia del parser empaquetado.
- Acceso UI: 8 pruebas de política por rol aprobadas; build Vite completado.
- Release AWS local: 45 pruebas de regresión aprobadas. La compuerta de paquete
  generó dos tarballs idénticos y confirmó dentro del candidato los módulos y
  ambas plantillas. El candidato v10 tiene SHA-256
  `c365c7005ba5e7f9108395f5716ef7504d706f810028dba6199144767da5b246`.
- La plantilla XLSX fue exportada, reabierta con el lector de hojas y sus dos
  pestañas se inspeccionaron/renderizaron.
- El paquete Azure reproducible se generó con SHA-256
  `364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d`; el
  ejemplo Terraform apunta al paquete fuente-validado.

## Verificación cloud posterior — 14/10/2026, 11:41–11:58 America/Chicago

AWS: el release `20261014-synthetic-catalog-v10-python312` se publicó en el
bucket privado versionado con SSE-S3. CloudFormation terminó `UPDATE_COMPLETE`;
la detección posterior fue `IN_SYNC`, con cero recursos desviados. Los dos
destinos activos del ALB están sanos. SSM confirmó revisión v10 y hashes
coincidentes de `app.py`, `erp_service.py` y `requirements.lock` en las dos
EC2. `/`, `/health`, `/ready` y `/api` devolvieron 200; `/metrics` 404 y
`/api/admin/users` sin sesión 401.

Azure: Terraform publicó el paquete Function
`364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d` y actualizó
la Function; el plan posterior confirmó `No changes`. Health devolvió 200. Un
smoke de venta y recepción compensatoria por Queue/Function terminó bien y el
saldo demo volvió a su línea base. Una petición viva al endpoint de catálogo
actualizó los metadatos de un SKU existente y confirmó que su `on_hand` no
cambió. El smoke usó release local con SQLite, no las EC2 ni RDS.

## Límite y siguiente prueba

El flujo Excel → CSV UTF-8, vista previa y validación está cubierto localmente
y el módulo ya está en AWS v10. Se probó también la ruta viva de catálogo Azure,
pero falta cargar un CSV desde el navegador del portal desplegado con sesión
autorizada y confirmar el resultado allí. El ledger es ficticio por diseño; no
representa inventario físico ni un WMS comercial.

## Rechequeo focalizado — 14/10/2026, 12:29 America/Chicago

Se repitieron las seis pruebas Node del parser CSV: formato Excel con BOM,
delimitador regional y coma decimal, plantilla de 12 SKU, igualdad del parser
incluido en el paquete AWS, encabezados/SKU duplicados y filas malformadas o
fuera de rango; 6/6 pasaron. Cinco pruebas backend dirigidas al lote verificaron
validación antes de sincronizar, preservación del saldo, rechazo de booleanos,
atomicidad y SKU repetidos; 5/5 pasaron con base temporal y cliente de prueba.
No se tocó Azure ni AWS. La carga mediante la vista real del navegador sigue
pendiente y, al corte de 12:25, el ALB AWS respondía 503.

## Límite de lote e integración en la compuerta — 14/10/2026, 13:29 America/Chicago

Se añadieron casos de límite tanto en la API del portal como en la Function
Azure: un lote de 500 SKU se acepta con dependencias de nube/DB simuladas, y
501 SKU se rechazan antes de cualquier escritura o llamada al WMS. Las suites
portal y Function pasaron 62/62 y 31/31, respectivamente. La puerta de calidad
integral incluye estos casos y terminó con 159 pruebas Python, además de 14
pruebas Node. Son pruebas automatizadas locales; el portal AWS está
respondiendo nuevamente, pero la importación todavía no se ejecutó desde su
interfaz con una sesión autorizada. El intento de smoke autenticado posterior
se detuvo por el rol incorrecto de la cuenta QA admin antes de importar datos.

## API de catálogo desde AWS y flujo Azure — 14/10/2026, 14:12 America/Chicago

Corrección: el smoke anterior falló por una expectativa de rol equivocada en el
harness, no por el usuario admin. En una ejecución posterior desde EC2 v10, el
portal autenticó como admin e importó por API autenticada el SKU sintético
`SKU-QA-V10-20261014`. Una venta y su recepción compensatoria terminaron
`completed_demo`/`received_demo`, ambos eventos quedaron `delivered` y el ledger
Azure regresó de 10 a 10. Se confirmó que la ruta API live de importación y la
integración funcionan; el archivo CSV seleccionado y confirmado desde la
interfaz del navegador aún no se probó. Las operaciones generan registros QA
persistentes y auditados, no inventario real. Resultado completo en
[revalidación cloud](CLOUD-REVALIDATION-2026-10-14.md).
