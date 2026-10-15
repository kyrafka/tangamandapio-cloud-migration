# Terraform Azure — vertical WMS de demostración

Nota histórica de este root (consulta del 08/10/2026): `rg-tangamandapio-261005-wus` y `tangama-wms-fn` fueron el inventario de ese corte. No son el entorno Azure vigente ni el root que debe usarse para desplegar. La revalidación del 15/10/2026 encontró `tangama-wms-261008` en `rg-tangamandapio-rebuild-wus`, `Running`, `httpsOnly=true` y `/api/health` HTTP 200; el root de Terraform correspondiente a esa reconstrucción es `iac/environments/azure-rebuild`. El flujo sigue siendo `demo-inventory-ledger`, no un inventario comercial real.

## Estado de Terraform: no aplicar todavía

El state local `terraform.tfstate` está fechado el 02/10/2026 y apunta al grupo anterior `rg-tangamandapio-261001r2-wus` y a nombres `...261001r2...`; no representa el grupo actual `...261005...`. Además, el `terraform.tfvars` local no define `function_package_path`, por lo que el `plan -refresh-only` probado falla antes de consultar/actualizar el state. No se cambió el state ni Azure.

Por tanto:

1. No ejecutar `terraform apply`, `terraform destroy` ni un plan de cambios contra este state.
2. Conservar el state y respaldarlo de forma segura; contiene información sensible.
3. Inventariar el grupo actual, comparar cada propiedad administrada y sus alertas/Action Groups con `modules/azure_operations`.
4. Crear un state aislado para el grupo actual y adoptar recursos existentes mediante importación revisada; no intentar recrearlos.
5. Generar el ZIP actual con `iac/scripts/package_azure_function.ps1`, especificar `function_package_path`, ejecutar plan normal y verificar que no proponga reemplazos/borrados antes de autorizar apply.

`terraform fmt -check` y `terraform validate` pasan. Eso valida el código, pero este entorno Azure aún **no está listo para un apply seguro** hasta completar la reconciliación descrita.
