# Azure Function health GET/HEAD y despliegue — 16/10/2026, 05:08–05:19 UTC

Se corrigió la sonda pública de `tangama-wms-261008` para admitir GET y HEAD.
HEAD devuelve HTTP 200 sin cuerpo; GET conserva el JSON de salud. La Function
sigue siendo una integración de fulfillment con ledger sintético, no un WMS
conectado a inventario físico.

## Código y comprobaciones

- Las 32 pruebas de `app/azure_function_tests` pasaron antes de publicar.
- El paquete inmutable
  `azure_function_package-97383da268c023b54c38c8bba28c31853abb10545b796b995b8b336511bbe30d.zip`
  pasó `tests/check_azure_package.py` como `SOURCE_MATCH_AND_SHA256_APPROVED`.
- El plan Terraform solo actualizaba la Function y sustituía el Blob del
  paquete por el nuevo release. No reemplazaba recursos de servicio ni datos.
- `terraform apply` terminó con 1 recurso añadido, 1 actualizado y 1 retirado
  (el Blob de paquete anterior); la retención de borrado temporal del storage
  está configurada en siete días.
- Se sincronizaron los disparadores de Function mediante ARM. Azure CLI lista
  las siete Functions esperadas.
- El plan Terraform posterior terminó `No changes` (salida 0).

## Verificación viva

| Comprobación | Resultado |
|---|---|
| Function state / `httpsOnly` | `Running` / `true` |
| GET `https://tangama-wms-261008.azurewebsites.net/api/health` | HTTP 200, TLS verificado (`ssl_verify_result=0`) |
| HEAD en la misma ruta | HTTP 200, TLS verificado y `size_download=0` |
| Disparadores indexados | 7 Functions visibles en Azure |

Esto acredita el despliegue de esta corrección y la salud HTTP de Azure. No se
repitió en este corte el E2E de pedidos AWS→Azure; el E2E y la restauración
documentados en
[`CLOUD-E2E-DR-2026-10-16-0500UTC.md`](../CLOUD-E2E-DR-2026-10-16-0500UTC.md)
son evidencia anterior a esta versión. AWS tampoco pudo revalidarse después:
STS rechazó el token compartido en este corte. No se hizo ningún cambio en AWS.
