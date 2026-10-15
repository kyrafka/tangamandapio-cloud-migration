# Revalidación del portal y consolas cloud — 15/10/2026, 19:21–19:23 UTC

Comprobaciones de solo lectura desde Chrome y los CLI disponibles. No se
modificaron pedidos, usuarios, inventarios ni recursos de nube.

## Portal y acceso

- `https://tangamandapio.kendellnm.me/`, `/health` y `/ready` devolvieron HTTP
  200; el health reportó `status=ok` a las 19:21:27 UTC y readiness
  `status=ready`.
- Azure Function `https://tangama-wms-261008.azurewebsites.net/api/health`
  devolvió HTTP 200 y `status=ok`. La cuenta CLI sigue siendo Azure for
  Students, estado `Enabled`.
- El portal cargó la portada y el panel de inicio de sesión; el registro de
  consola del navegador no mostró errores JavaScript. No se introdujeron
  credenciales. Las vistas internas y permisos no se probaron visualmente.

## AWS — consola y artefactos

- La sesión visual de AWS Console sigue abierta en la cuenta Academy
  `841113066612`, región `us-east-1`.
- Tras actualizar el grupo de destino, la consola mostró 2/2 destinos
  `Healthy`, 0 anómalos. El último chequeo mostrado para ambos fue el
  15/10/2026 a las 12:19 CDT (17:19 UTC).
- CloudFormation mostró `tangamandapio-live-20261013` en
  `UPDATE_COMPLETE`, con 47 recursos listados. La pila de grabaciones también
  figura `CREATE_COMPLETE`. No se ejecutó detección de drift en esta revisión;
  `UPDATE_COMPLETE` no se presenta como prueba de `IN_SYNC`.
- El prefijo `s3://tangamandapio-841113066612-us-east-1/releases/tangamandapio/`
  mostró 10 objetos, incluido el paquete v12
  `portal-b2b-20261015-login-drawer-a11y-v12-python312-c884314dd8ec617df90739aeee25d2f912d7e1d70ec1e66d442fbc6720407c13.tar.gz`.
  No se observó v13 entre esos objetos; existe una subcarpeta `qa/` que no se
  inspeccionó.
- El AWS CLI local devuelve `ExpiredToken` en `sts get-caller-identity`; por
  tanto no se hicieron consultas ni despliegues desde CLI. La sesión web de la
  consola y la identidad del CLI son estados distintos.
- No se consultó RDS en esta pasada; su disponibilidad, cifrado, Multi-AZ y
  retención siguen sin confirmación actual.

## Alcance pendiente

- El navegador está en login. Por seguridad, el agente no puede ingresar
  credenciales en el diálogo de autenticación; el usuario debe iniciar sesión
  manualmente para poder recorrer Admin, Comercial, Operaciones, ERP, WMS,
  CSV, correo y telefonía desde Chrome.
- Esta revisión no invocó el procesamiento Azure ni creó eventos de prueba.
  `/api/health` confirma disponibilidad, no consumo de Queue.
- Siguen pendientes una sesión AWS CLI renovada para inventario/drift/RDS y
  cualquier despliegue del candidato local v13.
