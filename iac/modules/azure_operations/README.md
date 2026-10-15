# Módulo Azure de operaciones

## Empaquetado de la Function

Antes de ejecutar `terraform plan` o `terraform apply`, cree el ZIP reproducible
desde la raíz del repositorio:

```powershell
.\iac\scripts\package_azure_function.ps1
```

El ZIP queda en `artifacts/azure_function_package-<SHA256>.zip`, carpeta
ignorada por Git. `rebuild.tfvars.example` fija explícitamente ese archivo; no
hay un nombre mutable predeterminado para Terraform.
Terraform sube el ZIP a un contenedor privado con nombre basado en SHA-256 y
configura `WEBSITE_RUN_FROM_PACKAGE` para montarlo mediante la identidad
administrada de la Function. El contenedor concede `Storage Blob Data Reader`
solo a esa identidad; no se generan SAS ni se habilita autenticación básica de
FTP/SCM. La rotación de paquetes usa `create_before_destroy`: el nuevo Blob
hash-nombrado se crea antes de retirar el anterior. La cuenta conserva blobs
borrados por 7 días mediante soft delete (versioning está deshabilitado), así
que el rollback remoto es temporal; conserva también una copia local del ZIP
anterior. Tras aplicar un paquete nuevo, sincroniza triggers con ARM y valida
health y un flujo autenticado antes de cerrar el despliegue.

Este módulo representa el dominio de cumplimiento logístico de Tangamandapio S.A.C. Crea un Resource Group etiquetado, Storage Account Standard LRS con TLS 1.2, contenedores Blob privados para eventos y paquetes, colas principal/poison, Function App Linux Consumption, Log Analytics, Application Insights y Key Vault con RBAC habilitado. La identidad administrada solo recibe permisos de datos sobre recursos que la aplicación necesita; no recibe acceso a secretos de Key Vault mientras el código no consuma secretos desde allí.

Las alertas 5xx y latencia apuntan a un Action Group común. Los receptores se
configuran mediante `alert_email_receivers`, variable sensible y vacía por
defecto; este workspace conserva su valor en
`iac/environments/azure-rebuild/alert-recipients.local.tfvars`, ignorado por
Git. En el entorno vivo del 14/10/2026 el Action Group tiene dos receptores
configurados y el plan posterior al cambio devuelve `No changes`. No se provocó
una alerta, así que esa configuración no prueba entrega efectiva de correos.

La telemetría conserva 30 días y tiene topes de ingestión de 0,1 GB/día en Log Analytics y Application Insights como protección de costos para el laboratorio. Si se alcanza el tope, la recolección puede detenerse hasta el siguiente reinicio diario; hay que revisar el uso, no usar el tope como filtro normal.

La implementación académica mantiene el componente expuesto solo por HTTPS y no crea una VM, AD DS, AVD, Power BI, Private Endpoint ni una base de datos adicional. Esos componentes permanecen como arquitectura objetivo de producción; activarlos no mejora la prueba del flujo WMS y sí aumenta el costo.

El código del receptor está en `app/azure_function`. Antes de aplicar, valida
la región y prepara el ZIP. El builder usa `requirements.lock` con hashes e
instala wheels para Python 3.11/Linux, incluye el lock y no sobrescribe ZIPs
existentes. Una prueba local comprueba que el SHA-256 y los archivos del paquete
coincidan con la fuente. Linux Consumption usa un Blob privado para el
paquete de ejecución; no depende de `az functionapp deployment source config-zip`
ni del endpoint Kudu/SCM. Tras el apply, sincroniza triggers por ARM y prueba
health, un evento autenticado y el conteo autenticado de poison. La cola poison
usa los cinco reintentos configurados en `host.json`; el endpoint no muestra
contenido de mensajes. Tras la demostración se capturan la región, el
inventario, el resultado del evento, las trazas y el costo; luego se elimina el
grupo de recursos por una acción confirmada del responsable.

Terraform también declara `ALLOWED_EVENT_SOURCES` para el contrato de eventos
AWS→Azure (`aws-order-core`, `aws-wms-demo-console` y `tangamandapio-erp` por
defecto). La Function rechaza un emisor no declarado antes de pedir identidad
administrada o escribir en Blob/Queue. Esto no reemplaza la clave de Function
ni convierte el inventario ficticio en un WMS empresarial.
