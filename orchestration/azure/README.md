# Orquestación Azure — fase posterior a AWS

## Propósito

Azure recibe el dominio operativo de Tangamandapio: el evento autenticado e idempotente de pedido que alimenta el WMS. No reemplaza la capa transaccional de AWS ni se desplegará mientras AWS no haya sido validado o cerrado según la ventana de laboratorio.

## Línea base comprobada

- Existe el Resource Group `rg-tangamandapio-ops-demo` en East US.
- No se declara ningún Storage Account, Function App, Queue, Key Vault, Log Analytics ni Application Insights como desplegado.
- `iac/environments/azure-demo` reutiliza el grupo existente para evitar fallar intentando crearlo otra vez.

## Recursos que Terraform propondrá

1. Storage Account LRS con TLS 1.2, Blob privado y Queue `fulfillment-events`.
2. Key Vault RBAC, borrado suave de 7 días y red por defecto denegada.
3. Function App Linux Consumption con identidad administrada.
4. Asignaciones RBAC a Blob, Queue y Key Vault.
5. Log Analytics y Application Insights.

## Puertas antes de aplicar

1. Terminar la prueba AWS o confirmar el cierre de sus recursos para no superponer consumos.
2. Definir nombres globalmente únicos para Storage Account y Key Vault en `terraform.tfvars`.
3. Obtener `terraform init` y `terraform validate` exitosos para `iac/environments/azure-demo`; no usar el entorno histórico `iac/environments/demo`.
4. Generar y revisar `terraform plan` con sesión Azure activa.
5. Confirmar el gasto antes de `terraform apply`.

## Brechas que siguen pendientes

- El módulo crea la Function App, pero el paquete `app/azure_function/` todavía debe publicarse con un mecanismo de despliegue versionado.
- La integración AWS→Azure sigue siendo un contrato/demostración local: falta el emisor real, autenticación entre nubes, cola de reintento y prueba extremo a extremo.
- Se debe capturar evidencia real de RBAC, cola, Blob, telemetría y recepción idempotente antes de declarar Azure implementado.

