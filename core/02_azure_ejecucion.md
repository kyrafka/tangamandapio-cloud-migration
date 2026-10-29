# Azure — WMS de demostración y servicios de operación

## Estado conocido al 29/10/2026

Azure CLI pudo listar los recursos del proyecto en West US: Functions Y1 y Flex, Storage, Key Vault, Application Insights, Log Analytics, alertas, VNet, DNS privado, Private Endpoint y VPN Gateway P2S. La Function Y1 respondió HTTP 200 en `/api/health`. La Function Flex tiene acceso público deshabilitado; desde Internet respondió `403 Ip Forbidden`, lo cual no prueba el trayecto privado.

El gateway P2S aparece provisionado como `Succeeded`. El reporte del 29/10 describe HTTPS 200 al endpoint privado del WMS desde el router EC2 y dos instancias AWS. Ese recorrido no pudo revalidarse en la consulta AWS posterior. Consulta [estado de IaC y límites](../iac/README.md) y [runbook P2S](../iac/environments/azure-p2s-vpn/README.md).

## Alcance funcional

Azure Functions procesa eventos del WMS de laboratorio y Blob/Queue mantienen un ledger de inventario sintético, con idempotencia. Este flujo sirve para ventas, recepciones y transferencias de demostración; no representa stock físico ni integración con un WMS comercial externo.

Application Insights, Log Analytics, Key Vault y alertas forman parte del soporte operativo. La presencia de recursos no confirma entrega actual de alertas ni correlación completa de un evento. Falta cerrar la trazabilidad con un identificador único desde el pedido hasta el resultado de Function.

## Terraform

Los roots Azure son independientes. Usa `azure-rebuild` para la reconstrucción del backend, `azure-flex-private` para la red privada del servicio y `azure-p2s-vpn` para el piloto de acceso privado. `azure-tfstate` administra el almacenamiento remoto de estado. `azure-demo` es un entorno separado.

Antes de `plan` o `apply`, confirma suscripción, grupo de recursos, estado remoto, variables no secretas, certificado nuevo y costo del gateway. Revisa el plan completo; no guardes `.tfstate`, planes, PFX, claves ni tokens en GitHub. No vuelvas a crear recursos solo porque una consulta externa a la Function privada devuelva 403.

## Cierre de una sesión

Al finalizar una ventana de prueba, desconecta la VPN si no se requiere, identifica gateways/planes/instancias que generan costo, destruye únicamente recursos temporales que estén mapeados en IaC y verifica el inventario en el portal Azure. No borres el estado remoto ni datos antes de comprobar la restauración que se quiere conservar.
