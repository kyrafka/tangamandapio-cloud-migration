# Estado AWS y HTTPS — 15/10/2026

## Verificación viva

Corte consultado aproximadamente a las 13:47 UTC. No se guardan credenciales ni
secretos en esta evidencia.

- El CNAME de validación de ACM resuelve públicamente:
  `_9568d15842cb7c5bd79e0208316e57af.tangamandapio.kendellnm.me` →
  `_5dddcef8a8f2271fe364f121e81b0951.wzccmgtwzk.acm-validations.aws`.
  ACM informa certificado `ISSUED` y validación `SUCCESS` para
  `tangamandapio.kendellnm.me`.
- El registro de aplicación apunta al ALB
  `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` mediante Cloudflare.
  Como el proxy está activado, las respuestas A públicas son IPs de Cloudflare;
  no deben fijarse ni usarse como IP del ALB. El destino CNAME sigue siendo
  válido mientras se conserve el mismo ALB.
- CloudFormation `tangamandapio-live-20261013` terminó `UPDATE_COMPLETE`; su
  salida `ApplicationURL` es `https://tangamandapio.kendellnm.me`. La detección
  de drift terminó `IN_SYNC`.
- El ALB tiene HTTPS/443 con el certificado ACM y acción `forward`; HTTP/80
  redirige a HTTPS. La URL pública `/health` y `/ready` respondió 200; HTTP
  `/health` respondió 301 a la URL HTTPS.
- `/api/auth/session` entregó cookie con `Secure`, `HttpOnly` y `SameSite=Lax`.
- ASG `tangamandapio-asg`: mínimo/deseado 2, máximo 5; dos instancias
  `InService` y saludables. Durante la actualización hubo un destino drenando;
  no forma parte de la capacidad deseada final.
- RDS PostgreSQL está `available`, cifrada, Single-AZ y conserva un día de
  retención de backups. No se cambió su topología en esta actualización.

## Límite observado en la prueba funcional

Se intentó la prueba integral existente usando el dominio HTTPS. En ambos
intentos el runner se detuvo en el login admin antes de crear pedidos o alterar
el inventario sintético; informó `POST /api/auth/login` HTTP 403 y
`compensation=not_needed`. En el mismo periodo, los registros de aplicación
incluyeron un rechazo de login HTTP 401. La causa de la diferencia entre el
estado visto por el runner y el registro del origen no quedó aislada. Por eso
no se declara pasada la prueba de login/roles/venta por el dominio; hace falta
revisar el origen de la credencial QA y repetir una sola vez tras diagnosticar.

Las pruebas unitarias locales de `tests/cloud` sí pasaron: 16/16. La prueba
anterior contra el ALB antes de HTTPS no sustituye esta prueba del hostname.
