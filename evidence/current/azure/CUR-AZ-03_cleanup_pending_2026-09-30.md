# CUR-AZ-03 — Cierre Azure pendiente de verificación

## Objetivo

Eliminar los grupos temporales de Tangamandapio y confirmar que Azure no conserva recursos facturables del laboratorio.

## Secuencia aprobada

1. Autenticar Azure CLI con la cuenta académica.
2. Eliminar el grupo temporal West US y el grupo vacío East US.
3. Consultar `az group exists` hasta obtener `false` para ambos.
4. Guardar una captura del comando o del portal con inventario cero.
5. Actualizar el Entregable 1 y la bitácora con fecha y resultado observados.

## Estado

Pendiente. No declarar recursos eliminados antes de la comprobación final.
