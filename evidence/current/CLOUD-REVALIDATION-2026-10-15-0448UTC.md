# Revalidación puntual de AWS, Azure y HTTPS — 15/10/2026, 04:48 UTC

Consultas de solo lectura posteriores al corte de las 04:10 UTC. No se aplicó
infraestructura, no se cambió configuración cloud y no se ejecutaron
transacciones de negocio.

## AWS

- STS aceptó el perfil temporal de AWS Academy en la cuenta `841113066612`.
- `tangamandapio-live-20261013` reportó `UPDATE_COMPLETE`; el ALB
  `tangamandapio-alb` está `active` y sus dos destinos están `healthy`.
- El ALB respondió HTTP 200 en `/health` y `/ready`.
- Solo existe listener HTTP/80; no hay listener HTTPS/443. HTTPS y el dominio
  siguen pendientes y el ALB no se declara seguro por HTTPS todavía.

## Azure

- La suscripción `Azure for Students` aparece `Enabled`.
- El inventario ARM encontró `tangama-wms-261008` en
  `rg-tangamandapio-rebuild-wus`, `Running`, con `httpsOnly=true`.
- `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200.
- El grupo `rg-tangamandapio-261005-wus` documentado por el root heredado
  `azure-demo` ya no existe en la suscripción activa; el root vigente de esta
  reconstrucción es `azure-rebuild`. No se intentó aplicar el root heredado.

## Preparación HTTPS y sincronización

- `tests/aws/certificate_preflight_test.sh` pasó con mocks: exige subdominio y
  ARN juntos, región del ALB, certificado `ISSUED` y SAN compatible antes de
  llegar a la validación/creación de change set.
- CloudFormation ya acepta un subdominio controlado por el usuario, crea el
  listener 443 con el certificado ACM y redirige HTTP/80 a HTTPS. Para DNS
  externo, ACM entrega CNAME de validación y el subdominio apunta al ALB con
  CNAME.
- No se activó HTTPS: aún falta el subdominio bajo un dominio cuyo DNS podamos
  administrar, emitir/validar su certificado y aprobar el change set.
- El HEAD local `ac9e27346282b4c055969c11440e35f757311624` coincide con
  `origin/codex/aws-v11-deploy-sync`; no había cambios rastreados pendientes al
  comprobarlo.

Esta verificación confirma disponibilidad técnica básica, no el cierre total de
la rúbrica. VPN privada AWS–Azure, HTTPS con hostname propio, pruebas WebRTC de
dos navegadores y una carga representativa siguen siendo criterios separados.

## Portada pública, VPN y CI — 15/10/2026, 04:53 UTC

- La portada pública respondió HTTP 200 en 913 ms y los ocho recursos JavaScript
  y CSS referenciados directamente respondieron HTTP 200. Es un smoke HTTP de
  entrega de archivos, no una evaluación visual autenticada ni una medición de
  animaciones/renderizado en navegador.
- AWS EC2 `CreateCustomerGateway --dry-run` devolvió `UnauthorizedOperation` por
  un `explicit deny` en una SCP de AWS Organizations. No se creó ningún recurso;
  el inventario sigue sin customer gateway, VPN gateway o VPN connection.
- Azure no tiene un VPN gateway en el grupo vigente. La conexión multinube no
  puede probarse hasta que el administrador de AWS Academy habilite el permiso
  denegado; no se intentará eludir esa política.
- El commit `ef006a9` quedó sincronizado en `origin/codex/aws-v11-deploy-sync` y
  GitHub Actions terminó `success`:
  https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38683627882
