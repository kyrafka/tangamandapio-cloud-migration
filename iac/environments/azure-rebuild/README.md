# Reconstrucción del WMS de demostración en Azure

La comprobación más reciente, 16/10/2026 08:08 UTC, confirma la Function
`Running`/HTTPS-only, health HTTP 200 con TLS válido y el componente Application
Insights `Succeeded`; ARM enumera la Function, colas, contenedores, Key Vault,
alertas y recursos de monitorización. El E2E AWS→Azure pasó a las 08:00 con
venta `completed_demo`, compra `received_demo`, dos eventos entregados y ledger
sintético restaurado 10→10. Application Insights correlacionó ambos `event_id`
con ejecuciones exitosas del worker (`resultCode=0`). Admin reconcilió 57/57
eventos y cero pendientes. Terraform remoto `plan -refresh-only` con
`rebuild.tfvars.example` y el plan normal con el archivo local protegido de
receptores terminaron `No changes` a las 08:07; no se ejecutó `apply`. Véase el
[corte cloud actual](../../../evidence/current/CLOUD-REVALIDATION-2026-10-16-0808UTC.md)
y la evidencia de despliegue y sondas.

## Revalidación viva — 16/10/2026, 02:40 UTC

La suscripción `Azure for Students` está `Enabled`; `tangama-wms-261008` sigue
`Running`, HTTPS-only y `/api/health` devuelve 200. `tangama-wms-ai` se enlaza
con `tangama-ops-law`; en la última hora Application Insights registró 94
requests (códigos 200/202 y guardas 400 esperadas), y las alertas métricas 5xx y
latencia y el Action Group están habilitados. El E2E completo iniciado desde
EC2 en AWS entregó venta/recepción sintéticas a Azure y restauró el saldo del
ledger a 10; no representa inventario físico. No hubo alerta disparada en esta
pasada ni ruta privada AWS–Azure. Detalle en la
[revalidación cloud](../../../evidence/current/CLOUD-REVALIDATION-2026-10-16-0240UTC.md).

## Revalidación más reciente — 14/10/2026, 08:14–08:15 America/Chicago

