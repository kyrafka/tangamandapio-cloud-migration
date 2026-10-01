# CUR-AZ-08 — Cierre Azure e inventario cero

**Fecha:** 01/10/2026

**Alcance:** recursos temporales de Tangamandapio S.A.C. en Azure for Students.

## Verificación previa

Se enumeraron exclusivamente los grupos con el prefijo `rg-tangamandapio`:

- `rg-tangamandapio-ops-demo`: sin recursos.
- `rg-tangamandapio-ops-wus`: Storage, Log Analytics, plan Consumption, Key Vault, Application Insights, Function App y Action Group del vertical WMS.

No se tocaron grupos ajenos al proyecto.

## Cierre ejecutado

Se solicitó la eliminación asíncrona de ambos grupos. La comprobación final de `az group list` filtrada por `rg-tangamandapio` no devolvió grupos, por lo que no permanecen recursos de Tangamandapio en Azure.

La evidencia funcional de WMS se conserva en `CUR-AZ-07`; el cierre elimina los recursos temporales, no los registros de la prueba. La imagen asociada es `screenshots/CUR-AZ-08_cierre_inventario_cero_2026-10-01.png`, rotulada como registro visual de Azure CLI y sin secretos.
