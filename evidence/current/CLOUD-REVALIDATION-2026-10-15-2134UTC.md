# Revalidación cloud y release v16 — 15/10/2026, 21:34 UTC

## Resultado

El release `20261015-edge-cache-safe-landing-v16-python312` quedó desplegado en
AWS. El update gradual de CloudFormation terminó `UPDATE_COMPLETE`; una
detección nueva terminó `DETECTION_COMPLETE` con drift `IN_SYNC`. El grupo
`tangamandapio-asg` quedó en 2/2 instancias deseadas, ambas `InService` y
`Healthy`; los dos destinos del target group también estaban saludables.

El token temporal se guardó en el perfil local `default` y STS confirmó la
cuenta `841113066612`. No se registra el access key, secreto ni session token.

## Artefacto e infraestructura

- Revisión: `20261015-edge-cache-safe-landing-v16-python312`.
- SHA-256: `94b9bea7808368fb46f771196bdae792e26babd6aaf22718a9d1917daf0996fe`.
- La clave inmutable, la revisión y el digest coinciden en los parámetros vivos
  del stack y en el objeto de S3. El objeto usa cifrado SSE-S3.
- CloudFormation actualizó el grupo de cómputo/plantilla, política de escalado,
  alarmas de CPU/capacidad y dashboard. El changeset no incluyó RDS, VPC, ALB ni
  eliminaciones.
- La plantilla no habilita WAF y RDS permanece sin cambios respecto de su
  configuración previa. El stack sigue siendo la fuente de verdad; no se
  modificaron instancias manualmente.

## Pruebas vivas

| Comprobación | Resultado |
|---|---|
| `https://tangamandapio.kendellnm.me/` | HTTP 200, certificado válido |
| `/health` y `/ready` por HTTPS público | HTTP 200 |
| Bundles JS/CSS v16 en Cloudflare | HTTP 200; claves incluyen `release=20261015-v16` |
| Bundle inexistente | HTTP 404 y `Cache-Control: no-store` desde ALB y Cloudflare; Cloudflare indicó `BYPASS` |
| `/health` y `/ready` en cada una de las dos instancias finales | HTTP 200; ambas informaron la revisión v16 |
| AWS Auto Scaling | Desired 2, 2 instancias `InService`/`Healthy`, máximo 5 |
| CloudFormation drift | `IN_SYNC` |

El HTTP listener devuelve 301 a HTTPS. Las respuestas del origen incluyeron
HSTS, CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y
`Referrer-Policy: no-referrer`.

## Validación local del release

La puerta local reportó `QUALITY_GATE=APROBADA`: 181 pruebas Python, 14 pruebas
Node, 40 transacciones aisladas del flujo sintético, build/auditoría frontend,
auditorías de dependencias, `cfn-lint`, Terraform `fmt`/`validate` y pruebas
con mocks. El paquete excluye los PNG y el audio locales ignorados por Git; la
portada usa el SVG versionado.

## Límites de este corte

- Azure no se revalidó durante esta actualización. Las pruebas Azure anteriores
  corresponden al ledger/WMS sintético, no a un sistema de inventario físico.
- No se repitió una llamada WebRTC con dos navegadores reales.
- No se completó una inspección visual autenticada de Admin/Comercial/
  Operaciones en Chrome en este corte; los chequeos HTTP no equivalen a esa
  prueba.
- El drift `IN_SYNC` acredita conformidad del stack CloudFormation, no demuestra
  conectividad privada AWS–Azure ni un failover de RDS.
- La evidencia es textual obtenida por CLI/API y HTTPS; el usuario aún puede
  capturar pantallas de las consolas para su sustentación.
