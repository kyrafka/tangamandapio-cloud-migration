# Revalidación HTTPS, Azure y acceso AWS — 15/10/2026, 19:12–19:13 UTC

Este corte separa los endpoints públicos comprobados de las vistas que exigen
sesión. No se modificaron recursos de nube durante estas comprobaciones.

## Portal HTTPS

- `https://tangamandapio.kendellnm.me/`: HTTP 200, título `Tangamandapio Cloud`.
- `/health` y `/ready`: HTTP 200.
- Nueve recursos JavaScript/CSS referenciados por la portada: HTTP 200.
- La pestaña Chrome sigue en el formulario de acceso. No se ingresaron
  credenciales y no se comprobaron las vistas privadas.

## Azure

- Suscripción `Azure for Students`: estado `Enabled`.
- Grupo `rg-tangamandapio-rebuild-wus`: `Succeeded`, región West US.
- Function App `tangama-wms-261008`: `Running`, `httpsOnly=true`.
- `https://tangama-wms-261008.azurewebsites.net/api/health`: HTTP 200.
- El GET de salud confirma disponibilidad del proceso, no por sí solo el
  procesamiento de mensajes. El E2E funcional previo está documentado en
  [smoke ERP–Azure 15/10](azure/AZURE-LIVE-ERP-SMOKE-2026-10-15.md).

## AWS

- AWS STS autenticó inicialmente la cuenta Academy `841113066612`.
- `cloudformation:DescribeStacks` y
  `elasticloadbalancing:DescribeTargetHealth` fueron rechazados por una
  denegación explícita de `voc-cancel-cred`; consultas posteriores devolvieron
  `ExpiredToken`. El inventario actual de AWS queda **sin verificar**.
- Última evidencia previa, a las 18:56 UTC: stack v12 `IN_SYNC` y dos targets
  sanos. Eso es un estado anterior, no una observación actual.
- La plantilla local apunta al artefacto v13 de SHA-256
  `d0e4f6b6ccadff7eb1edac2026211d081c2f1df941c6884e64ff0cab2e2c9c57`; el
  paquete existe localmente. No se confirmó su presencia en S3 ni su despliegue
  y no se hicieron escrituras AWS.

## Calidad local

- `tests/run_local_quality.ps1`: 181 pruebas unitarias, build de producción,
  CloudFormation y auditorías aprobadas; cero vulnerabilidades conocidas en
  las auditorías ejecutadas.
- Frontend: ocho pruebas de permisos/navegación, seis de importación CSV y
  build Vite aprobados; los nueve recursos de la web publicada también cargan.
- Terraform: `fmt -check` en los roots/módulos definidos, seis `validate` y
  cinco pruebas mock de red/costos aprobadas. No se ejecutó `apply`.

## Pendientes

- Renovar AWS CLI desde AWS Details y repetir inventario, publicación del
  paquete y despliegue controlado; el release v13 no está confirmado en nube.
- Completar manualmente el inicio de sesión en Chrome para probar los módulos
  por rol. El portal no se autenticó en este corte.
- Repetir E2E del portal desde AWS y las validaciones específicas de RDS,
  WebRTC entre dos navegadores y escalabilidad cuando exista acceso AWS.
