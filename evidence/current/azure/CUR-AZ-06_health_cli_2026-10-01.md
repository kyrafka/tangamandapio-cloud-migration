# CUR-AZ-06 — Health WMS autenticado y control CORS

| Campo | Registro |
|---|---|
| Fecha | 01/10/2026 |
| Recurso | Azure Function del vertical WMS, West US |
| Configuración | HTTPS obligatorio, autorización `function` y CORS limitado a `https://portal.azure.com` |
| Prueba | `GET /api/health` con clave de Function mantenida solamente en memoria del cliente de prueba |
| Resultado | HTTP `200`; cuerpo: `status=ok`, `service=tangamandapio-wms` |
| Interpretación | Un GET sin clave devuelve HTTP `401` intencionalmente; no es caída del servicio. |
| Resultado posterior relacionado | El POST de fulfillment, el Blob privado y la Queue se verificaron antes del cierre; ver `CUR-AZ-07`. |
| Imagen | `screenshots/CUR-AZ-06_health_cli_2026-10-01.png` |

La imagen es un registro visual de una prueba HTTP real con Azure CLI autenticado. No expone la clave de Function.
