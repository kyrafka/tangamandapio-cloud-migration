# Reconstrucción Azure y prueba viva — 12/10/2026

**Tipo de evidencia:** inventario consultado por Azure CLI, estado Terraform y
respuestas HTTP observadas directamente. Este archivo es un registro escrito;
no es una captura de Chrome ni de la consola del portal.

## Suscripción e infraestructura

- Suscripción seleccionada: **Azure for Students**, estado `Enabled`. La consulta
  no expone el saldo disponible; no se afirma que el crédito sea suficiente ni
  que el costo sea cero.
- Resource Group: `rg-tangamandapio-rebuild-wus`, región `westus`.
- Function App: `tangama-wms-261008`, estado `Running`, hostname
  `tangama-wms-261008.azurewebsites.net`, `https_only=true`.
- Terraform aplicó **14 recursos**, con `0 changed` y `0 destroyed`; la siguiente
  ejecución de `terraform plan -detailed-exitcode` terminó con código 0 (sin
  drift). `az resource list` mostró 10 recursos de Azure en el inventario del
  Resource Group; las asignaciones RBAC y recursos de datos hijos pueden no
  aparecer como recursos superiores.
- Se refrescó el plan contra Azure el 12/10 después de la prueba ERP→WMS y
  nuevamente tras la puerta de calidad actual: `No changes`, código de salida 0;
  no se aplicaron cambios cloud.
- Azure CLI fue `2.90.0`. El paquete ZIP existente se comparó byte por byte en
  sus archivos principales (`function_app.py`, `host.json` y
  `requirements.txt`) con `app/azure_function`; los tres coincidieron. Se
  publicó con `az functionapp deployment source config-zip`, usando la sesión
  Microsoft Entra, sin activar credenciales básicas de publicación.

## Configuración de seguridad/costo observada

- HTTPS obligatorio y mínimo TLS del Storage `TLS1_2`; FTPS `Disabled`.
- Políticas de publicación básica FTP y SCM: `false`.
- Storage con `allowBlobPublicAccess=false`; el contenedor `fulfillment-events`
  tiene acceso público no configurado (privado por defecto).
- La identidad administrada de la Function tiene roles de datos limitados al
  contenedor Blob de eventos y a la Queue `fulfillment-events`.
- Hay dos reglas de métricas (`Http5xx` y latencia) y un Action Group activo,
  pero **sin receptores de email, SMS o webhook**; las alertas no notifican a
  una persona o sistema. Este pendiente requiere un destinatario autorizado.
- Application Insights y Log Analytics conservan 30 días y tienen topes de
  ingestión de `0.1 GB/día` como salvaguarda. Si se alcanza el límite, se puede
  interrumpir la telemetría; el límite no es un costo máximo exacto.
- La consulta KQL a Application Insights (`requests`, últimas 48 h) devolvió
  `process_fulfillment_message`: **6 ejecuciones, 0 fallos observados**;
  `receive_fulfillment_event`: **7, 0**; `fulfillment_status`: **21, 0**;
  `demo_inventory`: **9, 0**; `health`: **1, 0**. Esto acredita actividad
  observada del trigger de Queue y de la Function, no solo el estado `Running`.
  Una enumeración de solo lectura con Entra ID encontró únicamente
  `fulfillment-events`; no existía `fulfillment-events-poison` en ese corte.
  Esto no prueba cómo se alertaría o recuperaría un mensaje poison futuro.
- El Key Vault está provisionado con RBAC, pero no contiene un secreto de
  integración creado en esta ejecución y la Function no tiene permiso para
  leerlo. No se afirma uso real de Key Vault por el flujo.

## Prueba funcional viva

La clave de Function se obtuvo en memoria desde Azure CLI y no se guardó ni se
mostró. El evento `lab-stock-20261012` fue sintético y utilizó el productor
permitido `aws-order-core` y el SKU de laboratorio `SKU-ARROZ-001`.

| Comprobación | Resultado observado |
|---|---|
| `GET /api/health` sin autenticación | HTTP 200, `status=ok` |
| POST al endpoint de fulfillment sin Function key | HTTP 401 |
| Productor `unknown-producer` con clave válida | HTTP 400 |
| Primer evento con SKU/cantidad | HTTP 202, `queued` |
| Reintento con mismo ID y cuerpo | HTTP 202, `queued_duplicate` |
| Consulta de resultado tras procesar la Queue | `demo_fulfillment_completed` |
| Inventario de laboratorio posterior | Arroz: 25 → 24; se descontó una sola unidad |
| Modo de inventario | `demo-inventory-ledger`; `is_real_erp=false` |

La prueba demuestra el procesamiento de evento y su idempotencia **dentro de
Azure**, sobre datos ficticios. No prueba que la aplicación AWS originara el
evento en esta ejecución ni que exista una conexión privada AWS–Azure. La
Queue y la Function reemplazan el flujo manual de demostración, no un WMS
comercial ni un ERP conectado a existencias reales.

