# Revalidación HTTPS, nube y navegador — 15/10/2026, 14:20–14:30 UTC

Solo se hicieron lecturas de estado y pruebas funcionales acotadas. No se
actualizaron recursos cloud, no se ejecutó `terraform apply` y no se registró
ningún pedido. La prueba de login usó valores sintéticos de dominio `.invalid`;
la página se recargó al terminar.

## AWS

- STS autenticó el perfil local `default` en la cuenta académica
  `841113066612`.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; última
  actualización `2026-10-15T13:31:11Z`; salida `ApplicationURL` HTTPS.
- ALB `tangamandapio-alb`: `active`, internet-facing. El listener HTTPS/443
  reenvía a la aplicación y HTTP/80 redirige a HTTPS.
- Los dos destinos del target group están `healthy`; ASG mínimo/deseado/máximo
  2/2/5 y ambas instancias `InService`/`Healthy`.
- ACM para `tangamandapio.kendellnm.me`: `ISSUED`.
- RDS `tangamandapio-postgres`: `available`, cifrada y no pública. Sigue
  Single-AZ (`MultiAZ=false`) y con retención de backup de un día: disponibilidad
  y recuperación aún son limitadas frente al objetivo de producción.
- `/health` y `/ready` en el dominio devolvieron HTTP 200.

## Azure

- La Function `tangama-wms-261008` se reportó `Running` y `httpsOnly=true`.
- `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200
  con `{"status":"ok","service":"tangama-wms"}`.
- Esto confirma salud del endpoint, no procesamiento de un evento nuevo en este
  corte. El procesamiento AWS→Azure ya tiene evidencia separada en
  [el E2E del 15/10](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json).

## Navegador Chrome — portal HTTPS

Se usó únicamente la pestaña del portal en Chrome; no se abrió localhost ni se
manipularon otras ventanas.

- La portada y sus imágenes de fondo se mostraron completas; la consola del
  navegador no registró errores ni advertencias.
- El panel de acceso se abrió/cerró; el envío vacío activó la validación nativa.
- La navegación de teclado llegó de usuario a contraseña y luego al botón de
  ingreso.
- Un intento con usuario `qa-ui-smoke@example.invalid` y contraseña ficticia
  regresó el mensaje esperado “Credenciales inválidas o cuenta deshabilitada”,
  sin bloqueo de Cloudflare. Luego se recargó la página; no se autenticó. El
  intento puede haber generado un registro normal de autenticación fallida;
  no se cambiaron contraseñas ni cuentas.
- A 390×844 px, `documentElement.clientWidth` y `scrollWidth` fueron ambos 390:
  no hubo desbordamiento horizontal. La vista se restauró al tamaño normal.

La cuenta permaneció sin sesión autenticada. Por ello, esta evidencia no cubre
las vistas privadas, la matriz visual de roles, importación CSV desde archivo,
la venta ERP por navegador ni WebRTC entre dos navegadores.

## Límites que permanecen

- No se ha comprobado conectividad privada AWS–Azure. El preflight previo
  registró rechazo explícito de `ec2:CreateCustomerGateway` por la SCP de AWS
  Academy; el flujo existente llega a Azure por HTTPS público.
- RDS conserva Single-AZ y un día de backups; la prueba de restauración previa
  fue puntual y no equivale a alta disponibilidad.
- No se hizo una carga transaccional a través del ALB ni una prueba real de
  escala a 3,000 usuarios.
- WMS mantiene ledger/inventario sintético; correo interno/relay de prueba no
  constituye correo corporativo ni SMTP productivo configurado.
- Este corte de verificación no sustituye aprobación de rúbrica ni evidencia del
  docente.

## Sincronización y CI de GitHub — 15/10/2026, 14:31–14:32 UTC

El commit `f6d7eaf` está publicado en `codex/aws-v11-deploy-sync`. La API de
GitHub reportó los tres check runs `completed/success`: backend/Azure worker y
flujo, validación de infraestructura AWS/Azure y build/auditoría frontend.
[Ejecución de Actions](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38752199176).
