# CUR-AZ-03 — Plan de cierre Azure sustituido por verificación final

## Objetivo

Eliminar los grupos temporales de Tangamandapio y confirmar que Azure no conserva recursos facturables del laboratorio.

## Secuencia aprobada

1. Autenticar Azure CLI con la cuenta académica.
2. Eliminar el grupo temporal West US y el grupo vacío East US.
3. Consultar `az group exists` hasta obtener `false` para ambos.
4. Guardar una captura del comando o del portal con inventario cero.
5. Actualizar el Entregable 1 y la bitácora con fecha y resultado observados.

## Estado final

El plan se ejecutó el 01/10/2026. La consulta autenticada filtrada por el prefijo
`rg-tangamandapio` no devolvió ningún Resource Group. La evidencia final de cierre
es `CUR-AZ-08`; este archivo se conserva como bitácora del procedimiento, no como
prueba principal.