## Prueba viva ERP → Azure — 12/10/2026

Se ejecutó `tests/run_live_azure_erp_smoke.py` con opt-in explícito, bases
SQLite temporales y una clave de Function mantenida en memoria. Se recorrió el
módulo ERP de `app/src` y se repitió con el artefacto local
`app/aws_release/current`: cliente/producto de laboratorio → venta con
SKU/cantidad → despacho automático mediante outbox → Azure Queue/Function →
consulta y reconciliación del resultado ERP. En ambos recorridos la venta
produjo `demo_fulfillment_completed` y descontó una unidad. Una recepción
compensatoria se procesó por el mismo contrato y el inventario ficticio terminó
exactamente en el valor inicial. Los eventos sintéticos permanecen en el
almacenamiento de auditoría Azure; no se borraron.

La prueba se puede repetir desde PowerShell con la CLI de Azure autenticada:
establecer `TANGAMA_LIVE_AZURE_SMOKE=I_ACKNOWLEDGE_DEMO_STOCK_MUTATION` solo
durante `python tests/run_live_azure_erp_smoke.py` y quitarla al terminar. El
script nunca muestra ni guarda la clave de Function; la puerta local comprueba
su sintaxis y que se niegue a correr sin ese opt-in, sin llamar a la nube.

Esto demuestra que el ERP fuente y el paquete local preparado para AWS
intercambian el contrato de punta a punta con Azure. No demuestra que la
instancia AWS desplegada originara el evento, que tenga el mismo artefacto ni
que exista conexión privada entre VPC/VNet. `demo-inventory-ledger` sigue
siendo un WMS académico ficticio.

## Pendientes abiertos

1. Restaurar autenticación del AWS Academy Lab y desplegar/validar AWS antes de
   probar un pedido completo originado por la instancia AWS.
2. Implementar y probar la red objetivo AWS VPC ↔ Azure VNet/VPN; Azure Functions
   sobre Consumption usa endpoint público y no equivale a una VNet.
3. Configurar un destinatario aprobado para el Action Group y demostrar alerta,
   notificación y recuperación.
4. Capturar pantallas directas de Chrome/portales con fecha y contexto, sin
   credenciales ni datos personales.
5. Medir costos reales, disponibilidad, escalado, RTO/RPO y recuperación antes
   de asignar puntos adicionales a la rúbrica.

El grupo queda activo para continuar las pruebas y puede incurrir cargos. La
suscripción `Azure for Students` está `Enabled`, pero ese estado no demuestra
que conserve crédito disponible. El 12/10 se intentó consultar Cost Management
en el ámbito del Resource Group; la consulta REST respondió `BadRequest` por
definición de conjunto de datos no válida. Además, `az consumption usage list`
devolvió 169 filas (161 con la etiqueta del proyecto), pero `pretaxCost` vino
como `None` y no incluyó moneda. Por tanto no hay un importe verificable ni se
afirma que el costo sea cero; revisar Cost Analysis en el portal con el ámbito
y permisos correctos antes de presupuestar.

La puerta local se volvió a ejecutar después de ampliar `tests/run_local_quality.ps1`
para incluir también `iac/environments/azure-rebuild`: **68 pruebas aprobadas**,
auditorías Python y frontend aprobadas, CloudFormation validada, y Terraform
`fmt`/`validate` aprobados en los entornos configurados. La ejecución no aplicó
infraestructura ni cambió recursos en Azure o AWS.

## Revalidación de red y sesión — 12/10/2026 (solo lectura)

Azure CLI renovó un token para `management.azure.com`; `az account show` confirmó
una suscripción `Enabled`. El inventario volvió a mostrar el Resource Group
`rg-tangamandapio-rebuild-wus` y 10 recursos. La Function
`tangama-wms-261008` está `Running`, `httpsOnly=true`, y su plan
`tangama-wms-plan` es SKU `Y1` / `Dynamic`. La enumeración de recursos no mostró
VNet ni Virtual Network Gateway en la suscripción; por tanto no hay una VPN
AWS–Azure desplegada en este corte. No se creó ni modificó ningún recurso Azure.
La sesión web del portal y el token CLI son contextos distintos; aquí se usó
Azure CLI autenticado, no una captura del portal.

## Revalidación viva de salud y flujo ERP → Azure — 12/10/2026

