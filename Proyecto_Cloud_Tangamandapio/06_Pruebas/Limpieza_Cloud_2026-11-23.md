# Retiro de recursos residuales del 23/11/2026

## Azure · West US

Terraform retiró ocho objetos de `rg-tangamandapio-rebuild-wus`. El plan aplicado registró cero altas, cero modificaciones y ocho bajas.

| Elemento retirado | Motivo |
| --- | --- |
| Function `tangama-wms-261030` | Estaba detenida. El ERP usa la Function Flex privada. |
| Plan `tangama-wms-plan` (Y1) | Su única aplicación era la Function detenida. |
| Alertas `tangama-wms-fn-5xx` y `tangama-wms-fn-latency` | Estaban desactivadas y apuntaban solo a la Function retirada. |
| Cuatro asignaciones de Azure RBAC | Correspondían a la identidad de la Function retirada. |

ARM confirmó que los cuatro recursos ya no aparecen en el grupo y el estado de Terraform comprobó las ocho bajas. La Function `tangama-flex-261104` sigue en `Running`, con acceso público desactivado y un Private Endpoint. Las alertas `tangama-flex-5xx-es` y `tangama-flex-latencia-es` siguen habilitadas. ARM confirmó el contenedor `tangama-postgres-backups`.

## AWS · Ohio

El paquete de S3 `portal-b2b-20261119-admin-backup-and-scaling.tar.gz` coincidía byte por byte con el paquete `portal-b2b-20261119-admin-07ba855f7cca.tar.gz`. El segundo sigue disponible para la versión 4 de la plantilla de lanzamiento. Se retiró el nombre duplicado de la lista activa de S3 y se comprobó que su versión anterior es recuperable.

La revisión encontró dos destinos saludables en el ALB, cuatro EC2 en ejecución, RDS Multi-AZ disponible, las tres IP elásticas asociadas y cero volúmenes EBS disponibles sin adjuntar. Se conservaron los respaldos, los registros y los artefactos de reversión. Las consultas de EC2 y CloudFormation en Virginia del Norte y Oregón quedaron limitadas por una política de AWS Organizations.

## Comprobación posterior

| Prueba | Resultado |
| --- | --- |
| ERP público `/ready` | HTTP 200 |
| Inventario WMS desde ambas EC2 de aplicación | HTTP 200 en cada instancia, con destino privado `10.20.1.4` |
| Validación de Terraform y suite de IaC | Configuración válida y 127 pruebas correctas |
