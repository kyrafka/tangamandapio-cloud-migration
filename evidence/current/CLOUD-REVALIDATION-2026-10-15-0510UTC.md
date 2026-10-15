# Revalidación cloud — 15/10/2026, 05:10 UTC

Comprobación puntual posterior a la actualización publicada a las 04:53 UTC.
No se desplegó código ni se alteró la infraestructura de aplicación durante
estas pruebas. La única creación fue una solicitud ACM de certificado público
para el subdominio ya acordado; ACM no cobra por certificados públicos.

## AWS

- STS autenticó en la cuenta Academy `841113066612`.
- CloudFormation `tangamandapio-live-20261013` está `UPDATE_COMPLETE`. Una nueva
  detección terminó `DETECTION_COMPLETE` con `IN_SYNC` a las 04:59:33 UTC.
- El ALB `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` está activo e
  internet-facing; los dos destinos del target group están `healthy`.
- `/`, `/health` y `/ready` por el ALB devolvieron HTTP 200. Sin sesión,
  `/api/admin/users` devolvió 401.
- El listener sigue solo en HTTP/80. RDS `tangamandapio-postgres` está
  `available`, Single-AZ y conserva un día de backup automático.
- Solicitud ACM `arn:aws:acm:us-east-1:841113066612:certificate/6f8c1c79-ccfc-4e5e-9238-3b16065fef1d`
  para `tangamandapio.kendellnm.me`: `PENDING_VALIDATION`. ACM entregó un CNAME
  DNS de validación; falta publicarlo como DNS only. El parámetro de hostname y
  el ARN de certificado del stack siguen vacíos hasta que ACM emita el
  certificado. Una consulta pública no encontró aún el CNAME de validación. No
  hay listener 443 todavía.

## Azure

- Suscripción `Azure for Students`: `Enabled`.
- `az group show` confirmó `rg-tangamandapio-rebuild-wus` en `westus`, estado
  `Succeeded`.
- `https://tangama-wms-261008.azurewebsites.net/api/health` respondió HTTPS 200
  con `status: ok`. Las consultas de inventario y `functionapp show` del CLI no
  concluyeron en tiempo razonable y se cancelaron; en este corte se confirma la
  salud del endpoint, no el estado completo del recurso por ARM.

## Puerta local repetida

- Python: 152 pruebas y 157 subtests aprobados en `app/tests`,
  `app/aws_release/tests`, `app/aws_release/current/tests` y
  `app/azure_function_tests`.
- Frontend: 8 pruebas de permisos, 6 de importación CSV y build de Vite
  aprobados.
- `cfn-lint` en las plantillas CloudFormation: aprobado.
- Terraform 1.16.2: `fmt -check`, `init -backend=false` y `validate` aprobados en
  los seis entornos incluidos por CI; las pruebas mock de red/costos aprobaron
  3/3 y 2/2.
- Guardas AWS: preflight de certificado, protección de destrucción, restauración
  de estado de monitoreo y validación del nombre del stack aprobados.

## Pendiente

- Kendell debe publicar el CNAME ACM en DNS con proxy desactivado para ese
  registro. Después, esperar `ISSUED`, desplegar los parámetros del dominio y
  certificado en CloudFormation, y verificar redirect HTTP→HTTPS y certificado
  desde un navegador externo.
- HTTPS al hostname expiró al conectar durante la prueba de este corte; no está
  activo. No se hizo una prueba WebRTC de dos navegadores.
- El DNS actual del hostname responde con dos A distintos de las IP actuales
  del ALB, mientras HTTP `/health` por el hostname devuelve 200. Esto es
  consistente con una capa DNS/proxy, pero no se inspeccionó la configuración
  privada de Cloudflare.

Este documento es evidencia de una revalidación puntual, no certifica
capacidad para 3,000 usuarios, entrega de alertas ni una VPN privada AWS–Azure.

## Seguimiento — 05:13 UTC

- El CNAME ACM aún no resuelve públicamente y el certificado continúa
  `PENDING_VALIDATION`; HTTPS no se habilitó.
- AWS volvió a responder `/health` 200 y mantiene `UPDATE_COMPLETE` con 2/2
  targets `healthy`. Azure volvió a responder `/api/health` HTTPS 200.
- Los tres checks de GitHub Actions del commit `8e49d8e` terminaron
  `completed/success`: backend y flujo, infraestructura AWS/Azure, y frontend.
- El branch local y el remoto coinciden en `8e49d8e`.

## E2E en vivo — 05:15 UTC

- El smoke autenticado se ejecutó por SSM en una EC2 del portal, con el opt-in
  explícito de escrituras sintéticas. Admin inició sesión; Comercial y
  Operaciones respetaron 200/403 según rol, sin acceso admin indebido.
- Importación de catálogo, venta `completed_demo`, compra/recepción
  `received_demo`, dos eventos outbox entregados y ledger sintético 10→10.
- Las dos suscripciones de SNS se leyeron como confirmadas (0 pendientes).
- Las 24 lecturas de la prueba tuvieron HTTP 200, concurrencia 6, p95 246.02 ms.
  Es una prueba pequeña de lectura, no una demostración de 3,000 usuarios.
- Los tres checks de GitHub Actions del commit `9dc9a4b` terminaron
  `completed/success` antes de esta nueva actualización de evidencia.
- Evidencia sanitizada: [resultado E2E](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15-0515UTC.json).

## Revalidación posterior — 05:18–05:26 UTC

- AWS STS autenticó en la cuenta Academy `841113066612`. CloudFormation sigue
  `UPDATE_COMPLETE`; ambos destinos siguen `healthy`; el ALB solo expone el
  listener HTTP/80. El health HTTP del portal respondió 200 a las 05:26:20 UTC.
- Azure for Students sigue `Enabled` y el endpoint HTTPS `/api/health` respondió
  `{"status":"ok","service":"tangamandapio-wms"}`. La lectura de inventario
  ARM mediante Azure CLI y REST expiró tras 20 s; no se afirma que el estado
  completo de recursos haya sido inspeccionado.
- El certificado ACM `tangamandapio.kendellnm.me` continúa
  `PENDING_VALIDATION`. El resolver público no encuentra el CNAME esperado
  `_9568d15842cb7c5bd79e0208316e57af.tangamandapio.kendellnm.me`.
  Las capturas recientes muestran el CNAME del subdominio hacia el ALB con proxy
  Cloudflare y otros CNAME de validación; ninguno visible coincide con el
  token de validación actual. Mantener el registro ACM en DNS only.
- Suite local repetida: 152 pruebas Python (157 subtests), 8 pruebas de permisos,
  6 pruebas CSV, build Vite y `cfn-lint`, todo aprobado. GitHub Actions del
  commit `a1c1596f77071a2b821558cce3d0a05a6b70dba8` terminó `success`; local y
  remoto coinciden.
- No hubo despliegue ni cambio de recursos en esta revalidación. HTTPS y la
  prueba WebRTC de dos navegadores siguen pendientes del CNAME ACM y del
  listener 443.
