# Terraform Azure — vertical WMS de demostración

El grupo Azure que existe ahora es `rg-tangamandapio-261005-wus` en `westus`. En la consulta del 08/10/2026 sus diez recursos de nivel superior reportaron `provisioningState=Succeeded`; `tangama-wms-fn` aparece habilitada, `Running` y `httpsOnly=true`. Esto describe recursos y ejecución técnica, no inventario real: el flujo sigue siendo `demo-inventory-ledger`.

## Estado de Terraform: no aplicar todavía

El state local `terraform.tfstate` está fechado el 02/10/2026 y apunta al grupo anterior `rg-tangamandapio-261001r2-wus` y a nombres `...261001r2...`; no representa el grupo actual `...261005...`. Además, el `terraform.tfvars` local no define `function_package_path`, por lo que el `plan -refresh-only` probado falla antes de consultar/actualizar el state. No se cambió el state ni Azure.

Por tanto:

1. No ejecutar `terraform apply`, `terraform destroy` ni un plan de cambios contra este state.
2. Conservar el state y respaldarlo de forma segura; contiene información sensible.
3. Inventariar el grupo actual, comparar cada propiedad administrada y sus alertas/Action Groups con `modules/azure_operations`.
4. Crear un state aislado para el grupo actual y adoptar recursos existentes mediante importación revisada; no intentar recrearlos.
5. Generar el ZIP actual con `iac/scripts/package_azure_function.ps1`, especificar `function_package_path`, ejecutar plan normal y verificar que no proponga reemplazos/borrados antes de autorizar apply.

`terraform fmt -check` y `terraform validate` pasan. Eso valida el código, pero este entorno Azure aún **no está listo para un apply seguro** hasta completar la reconciliación descrita.
