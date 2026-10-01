# Fase Azure — operación WMS

## Objetivo

Azure recibe de forma asíncrona el evento de pedido ya confirmado en AWS. No aloja un segundo portal comercial.

## Estado de ejecución — 30/09/2026

- El grupo inicial `rg-tangamandapio-ops-demo` en East US permanece con cero recursos. Azure for Students rechazó el App Service Plan allí por política de regiones.
- La política permitió West US, por lo que Terraform creó el grupo temporal `rg-tangamandapio-ops-wus` y completó 12 recursos: Resource Group, Storage, Blob privado, Queue, Key Vault, Service Plan Consumption, Function App, Log Analytics, Application Insights y tres asignaciones RBAC de identidad administrada.
- Diagnóstico actualizado: el primer paquete Python no se indexó (HTTP 404). Se corrigió el paquete para usar funciones explícitas `function.json`, se incorporaron las dependencias en `.python_packages` y se configuró `AzureWebJobsStorage`, requerido por el host. Azure ya registra `HttpHealth` y `HttpFulfillment`; sin embargo, las invocaciones con clave válida siguen devolviendo HTTP 500 incluso para el health handler aislado. No existe evidencia válida de Blob/Queue ni se debe declarar la prueba de aceptación como aprobada. La excepción interna sigue pendiente de obtenerse desde el runtime.
- El cierre pendiente debe destruir el grupo temporal de West US y verificar el inventario en cero. No afirmar que el cierre ocurrió hasta que Azure confirme la eliminación.

## Vertical mínimo

1. Storage Account Standard LRS, TLS 1.2, Blob no público y soft delete.
2. Contenedor privado de eventos y Storage Queue WMS.
3. Function App Consumption con endpoint autenticado.
4. Managed Identity + roles Blob/Queue/Key Vault de mínimo privilegio.
5. Key Vault para secreto de integración.
6. Log Analytics + Application Insights.
7. Restricción de acceso de Function a la salida identificada de AWS o control equivalente.

`iac/environments/azure-demo/` y `iac/modules/azure_operations/` pasan `fmt` y `validate` localmente. En Azure se aplicó el despliegue temporal mediante Terraform en una región permitida. El archivo habilita el indexado Python y compilación Oryx para la Function.

## Pruebas de aceptación

- `order.created` con `event_id` llega a Function y obtiene respuesta aceptada.
- Existe un Blob privado y un mensaje en Queue con el mismo identificador.
- Reenvío del evento devuelve duplicado y no agrega un segundo mensaje.
- Error temporal deja trazabilidad/reintento sin afectar el pedido AWS.
- Logs y telemetría visibles; costo e inventario final capturados tras destrucción autorizada.

No se alterará el tenant académico para Entra ID/AD DS, ni se desplegarán AVD, Power BI, VPN o Private Endpoints en el piloto de bajo costo.
