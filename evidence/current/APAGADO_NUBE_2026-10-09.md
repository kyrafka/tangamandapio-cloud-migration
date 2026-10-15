# Apagado de nube — 09/10/2026

## Resultado final

- AWS `us-east-1`: eliminados los stacks `tangamandapio-live-20261005` y
  `tangamandapio-voice-recordings`. La instancia RDS, buckets del proyecto,
  parámetro SSM y secreto de Secrets Manager también se retiraron. Consultas
  finales no encontraron stacks, instancia RDS, buckets ni parámetro del
  proyecto; Secrets Manager aceptó eliminar el secreto sin periodo de
  recuperación (la última consulta mostraba su marca `DeletedDate`). No quedan
  backups automáticos de RDS.
- Se conserva únicamente el snapshot final
  `tangamandapio-live-20261005-final-20261009192408`: `available`, cifrado,
  20 GB. Puede generar un costo bajo de almacenamiento; no se borró para
  preservar la recuperación de PostgreSQL.
- Azure: destrucción Terraform completada (`15 destroyed`); el grupo
  `rg-tangamandapio-rebuild-wus` ya no existe y el state local quedó vacío.
  No se purgó la copia soft-deleted de Key Vault para mantener su periodo de
  recuperación.
- El servidor local está detenido y no hay proceso escuchando en el puerto
  `8080`.
- La sesión de AWS Academy no se finalizó desde el portal: es independiente de
  los stacks y cerrar el laboratorio puede invalidar o eliminar el snapshot
  conservado. No se dejaron otros recursos activos del proyecto.

## Inventario verificado antes de retirar

- AWS `us-east-1`: stacks `tangamandapio-live-20261005` (`UPDATE_COMPLETE`,
  45 recursos) y `tangamandapio-voice-recordings` (`CREATE_COMPLETE`, 2
  recursos). La detección de drift terminó `IN_SYNC` en ambos.
- La RDS `tangamandapio-postgres` estaba `available`, `db.t3.micro`, 20 GB,
  cifrada, privada, single-AZ y con un día de backups automáticos. La revisión
  confirmó que la release en AWS era `20261009-erp-internal-mail`; la rama local
  `20261009-smtp-adapter-local` no estaba publicada.
- Los buckets AWS de archivos y grabaciones no tenían objetos. El bucket de
  artefactos tenía dos releases activas; ambas se descargaron y se validaron
  como archivos gzip:
  - `artifacts/cloud-recovery-20261009/aws/portal-20261008-wms-inventory-publish.tar.gz`
    (18,129,011 bytes; SHA-256 `0E8A30F8A71915D4887A26898B26247B715255D2C96F161E0468DB30A5BF76FC`).
  - `artifacts/cloud-recovery-20261009/aws/portal-b2b-20261009-erp-internal-mail.tar.gz`
    (18,151,002 bytes; SHA-256 `A1728F5EDD081460C75CC5AB5E218CCD0334AA71D67ACE9445F18D26BC4922DA`).
- Azure: `rg-tangamandapio-rebuild-wus` era el único grupo de recursos del
  proyecto y sus diez recursos estaban `Succeeded`. Terraform refrescó su state
  local sin cambios remotos; una diferencia previa de `WEBSITE_RUN_FROM_PACKAGE`
  provenía del URL temporal que Zip Deploy asigna y ahora quedó registrada en
  el state local. El state puede contener datos sensibles y no se publica.
- Azure Storage: se exportaron 37 blobs del ledger/eventos y tres paquetes de
  Function al directorio local
  `artifacts/cloud-recovery-20261009/azure/` (40 archivos, 1,818,529 bytes).
  La cola `fulfillment-events` no tenía mensajes. No se copiaron los
  contenedores internos `azure-webjobs-secrets` ni secretos de Function.
  Todo el ledger es sintético y no constituye inventario real.

## IaC y validación

- `iac/cloudformation/aws-lab.yaml` ahora usa un día como retención por defecto,
  acorde al perfil de costo observado y al script de reconstrucción. La plantilla
  pasó `aws cloudformation validate-template`; el stack desplegado ya usaba ese
  valor y ambos stacks estaban `IN_SYNC`.
- `iac/environments/azure-rebuild` valida con Terraform; el refresh-only se
  aplicó únicamente al state local, sin modificar recursos. El plan de refresco
  posterior no encontró diferencias.
- Las copias en `artifacts/cloud-recovery-20261009/` son locales, no deben
  subirse sin revisar `.gitignore` y no contienen las claves de Azure Storage.

## Copias conservadas

Los releases AWS, eventos sintéticos y paquetes de Azure siguen en
`artifacts/cloud-recovery-20261009/`. Se conservaron localmente antes de quitar
los servicios; el detalle de tamaños, conteos, estado previo y hashes está en
este registro. Las copias incluyen datos sintéticos, no secretos de Azure.