Corte local `America/Chicago` 20:07 del 12/10 (01:07 UTC del 13/10). La consulta
directa a `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió
HTTP 200 con `status=ok`. La Function seguía `Running` y `httpsOnly=true`.

Se volvió a ejecutar, con opt-in explícito, `tests/run_live_azure_erp_smoke.py`.
El proceso local que usa el artefacto `app/aws_release/current` creó una venta
sintética de una unidad `SKU-ARROZ-001`, el outbox la entregó a Azure Queue,
la Function completó el evento y el ERP reconcilió el resultado. Una recepción
compensatoria recorrió la misma cola y restauró el inventario ficticio al
valor inicial. Resultado: `LIVE_E2E=PASSED`; blobs/eventos de auditoría
sintéticos permanecen en Azure. No se originó desde EC2 ni se modificó
infraestructura cloud.

Application Insights confirmó en las últimas 24 horas 15 solicitudes y 0
fallos observados: `process_fulfillment_message` 2, `receive_fulfillment_event`
2, `fulfillment_status` 6, `demo_inventory` 4 y `health` 1. Esto acredita
actividad reciente de la Function y el ciclo de prueba dentro de Azure, no una
VPN privada ni el flujo desde la instancia AWS.

Después de la prueba se ejecutó `terraform plan -detailed-exitcode` con el
state local vigente y `rebuild.tfvars.example`: código 0, `No changes. Your
infrastructure matches the configuration.` Fue una consulta/plan, no un apply;
no se cambió infraestructura Azure.

## Cola poison y publicación privada con identidad — 12/10/2026

Corte `America/Chicago` 20:40. Se agregó a la configuración explícita de Azure
Functions `maxDequeueCount=5`, visibilidad de 60 s y lotes pequeños. Terraform
creó la cola `fulfillment-events-poison` y asignó `Storage Queue Data Reader`
a la identidad administrada de la Function. La ruta autenticada
`/api/wms/poison-queue` devuelve solo el conteo aproximado, nunca los mensajes.
Prueba viva inicial: `/api/health` HTTP 200; la ruta poison sin clave HTTP 401;
con clave de Function HTTP 200, `status=ok`, conteo `0` y
`payloads_exposed=false`.

Linux Consumption no pudo publicarse por Kudu/SCM desde este equipo: la solicitud
directa de red al endpoint SCM agotó 15 s y el primer `config-zip` no confirmó
despliegue. Para evitar dependencia del push, se alineó Terraform con el plan
real: paquete ZIP inmutable nombrado por SHA-256 en Blob privado, lectura por
identidad administrada y `WEBSITE_RUN_FROM_PACKAGE` sin SAS. Se aplicó el plan
revisado: 3 recursos añadidos, 1 actualizado y 0 destruidos. El endpoint nuevo
respondió 401 sin clave y 200 autenticado después de sincronizar triggers por
Azure Resource Manager; health y estado de Function permanecieron correctos.
La lista de funciones de Azure incluyó `process_fulfillment_message`, así que
el trigger de Queue quedó indexado tras la sincronización. Con conteo poison 0
y sin mensajes visibles en la cola principal, se envió un mensaje sintético con
checksum inválido (`poison-test-…`). El runtime lo reintentó y lo movió a
`fulfillment-events-poison`; el conteo aproximado llegó a 1 después de unas 25
consultas (aprox. seis minutos). El mensaje se leyó solo para verificar el
marcador sintético y se borró con su pop receipt. Verificación final: poison
0 y cola principal sin mensajes visibles. Esto prueba el reintento y el camino
poison en Azure, pero no un fallo de negocio real ni recuperación AWS→Azure.

La puerta completa `tests/run_local_quality.ps1 -ValidateTerraform` aprobó
72 pruebas en su corte original, auditorías de dependencias, build frontend,
CloudFormation y Terraform format/validate. Tras la migración del paquete se repitieron unit tests Azure
(21/21) y `terraform validate`; el plan aplicado fue no destructivo. La
integración AWS→Azure y la VNet/VPN privada siguen sin validarse. A las 21:03
hora local, AWS STS aceptó la terna guardada en `default` tras compararla en
memoria con la suministrada; no se imprimió la identidad. Una consulta de
inventario posterior encontró cero EC2, balanceadores/target groups y RDS en
`us-east-1`; no se modificaron recursos. Véanse
[`AWS-REVALIDACION-STS-2026-10-12.md`](../aws/AWS-REVALIDACION-STS-2026-10-12.md)
y [`AWS-INVENTARIO-2026-10-12.md`](../aws/AWS-INVENTARIO-2026-10-12.md).

La puerta local volvió a ejecutarse tras implementar guardas de conservación de
RDS y recuperación idempotente del admin: 74 pruebas unitarias, auditoría de
dependencias, build, cfn-lint, Terraform format/validate y prueba simulada de
`destroy.sh` aprobaron. No se hicieron cambios ni se ejecutaron pruebas en
Azure durante esa puerta.

## Revalidación posterior — 12/10/2026, aproximadamente 21:46 America/Chicago

Azure CLI volvió a mostrar la suscripción `Enabled` y el grupo
`rg-tangamandapio-rebuild-wus`. El inventario confirmó Storage, Key Vault, Log
Analytics, Application Insights, la Function `tangama-wms-261008` y su plan;
la Function estaba `Running` con `httpsOnly=true`. La sonda pública
`/api/health` respondió HTTP 200.

Se repitió `tests/run_live_azure_erp_smoke.py` con su opt-in: el portal release
AWS ejecutado localmente registró socios temporales, publicó una venta
sintética de `SKU-ARROZ-001` en el outbox y Azure respondió
`demo_fulfillment_completed`. La recepción compensatoria procesó
`demo_restock_completed` y devolvió el ledger ficticio al stock de partida.
Resultado `LIVE_E2E=PASSED`; los eventos de auditoría sintéticos quedan en
Azure. Esto acredita el flujo local→Azure, no una llamada originada desde AWS.

En la consulta final de Application Insights de las últimas 24 horas se
observaron 114 solicitudes, de las cuales 5 constaban como fallidas. El
desglose atribuyó 15 invocaciones a `process_fulfillment_message`, 5 marcadas
como no exitosas; las solicitudes de estado poison, inventario y estado de
fulfillment mostraron 200 y las entregas de eventos 202. La tabla de
excepciones agregada indicó 10 `RpcException`. Tras el smoke test, la ruta
autenticada `/api/wms/poison-queue` volvió a devolver HTTP 200, `status=ok` y
conteo aproximado 0.
Una clasificación local que no imprimió textos ni cuerpos encontró 10
`RpcException` con señal de checksum/mismatch; esto coincide con las 5
invocaciones fallidas y con el mensaje de checksum inválido de la prueba poison
anterior (máximo de cinco entregas). Es consistente con aquel ensayo sintético,
pero no se confirmó correlación por `operation_Id`, así que se conserva como
fallo histórico observado, no como error productivo demostrado ni como cero
fallos. No se leyeron ni archivaron cuerpos de mensajes ni textos de excepción.

Tras el smoke test se ejecutó un `terraform plan -refresh=true -detailed-exitcode`
contra la sesión Azure activa, el state local y `rebuild.tfvars.example`. Resultado
de Terraform: código 0, `No changes. Your infrastructure matches the
configuration.` No se guardó un plan ni se aplicaron cambios.

En el corte previo (aprox. 21:46), AWS Academy mostraba `Lab terminated` / `No
running instance` y las operaciones RDS eran denegadas por una política
explícita. Ese estado quedó superado por la revalidación AWS de las 23:57 que
se documenta abajo: el token nuevo funciona, aunque el permiso de modificación
de RDS sigue denegado.

## Revalidación actual — 12/10/2026, 23:57 America/Chicago

La sesión Azure CLI muestra la suscripción `Enabled`; el Resource Group
`rg-tangamandapio-rebuild-wus` respondió `Succeeded` y la Function
`tangama-wms-261008` respondió `Running`. La URL pública de health devolvió
HTTP 200 con `{"status":"ok","service":"tangamandapio-wms"}`. El inventario
del grupo devolvió diez recursos superiores. Una consulta a toda la suscripción
filtrada por `Microsoft.Network/` no devolvió filas; no hay VNet, gateway ni
conexión VPN en la suscripción al corte. El endpoint de la Function sigue
siendo público, aunque exige autenticación para las rutas operativas.

Se volvió a ejecutar `tests/run_live_azure_erp_smoke.py` con su opt-in. El
artefacto local `app/aws_release/current` registró una venta sintética de una
unidad, que Azure procesó como `demo_fulfillment_completed`, y una recepción
compensatoria `demo_restock_completed`. El script comprobó que el stock ficticio
final coincide con el baseline. Resultado `LIVE_E2E=PASSED`; los eventos
sintéticos de auditoría permanecen en Azure. El flujo corrió en un proceso
local con SQLite temporal, no desde EC2 y no cambió infraestructura cloud.

En esta misma revisión AWS STS aceptó la terna nueva guardada en `default`,
RDS enumeró cero instancias y el snapshot cifrado del proyecto siguió
`available`. Una comprobación de autorización de `rds:ModifyDBInstance` contra
un ID deliberadamente inexistente devolvió `AccessDenied`; no se creó ni
modificó recurso. No se lanzó una nueva restauración RDS facturable. La puerta
local completa aprobó 79 pruebas, auditorías de dependencias, build frontend,
CloudFormation, Terraform formato/validación y dos pruebas mock de VPN, sin
`apply`.

Esta revalidación actualiza el estado de red/Function y el smoke test del corte
23:57; las consultas de Application Insights y de costos descritas arriba
pertenecen a cortes anteriores y no se presentan como métricas actuales. Este
registro sigue siendo CLI/HTTP, no una captura de Chrome o del portal Azure.
