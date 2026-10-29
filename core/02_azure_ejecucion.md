# Azure — WMS de demostración y servicios de operación

## Estado comprobado al 29/10/2026, 21:14 UTC

La Function Y1 `tangama-wms-261008` está desplegada y `/api/health` responde 200. Flex `tangama-wms-flex-261013` está en ejecución y su Private Endpoint está `Succeeded/Approved`; desde Internet `/api/health` devuelve 403, esperado con acceso público deshabilitado.

Se verificó una recepción sintética en vivo por Y1: la cola procesó el evento `qa-recv-20261029211311-97957bdb`, Application Insights registró aceptación, resultado y repetición; el resultado fue `demo_restock_completed`. El reenvío del mismo ID quedó `queued_duplicate` y el ledger sintético aumentó una sola unidad. La cola poison reportó 0 mensajes. El registro no es un evento enviado desde el portal AWS ni prueba la ruta privada a Flex. No representa inventario físico.

El gateway Azure P2S está `Succeeded`, route-based, OpenVPN/certificado; no es Site-to-Site administrada. La métrica `P2SConnectionCount` llegó a máximo 1 entre 17:50 y 18:10 UTC, pero no tuvo puntos posteriores en la consulta; el route table consultado no contiene rutas y ninguna subnet tiene ese route table asociado. No hay evidencia de túnel activo ahora ni de recorrido extremo a extremo AWS→Flex. El anterior reporte de HTTPS 200 desde EC2 es histórico hasta poder revalidarlo. Consulta [estado de IaC y límites](../iac/README.md) y [runbook P2S](../iac/environments/azure-p2s-vpn/README.md).

## Alcance funcional

Azure Functions procesa eventos del WMS de laboratorio y Blob/Queue mantienen un ledger de inventario sintético, con idempotencia. Este flujo sirve para ventas, recepciones y transferencias de demostración; no representa stock físico ni integración con un WMS comercial externo.

Application Insights sí registró el ID de la recepción QA en cinco trazas entre 21:13 y 21:14 UTC. La correlación quedó demostrada dentro del flujo de Azure; falta enlazar el mismo ID a un pedido/outbox AWS vivo. No se disparó una alerta nueva.

El Storage de operaciones exige HTTPS y TLS 1.2, tiene cifrado Blob habilitado y soft delete de 7 días; no tiene versionado de blobs y permite acceso de red pública. Estas propiedades no constituyen una copia de PostgreSQL ni una restauración cruzada.

## Terraform

Los roots Azure son independientes. Usa `azure-rebuild` para la reconstrucción del backend, `azure-flex-private` para la red privada del servicio y `azure-p2s-vpn` para el piloto de acceso privado. `azure-tfstate` administra el almacenamiento remoto de estado. `azure-demo` es un entorno separado.

Antes de `plan` o `apply`, confirma suscripción, grupo de recursos, estado remoto, variables no secretas, certificado nuevo y costo del gateway. Revisa el plan completo; no guardes `.tfstate`, planes, PFX, claves ni tokens en GitHub. No vuelvas a crear recursos solo porque una consulta externa a la Function privada devuelva 403.

## Cierre de una sesión

Al finalizar una ventana de prueba, desconecta la VPN si no se requiere, identifica gateways/planes/instancias que generan costo, destruye únicamente recursos temporales que estén mapeados en IaC y verifica el inventario en el portal Azure. No borres el estado remoto ni datos antes de comprobar la restauración que se quiere conservar.
