# Entorno Azure de demostración

Este entorno es independiente de AWS para que el plan de Azure no requiera una sesión AWS activa. Despliega el vertical WMS y de observabilidad usando el módulo `azure_operations`.

El grupo `rg-tangamandapio-ops-demo` ya existe y el módulo lo trata como dependencia existente (`create_resource_group = false`); esto evita un conflicto de creación. Si se decide usar otro grupo nuevo, cambiar el valor de forma consciente.

Antes de aplicar se debe reemplazar los nombres de Storage y Key Vault por nombres globalmente únicos. La ejecución exige una sesión autenticada de Azure CLI o un agente seguro con credenciales de Azure. No se deben guardar credenciales en este directorio.

La destrucción del grupo de recursos se realiza únicamente después de capturar las evidencias y con autorización expresa, porque elimina los objetos, la cola, las trazas y las configuraciones de Azure del piloto.
