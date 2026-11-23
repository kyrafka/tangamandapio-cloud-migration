# Servicios base del WMS en Azure

Esta raíz administra `rg-tangamandapio-rebuild-wus`, Storage, colas, Application Insights, el grupo de acciones y Key Vault. La aplicación que atiende al ERP es `tangama-flex-261104` y se administra en [azure-flex-private](../azure-flex-private). Sus alertas están declaradas en [Azure Monitor](../../azure-monitoring/function-alerts.json).

`deploy_legacy_consumption = false` mantiene fuera de esta raíz la Function Consumption anterior, su plan, las dos alertas métricas antiguas y los cuatro permisos de su identidad. El módulo conserva la opción de aprovisionar el entorno anterior para las raíces de demostración que aún lo usan.

El contenedor `tangama-postgres-backups` y la clave de recuperación se conservan en Azure. El [stack de respaldo](../../cloudformation/aws-azure-postgres-backup.yaml) en AWS programa las copias. Revisa las políticas de retención y protege el Key Vault antes de cualquier cambio que afecte los respaldos.

## Preparar el plan

Copia `rebuild.tfvars.example` a `terraform.tfvars`, ajusta los nombres a tu entorno y proporciona los destinatarios de alertas mediante variables locales. Conserva los estados, planes y variables privadas fuera de Git.

Desde esta carpeta, el lanzador verifica la suscripción, genera el paquete para el registro de artefactos e inicializa el backend. La operación `up` muestra el plan y pide confirmación antes de aplicar.

```powershell
.\lifecycle.ps1 up -ExpectedSubscriptionId '<GUID-de-la-suscripción>'
```

Si necesitas reconstruir el backend remoto en un entorno nuevo, usa `bootstrap-state` con el identificador de la suscripción de ese entorno. Conserva el backend `azure-tfstate` operativo. Consulta el [orden de reconstrucción](../../README.md) antes de aprovisionar la red, la Function Flex y sus dependencias.
