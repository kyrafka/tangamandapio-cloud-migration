# Paquete reproducible y plan de publicación Azure — 13/10/2026

## Corte más reciente — 22:03 America/Chicago

La ruta `function_package_path` del ejemplo normal de Terraform se corrigió:
antes apuntaba a un ZIP mutable antiguo (`643750B5…`) cuyo código no coincidía
con la fuente. El paquete actual se construyó desde `app/azure_function` con
`requirements.lock` y hashes, wheels de Python 3.11/Linux, timestamp ZIP fijo y
nombre content-addressed. La prueba local comprobó coincidencia byte por byte de
`function_app.py`, `host.json`, `requirements.txt` y `requirements.lock`, además
del SHA-256 completo:
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065`.
El paquete previo local `azure_function_package-20261013-event-guard-v1.zip`
se conserva con hash `0e1f153ff4130175844346a2874f09e58015388b43df7b54611752400e8b7211`.

El plan autenticado propuso únicamente crear el Blob del paquete nuevo, cambiar
settings de la Function en el sitio y destruir el objeto Terraform del Blob
anterior. Se verificó `create_before_destroy`; no hubo cambios al grupo,
Storage Account, Function App como recurso, colas, Key Vault, alertas o roles.
Se aplicó exactamente el plan guardado: `1 added, 1 changed, 1 destroyed`.
Después, trigger sync pasó, la Function reportó `Running`/HTTPS-only,
`DEPLOYMENT_PACKAGE_SHA256` coincidió con el artefacto, `/api/health` devolvió
HTTP 200 y el plan Terraform normal quedó `No changes`.

El E2E post-release, 13/10/2026, recorrió ERP local → outbox → Azure
Queue/Function → conciliación ERP. Venta
`evt-058124ac95d442238e45fc83cc197a77` terminó `demo_fulfillment_completed`;
la recepción `evt-0ac5e6b060cd4dea98644b6b05eb8ee9` terminó
`demo_restock_completed`. El script validó que el stock final fuera exactamente
la línea base. Los eventos sintéticos permanecen en auditoría; la base SQLite
local se eliminó.

El ARM de Storage confirma soft delete activado por 7 días. El comando de
listado data-plane de blobs eliminados no estuvo disponible con la identidad
CLI actual, por lo que no afirmamos haber probado recuperación remota. La copia
ZIP previa sí está preservada localmente. El E2E no partió de EC2 y el ledger
sigue siendo ficticio. `requirements.lock`, auditoría y dry-run de instalación
Linux Python 3.11 pasaron; no se modificaron componentes de AWS.

## Revalidación posterior al despliegue — 04:37 America/Chicago

- Azure for Students aparece `Enabled` y la Function
  `tangama-wms-261008` aparece `Running`, `httpsOnly=true`.
- La cuenta de almacenamiento informa borrado reversible de Blob habilitado
  por 7 días; el versionado de blobs está deshabilitado.
- Se ejecutaron dos empaquetados independientes de la Function. Los ZIP
  resultaron byte-idénticos, SHA-256
  `643750B5497FEC9705BC7FE04742060FEC48F947AA81D6C7E86C5FAB6758A3BE`.
- Las 21 pruebas unitarias de Azure Functions pasaron con el entorno Python
  fijado por el proyecto.
- El plan autenticado solo propuso el release del artefacto: crear el Blob
  identificado por el digest nuevo antes de retirar el antiguo, actualizar en
  el sitio la configuración de la Function y eliminar el Blob anterior del
  recurso Terraform (`1 to add, 1 to change, 1 to destroy`). No hubo cambios de
  Resource Group, Storage Account, Function App como recurso, red, colas,
  Key Vault o alertas.
- El guard del plan validó esas acciones exactas y rechazó cualquier otra
  mutación. Se aplicó el plan guardado en `%TEMP%`; Terraform completó con 1
  alta, 1 cambio y 1 destrucción del Blob anterior. El nuevo Blob está
  identificado por el SHA-256 del paquete. El anterior queda bajo soft delete
  de 7 días y además se conservó una copia local
  `artifacts/azure_function_package_16638E41DA4C_previous.zip` (hash
  `16638E41DA4C8CE27F7A1DC1B56C1478C831A3C36DEF19ABD9984B3002EB525B`).
- Un `terraform plan` posterior al apply terminó con `No changes`; el estado
  remoto y el HCL quedaron reconciliados para este release.
- Se sincronizaron triggers; `az functionapp show` reportó `Running` y
  `httpsOnly=true`, y HTTPS `/api/health` devolvió `ok`.
- Después del despliegue, el E2E ERP local → Azure Queue/Function pasó:
  `evt-46a72c6479634d05ba50ec5c13af32b1` terminó
  `demo_fulfillment_completed`; `evt-74641a0938814524a8cb17edc0b34f0e`
  terminó `demo_restock_completed`. La lectura autenticada de inventario y
  ambos estados persistidos devolvió modo `demo-inventory-ledger` y el SKU
  ficticio `SKU-ARROZ-001` en 24 unidades. La SQLite local de prueba fue
  temporal y el smoke no usó la instancia AWS.

## Alcance y límites

El release está publicado y probado. El despliegue reemplazó el objeto Blob
anterior, que es recuperable por hasta 7 días mediante soft delete; esto no
equivale a versionado permanente ni a una prueba de restauración. La copia ZIP
local protege el artefacto anterior, pero no sustituye una restauración del
Blob remoto. El E2E de las 03:54 valida el release previo; el E2E posterior
documentado arriba valida el release nuevo.

El empaquetador excluye bytecode de Python, fija el timestamp y crea un ZIP
temporal validado antes de reemplazar atómicamente el artefacto destino. Una
prueba fallida del reemplazo atómico en Windows detectó que el nombre de
respaldo no podía ser nulo; se corrigió y se repitió el build preservando el
paquete anterior. Dos builds independientes resultaron byte-idénticos. La
prueba directa `python -m pytest` no se usó porque el Python global no incluía
pytest; la suite aprobada se ejecutó con el `app/.venv` fijado por el proyecto
(`unittest discover`, 21 pruebas). La compuerta completa local aprobó 81
pruebas, auditoría de dependencias, build web, CloudFormation y validación de
Terraform.

## Próximo paso seguro

Mantener la retención de paquetes alineada con el límite de recuperación de 7
días o activar versionado si el costo/alcance lo justifica; ejecutar y
documentar una restauración de paquete/Blob en un entorno controlado antes de
afirmar rollback probado. El WMS sigue siendo un ledger ficticio, no inventario
empresarial real. La prueba ejecutada conecta el ERP local con Azure, no se
originó en EC2 y no demuestra VPN privada.
