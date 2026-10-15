# Revalidación local en vivo — 13/10/2026 18:39 America/Chicago

## Comprobación HTTP adicional — 13/10/2026 23:40 America/Chicago

Sin reiniciar servicios ni iniciar sesión, el portal local en
`http://127.0.0.1:8080` respondió `/health` HTTP 200 con
`{"database":"ok","status":"ok"}` y `/ready` HTTP 200 con
`{"dependencies":{"database":"ok"},"status":"ready"}`. Es una lectura
puntual de la app local; no verifica permisos de una sesión autenticada ni
actualiza el estado de AWS/Azure.

## Actualización — 13/10/2026 19:02 America/Chicago

Se reconstruyó el contenedor local de la aplicación para servir la corrección
ERP más reciente, preservando el volumen nombrado `app_aws-data` montado en
`/data`. El contenedor figura `healthy` y fue creado a las 00:01:36 UTC del
14/10. Sin sesión, `/`, `/health`, `/ready` y el bundle
`/assets/index-DXBGVYDc.js` devolvieron HTTP 200; `/api/erp/overview` devolvió
401, que confirma que no se expone el resumen a una petición anónima. La
autorización por rol de datos financieros se cubre con pruebas automatizadas
de la [QA local](QA-LOCAL-2026-10-13.md); no se introdujo una sesión real ni se
hizo una comprobación visual autenticada en navegador.

Esta reconstrucción afecta solo al contenedor local. No se reiniciaron ni
modificaron recursos AWS o Azure.

Comprobación de solo lectura, sin reiniciar contenedores ni modificar datos.
La configuración de Compose se resolvió para `docker compose ps` usando valores
efímeros solo en el proceso de consulta; no se recrearon servicios ni se
escribieron en archivos.

## Servicios locales

Los tres servicios del perfil predeterminado estaban `running` y `healthy`:
`aws-app`, `azure-service` y `mailpit`. El perfil opcional `ops` (Prometheus,
Grafana y Portainer) no se activó en esta comprobación.

## Respuestas HTTP

| Prueba | Resultado | Interpretación |
|---|---:|---|
| Portal `/` | 200 | La interfaz sirve contenido |
| `/health` | 200 | Aplicación y base local responden |
| `/ready` | 200 | La instancia está lista |
| Assets de administración JS/CSS | 200 | Recursos de la consola existen y se sirven |
| `/administracion` sin sesión | 303 | Redirección al flujo de autenticación esperada |
| API de alarmas sin sesión | 401 | Rechazo de autenticación esperado |
| `/api/auth/session` | 200 | Endpoint de sesión disponible |
| Health de `azure-service` con clave demo local | 200 | Function de laboratorio local responde |
| API de Mailpit | 200 | Bandeja SMTP de pruebas responde |

La protección HTTP se verificó sin iniciar sesión; por ello no se afirma aquí
una prueba visual autenticada ni una prueba manual de permisos dentro del
navegador. La cobertura de roles sigue siendo la de las pruebas automatizadas
registradas en [QA local](QA-LOCAL-2026-10-13.md).

Esta revisión acredita únicamente el stack local. No cambia el estado de AWS ni
Azure desplegados y no sustituye el inventario cloud ni la verificación manual
en Chrome.
