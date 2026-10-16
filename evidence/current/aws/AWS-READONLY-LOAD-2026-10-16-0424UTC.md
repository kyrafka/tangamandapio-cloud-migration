# Revalidación AWS de solo lectura y smoke de carga — 16/10/2026, 04:22–04:24 UTC

## Resultado

El perfil AWS `default` autenticó en la cuenta `841113066612` con un rol
temporal de AWS Academy. No se imprimieron ni guardaron credenciales en esta
evidencia. CloudFormation informó `UPDATE_COMPLETE`; una detección nueva de
drift concluyó `IN_SYNC` a las 04:23:50 UTC.

El ALB mantuvo dos destinos `healthy`. El ASG `tangamandapio-asg` tenía deseado
2, mínimo 2, máximo 5 y dos instancias `InService/Healthy`. RDS
`tangamandapio-postgres` estaba `available`, cifrada y no pública, pero
Single-AZ y con retención de backups de un día.

Las cinco alarmas consultadas (`high-cpu`, `in-service-capacity`, `rds-high-cpu`,
`target-5xx` y `unhealthy-targets`) estaban `OK`. Matiz: `target-5xx` no recibió
datapoints y su configuración trata datos faltantes como `NonBreaching`; su
estado no demuestra que haya observado peticiones. No se dispararon alarmas ni
se enviaron avisos.

Pruebas públicas de salud desde el host:

| Endpoint | Resultado |
|---|---|
| `https://tangamandapio.kendellnm.me/health` | HTTP 200, ~1.01 s |
| `http://tangamandapio.kendellnm.me/health` | HTTP 301 hacia HTTPS |
| `https://tangama-wms-261008.azurewebsites.net/api/health` | HTTP 200, ~0.93 s |

## Smoke autenticado y carga de lectura

Se ejecutó `run_live_aws_portal_azure_e2e.ps1` en modo `admin-readonly`, destino
`alb-origin-https`: el cliente se conectó al origen del ALB con hostname y TLS
correctos, evitando confundir el 403 previo del proxy Cloudflare con el estado
del origen. La ruta de prueba está prevista por el runner.

- Resultado: `LIVE_ADMIN_READONLY_SMOKE_PASSED`.
- 24 peticiones GET autenticadas, concurrencia 6; todas HTTP 200; p95 191.51 ms.
- Dashboard: una orden visible; outbox paginado completo, 49/49 entregados y
  cero pendientes.
- Autorización: Comercial obtuvo 200 solo para ventas y 403 para usuarios,
  alarmas, outbox y WMS. Operaciones obtuvo 200 para outbox/WMS y 403 para
  ventas y rutas administrativas.
- Alertas: dos suscripciones SNS confirmadas, cero pendientes.
- No se crearon pedidos, compras, transacciones financieras ni mensajes WMS.

El runner inicia y cierra sesión autenticada; por ello se generan eventos
normales de auditoría de sesión. SSM también registra la ejecución del comando.
No se alteraron reglas de Cloudflare, infraestructura, alarmas ni datos de
negocio.

## Límite de esta evidencia

24 lecturas concurrentes constituyen un smoke de regresión y latencia puntual,
no una prueba de estrés, una previsión de concurrencia ni evidencia de soporte
para los 3,000 usuarios externos del supuesto de diseño. Las pruebas históricas
de escalado sintético 2↔3 no sustituyen una carga sostenida representativa.
Continúan pendientes la ruta privada AWS–Azure, WAF, failover/Multi-AZ y mayor
retención RDS, prueba sostenida y correlación de alarmas con tráfico observado,
capturas actuales de consola y recorrido visual completo.

## Reproducción local

La adición del smoke fue cubierta por 32 pruebas unitarias de su módulo y por
la compuerta local completa: 215 pruebas Python, 14 pruebas Node, build del
frontend, auditorías, validación CloudFormation, validación Terraform y cinco
pruebas mock. Estas validaciones no aplican cambios en la nube. GitHub Actions
para el commit de pruebas `b1d36a9` pasó sus tres trabajos (run
[38851449937](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38851449937)).
