# Revisión Terraform de Azure del 20 de noviembre

Los planes consultaron el backend remoto del proyecto en Azure for Students.
Se usó Terraform 1.16.2 y se validaron el formato, la configuración y las tres
pruebas del entorno Flex con proveedor simulado.

| Raíz | Lectura | Resultado |
| --- | --- | --- |
| `azure-flex-private` | Plan normal antes del ajuste | Solo proponía cambiar las etiquetas de la Function. Azure agrega `hidden-link: /app-insights-resource-id` para mantener el vínculo con Application Insights. |
| `azure-flex-private` | Plan normal después del ajuste | Sin operaciones sobre recursos. Quedan cambios solo en las salidas del estado. Terraform preserva esa etiqueta y administra las demás. |
| `azure-flex-private` | Sincronización de salidas y segundo plan | Se guardaron tres salidas y el refresco en el backend. `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` El plan posterior dio `No changes`. |
| `azure-rebuild` | Plan `refresh-only` desde el backend vigente | Siete recursos cambiaron fuera del estado. El plan de lectura se pudo completar con el ZIP inmutable generado desde el repositorio. Se retiró la referencia a un ZIP antiguo del archivo de ejemplo. |

Los cambios observados en `azure-rebuild` corresponden a propiedades de
red de Key Vault, identidad y etiquetas de la Function anterior, receptores
del grupo de acción, acciones y estado de las dos alarmas anteriores, y
metadatos de las colas principal y de mensajes fallidos. Antes de preparar un
plan de escritura hay que cotejar los receptores autorizados y el estado de los
servicios anteriores. En esa raíz se hizo una revisión de solo lectura.

Las salidas sincronizadas de Flex fueron `fulfillment_event_url`,
`function_deployment_container_endpoint` y `wms_queue_status_url`.

[Raíz de la Function Flex](../../../iac/environments/azure-flex-private/README.md) ·
[Raíz de reconstrucción Azure](../../../iac/environments/azure-rebuild/README.md).
