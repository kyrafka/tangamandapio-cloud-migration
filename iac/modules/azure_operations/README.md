# Módulo Azure de operaciones

## Empaquetado de la Function

Antes de ejecutar `terraform plan` o `terraform apply`, cree el ZIP reproducible
desde la raíz del repositorio:

```powershell
.\iac\scripts\package_azure_function.ps1
```

El ZIP queda en `artifacts/azure_function_package.zip`, carpeta ignorada por Git.
El entorno recibe su ruta mediante `function_package_path`; Terraform usa Zip Deploy
en lugar de conservar paquetes históricos o URLs SAS con caducidad fija.

Este módulo representa el dominio de cumplimiento logístico de Tangamandapio S.A.C. Crea un Resource Group etiquetado, Storage Account Standard LRS con TLS 1.2, contenedor Blob privado, Storage Queue, Function App Linux Consumption, Log Analytics, Application Insights y Key Vault con RBAC. La Function recibe una identidad administrada con permisos mínimos para escribir solamente en Blob, Queue y leer secretos.

La implementación académica mantiene el componente expuesto solo por HTTPS y no crea una VM, AD DS, AVD, Power BI, Private Endpoint ni una base de datos adicional. Esos componentes permanecen como arquitectura objetivo de producción; activarlos no mejora la prueba del flujo WMS y sí aumenta el costo.

El código del receptor está en `app/azure_function`. Antes de aplicar, se debe validar la región y preparar el paquete de despliegue. Tras la demostración se capturan la región, el inventario, el resultado del evento, las trazas y el costo; luego se elimina el grupo de recursos por una acción confirmada del responsable.