Terraform 1.16.0 volvió a consultar ARM con `rebuild.tfvars.example` y el
archivo local de receptores de alertas; el plan terminó `No changes` (salida
0). No se guardó un plan aplicable ni se ejecutó `apply`. La Function seguía
`Running` y las reglas 5xx/latencia y los dos receptores de correo quedaron
confirmados en la lectura CLI de las 08:08. La confirmación de recepción del
usuario se refiere a una prueba SNS de AWS, no a una entrega Azure; aquí no se
disparó la regla ni se archivó correlación de entrega independiente.
La evidencia está en [el plan Terraform](../../../evidence/current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md)
y la [revalidación cloud](../../../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

## Revalidación más reciente — 14/10/2026, 07:16–07:18 America/Chicago

Azure for Students está `Enabled`; ARM reportó el grupo
`rg-tangamandapio-rebuild-wus` como `Succeeded` con diez recursos. La Function
`tangama-wms-261008` respondió HTTP 200 en `/api/health`. Terraform 1.16.0,
con `rebuild.tfvars.example` y el archivo local de receptores de alertas,
consultó ARM y terminó `No changes` (salida 0). No hubo `apply`, no se envió un
evento de procesamiento ni se probó la entrega de alertas. Esto confirma el
estado del root `azure-rebuild` en este corte; no demuestra un WMS comercial ni
conectividad privada con AWS. Véase la [evidencia del plan](../../../evidence/current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

## E2E y barreras de ingreso — 14/10/2026, 07:43–07:49 America/Chicago

El smoke opt-in verificó HTTP 401 sin Function key, 400 para productor no
autorizado y que el ID rechazado siguiera `pending`, sin persistencia. Después
completó venta y recepción compensatoria en el ledger demo, con stock igual a
la línea base. Application Insights registró seis recepciones HTTP 202, un
rechazo 400 y seis ejecuciones del worker `resultCode=0` en tres corridas. La
cola poison informó conteo cero antes y después sin exponer mensajes; no se usó
EC2/RDS ni se cambió infraestructura. Véase la
[evidencia E2E](../../../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md).

## E2E compensado — 14/10/2026, 07:29 America/Chicago

El arnés opt-in del artefacto local completó una venta y su recepción
compensatoria en el ledger demo, y verificó que el stock regresara a la línea
base. Application Insights mostró cuatro respuestas HTTP 202 y cuatro
ejecuciones del worker con `resultCode=0` para dos corridas en la última hora.
La cola poison reportó conteo aproximado cero antes/después; no se leyeron ni
modificaron mensajes. Los dos eventos de la última corrida permanecen en la
auditoría de Azure. No se usó EC2/RDS ni se cambió infraestructura. Véase la
[evidencia E2E](../../../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md).

## Revalidación más reciente — 14/10/2026, 06:29 America/Chicago

La Function `tangama-wms-261008` está `Running`, HTTPS-only y `/api/health`
respondió 200. Application Insights consultado a las 06:29 mostró en la última
hora 3 solicitudes `health` sin fallos, 9 trazas que mencionan
`process_fulfillment_message`, 6 que mencionan `receive_fulfillment_event`, 0
errores de severidad y 0 excepciones; las menciones de trazas no equivalen a
invocaciones. Terraform actualizó únicamente `tangama-ops-ag` para asignar dos
receptores de correo; ambos siguen `Enabled` y el plan posterior terminó
`No changes`. Las reglas 5xx/latencia siguen habilitadas, pero no se generó una
alerta ni se probó la entrega. Los correos
no se guardan en Git: `alert_email_receivers` se conserva en el archivo local
ignorado `alert-recipients.local.tfvars`. Si se reconstruye desde cero o en
otra máquina, proporcione esa variable desde un archivo local protegido; su
valor por defecto está vacío.

La cuenta `Azure for Students` sigue `Enabled`; esto no informa el crédito
restante. No se cambió el paquete de la Function ni se desplegó el resto de la
infraestructura en este corte.

## Revalidación más reciente — 14/10/2026, 04:30–04:31 America/Chicago

Terraform 1.16.2 y un plan normal con salida detallada consultaron los recursos
administrados en Azure Resource Manager sin encontrar cambios (`No changes`,
salida 0). No se aplicó nada ni se guardó un plan. El state local permanece
ignorado por Git. Véase [la evidencia del plan del 14/10](../../../evidence/current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

## Revalidación más reciente — 13/10/2026

La suscripción Azure for Students está `Enabled`. El paquete Function
`6eea3b6a…` quedó publicado; tras el apply, la Function informó
`Running`/HTTPS-only, el SHA configurado coincide, `/api/health` devolvió HTTP
200 y el plan Terraform terminó `No changes`. El E2E compensado posterior
aprobó. La prueba de blobs eliminados no estuvo accesible por data plane; ARM
confirma retención de 7 días y el ZIP anterior se conserva localmente. Véase
[`AZURE-ERP-E2E-2026-10-13.md`](../../../evidence/current/azure/AZURE-ERP-E2E-2026-10-13.md).

## Estado comprobado — 12/10/2026

La sesión CLI apunta a **Azure for Students**, estado `Enabled`; eso no revela
el saldo restante. El Resource Group `rg-tangamandapio-rebuild-wus` está activo
en `westus`. La Function `tangama-wms-261008` está `Running` y pasó una prueba
funcional viva; ver
[`AZURE-RECONSTRUCCION-2026-10-12.md`](../../../evidence/current/azure/AZURE-RECONSTRUCCION-2026-10-12.md).

## Corte posterior — 13/10/2026

El hash `643750B5…` pertenece a un corte previo, pero su `function_app.py` no
coincide con el árbol fuente vigente. El Blob revalidado como activo fue
`function-0e1f153f…`; su copia local sí coincidía con el código de ese corte.
El paquete nuevo `6eea3b6a…` incluye locks y dependencias Linux verificadas;
fue publicado y revalidado en el corte actual descrito arriba. La evidencia de
ese plan anterior se conserva para auditoría histórica:
[`AZURE-PLAN-PAQUETE-2026-10-13.md`](../../../evidence/current/azure/AZURE-PLAN-PAQUETE-2026-10-13.md).
El plan posterior a la publicación terminó `No changes`.

El E2E conectó el release ERP **local** con Azure; no partió de EC2 y no
demuestra VPN ni WMS empresarial.

El state local actual administra el grupo vivo y puede contener configuración
operativa; no se debe copiar ni versionar junto con `terraform.tfstate.backup`
o planes guardados. `rebuild.tfplan` corresponde a un ciclo anterior; no lo
apliques. El ZIP del ejemplo debe llamarse
`azure_function_package-<SHA256>.zip`; una prueba local compara su hash y los
archivos de fuente. El builder usa `requirements.lock`, instala con hashes para
Python 3.11/Linux y no sobrescribe artefactos existentes. Si cambia la fuente,
vuelve a ejecutar el builder y actualiza la ruta SHA en el archivo de variables
antes de planificar.

## Diseño del entorno

El módulo crea el Resource Group, Storage Standard LRS, contenedores Blob
privados, Queue normal y poison, Key Vault con RBAC, Function Linux Consumption
(`Y1`), Log Analytics, Application Insights, alertas y permisos mínimos de
datos para la identidad de la Function. Cada paquete de la Function se guarda
en un Blob inmutable, identificado por SHA-256, y se monta mediante URL privada
con la identidad administrada (`Storage Blob Data Reader`), sin SAS persistente.
La cola poison solo expone su conteo aproximado por una ruta protegida con clave
de Function; nunca devuelve cuerpos de mensajes. La identidad no tiene acceso a
secretos de Key Vault mientras la aplicación no los consuma.

La Function requiere HTTPS y deja deshabilitada la autenticación básica de
publicación FTP/SCM. El paquete se publica desde Terraform al Blob privado; la
identidad administrada lo descarga al iniciar. Este método evita Kudu/SCM y SAS
con vencimientos, y se ajusta a Linux Consumption.

Log Analytics y Application Insights conservan 30 días y tienen un tope de
ingestión de 0,1 GB/día como salvaguarda del laboratorio. Si se alcanza, la
recolección de telemetría puede parar hasta el siguiente reinicio diario; el
tope no sustituye el filtrado de registros ni garantiza un máximo exacto de
cargos.

El WMS continúa siendo un **ledger ficticio**: valida eventos con SKU/cantidad,
idempotencia y stock de laboratorio; no integra inventario comercial.

## Procedimiento de reconstrucción

Primero confirma `az account show` y el inventario de recursos. No ejecutes este
procedimiento en otra suscripción sin revisar sus nombres y costos. No uses
`az functionapp deployment source config-zip` en este entorno: la Function es
Linux Consumption, y el release se monta desde un Blob privado por identidad.

```powershell
& .\tools\terraform-1.16.0\terraform.exe fmt -check -recursive
& .\iac\scripts\package_azure_function.ps1
Push-Location iac\environments\azure-rebuild
& ..\..\..\tools\terraform-1.16.0\terraform.exe validate
& ..\..\..\tools\terraform-1.16.0\terraform.exe plan -var-file=rebuild.tfvars.example -var-file=alert-recipients.local.tfvars -out=rebuild-current.tfplan
& ..\..\..\tools\terraform-1.16.0\terraform.exe show -no-color rebuild-current.tfplan
```

Solo si el plan apunta a la suscripción esperada y no reemplaza ni destruye
recursos de infraestructura se puede publicar. Para un cambio de código es
esperable que Terraform cree el Blob con el nuevo SHA-256, actualice la Function
en el sitio y reemplace el Blob content-addressed anterior. El módulo usa
`create_before_destroy`; ambos paquetes coexisten durante el cambio y el Blob
anterior queda recuperable mediante soft delete de Storage por 7 días. Conserva
también una copia local del ZIP previo. Cualquier destrucción adicional, o una
reposición de Resource Group, Storage Account, Function App o Key Vault, bloquea
la publicación hasta investigar el plan.

```powershell
& ..\..\..\tools\terraform-1.16.0\terraform.exe apply rebuild-current.tfplan
az rest --method post --url "https://management.azure.com/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-tangamandapio-rebuild-wus/providers/Microsoft.Web/sites/tangama-wms-261008/syncfunctiontriggers?api-version=2016-08-01" --output none
Pop-Location
```

Después se comprueban estado `Running`, `/api/health`, sincronización de triggers
y la cola poison con una invocación autorizada y clave obtenida de forma segura;
no se imprime ni se guarda la clave en el repositorio. Repite el smoke E2E de
venta/compensación e inventario, conserva la copia del ZIP anterior y confirma
que el Blob previo sigue recuperable. Las pruebas locales solas no sustituyen
la validación viva. No destruyas el grupo ni purgues el Key Vault sin una
revisión explícita de los datos que se conservarán.

## Release actualizado — 14/10/2026

La Function viva usa el paquete inmutable
`azure_function_package-ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27.zip`
(SHA-256 `ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27`).
`rebuild.tfvars.example` apunta ahora a esa misma versión. El plan posterior al
apply se comprobó contra ARM y quedó `No changes`. El Blob previo
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065.zip` fue
retirado por Terraform al actualizar la Function; la cuenta mantiene soft
delete de blobs por 7 días y el ZIP anterior también está conservado localmente.
No se ha probado una restauración del Blob eliminado. El E2E post-deploy está
en [la evidencia Azure](../../../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md).

## Candidato local de catálogo sintético — 14/10/2026

El paquete inmutable recién generado desde `app/azure_function` es
`azure_function_package-364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d.zip`
(SHA-256 `364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d`).
`rebuild.tfvars.example` apunta a este candidato y el validador comprueba que el
ZIP coincide con el código fuente. El paquete anterior `ecb71ccd…` es el último
que consta desplegado; la Function viva no cambia hasta revisar el plan
Terraform y aplicar únicamente el cambio de paquete. No afirmar el despliegue
del catálogo hasta verificar el hash live y repetir el smoke post-deploy.

## Estado vigente posterior al despliegue — 14/10/2026, 11:58 America/Chicago

La nota de candidato inmediatamente anterior quedó superada. Se revisó y aplicó
un plan Terraform que solo actualizaba el paquete de la Function y su Blob
content-addressed (1 add, 1 change, 1 destroy del Blob anterior, recuperable
por soft delete de 7 días). El paquete activo es
`azure_function_package-364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d.zip`;
el plan posterior terminó `No changes`. Health respondió 200 y la ruta de
catálogo actualizó metadatos de un SKU demo sin cambiar `on_hand`. El smoke de
venta/recepción Queue/Function procesó datos sintéticos y restauró el ledger a
la línea base. Evidencia: [CATALOGO-SINTETICO-IMPORT-2026-10-14](../../../evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md).
El smoke de negocio usó la aplicación local y SQLite; no equivale a una venta
autenticada desde las EC2/RDS. No se desplegó infraestructura adicional.
