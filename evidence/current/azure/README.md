# Evidencias vigentes Azure

**Fecha de corte:** 01/10/2026  
**Dominio:** operación WMS asíncrona de Tangamandapio S.A.C.  
**Región temporal:** West US

| ID | Qué demuestra | Resultado | Uso en el entregable |
|---|---|---|---|
| CUR-AZ-01 | Terraform creó el vertical WMS temporal | 12 recursos creados | Sí, como evidencia de infraestructura |
| CUR-AZ-02 | Diagnóstico inicial de Functions | El primer empaquetado Linux no permitió acreditar el flujo WMS | Sí, solo como antecedente de corrección |
| CUR-AZ-03 | Eliminación e inventario final | Pendiente | No usar hasta verificar inventario cero |
| CUR-AZ-05 | Inventario Azure CLI actual | Function Linux `Running`, Storage, Key Vault, Monitor y plan Consumption | Sí, evidencia visual de infraestructura actual |
| CUR-AZ-06 | Health WMS autenticado | HTTP `200`, `status=ok`; CORS limitado al portal | Sí, evidencia visual de funcionamiento parcial |
| CUR-AZ-07 | Flujo WMS extremo a extremo | Health `200`; fulfillment `202`; repetición idempotente `200`; Blob y Queue verificados | Sí, evidencia visual de funcionamiento completo |
| CUR-AZ-08 | Cierre Azure | Ambos grupos de Tangamandapio eliminados; consulta final sin grupos | Sí, evidencia visual de control de costos |

No se guarda ningún secreto, clave de Function, URL firmada, identificador de cuenta ni dato personal. Las imágenes `CUR-AZ-05`, `CUR-AZ-06` y `CUR-AZ-07` son registros visuales generados desde consultas autenticadas de Azure CLI, no capturas del portal; consignan fecha, región, recurso, configuración y resultado sin exponer datos sensibles.
