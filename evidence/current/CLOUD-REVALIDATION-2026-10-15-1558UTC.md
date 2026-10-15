# Revalidación AWS y navegador — 15/10/2026, 15:40–15:58 UTC

Esta nota reemplaza el estado operativo del corte de las 14:45 para el portal
AWS. No certifica criterios que no se probaron en esta revisión.

## AWS

- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`, última
  actualización `2026-10-15T15:40:08Z`.
- Release desplegado: `20261015-login-drawer-a11y-v12-python312`.
  El artefacto se referencia en el stack con SHA-256
  `c884314dd8ec617df90739aeee25d2f912d7e1d70ec1e66d442fbc6720407c13` y llave
  privada `releases/tangamandapio/portal-b2b-20261015-login-drawer-a11y-v12-python312-c884314dd8ec617df90739aeee25d2f912d7e1d70ec1e66d442fbc6720407c13.tar.gz`.
- Auto Scaling Group `tangamandapio-asg`: deseado/mínimo 2, máximo 5; dos EC2
  `InService`/`Healthy`, ambas con launch template versión 14. La EC2 previa
  versión 13 estaba `Terminating`; el target seguía `draining` durante la
  desregistración y no se cuenta como capacidad activa.
- ALB `tangamandapio-alb`: `active`, internet-facing; ambos targets v14
  `healthy` en puerto 8080, health check `/health`. HTTPS/443 reenvía al grupo;
  HTTP/80 redirige a HTTPS/443 con 301.
- Certificado ACM para `tangamandapio.kendellnm.me`: `ISSUED`, asociado al ALB.
- RDS `tangamandapio-postgres`: `available`, privada, cifrada, Single-AZ y
  retención de backups de un día. Esta actualización no cambió la base de datos.

## Prueba en Chrome sobre el dominio HTTPS

La prueba se hizo dentro de la pestaña de Chrome del portal publicado; no se usó
localhost ni se controlaron otras ventanas. Después de recargar, el HTML cargó
`/assets/accessibility-drawer-7f1356105ee4.js`. La portada y el panel de acceso
se mostraron correctamente, y la consola del sitio no informó errores ni
advertencias.

- Al cerrar el panel, el helper aplicó `inert` y `aria-hidden="true"`; el foco
  quedó en el botón visible `Acceder`. Al pulsar Tab no se enfocó el campo de
  usuario oculto.
- Al reabrir el panel, el foco regresó al campo `Usuario corporativo`.
- Se comprobó el cambio a tema claro y se restauró el tema oscuro.
- Se dejó abierta la pantalla de acceso para que Diego pueda iniciar sesión.
  No se introdujeron credenciales; las vistas privadas y los permisos por rol
  siguen pendientes de esa autenticación manual.

## Límites y siguientes verificaciones

Esta revisión no ejercitó ventas/ERP, importación CSV, eventos Azure/WMS,
notificaciones SNS, llamadas WebRTC ni carga transaccional. Tampoco se desplegó
la VPN AWS–Azure. Esos criterios siguen pendientes y no quedan certificados por
un `UPDATE_COMPLETE` ni por la prueba de la portada.
