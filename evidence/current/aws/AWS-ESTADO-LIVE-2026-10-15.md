# Estado AWS y HTTPS — 15/10/2026

## Verificación viva

Corte consultado aproximadamente a las 13:56 UTC. No se guardan credenciales ni
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
  `InService` y saludables. El reemplazo gradual terminó.
- RDS PostgreSQL está `available`, cifrada, Single-AZ y conserva un día de
  retención de backups. No se cambió su topología en esta actualización.

## Pruebas funcionales y límite pendiente

La prueba integral ejecutada dentro de la instancia EC2 contra `127.0.0.1:8080`
terminó `LIVE_E2E_PASSED`. El login de admin y los controles de rol pasaron:
Comercial obtuvo 200 en ventas y 403 en rutas restringidas; Operaciones obtuvo
200 en outbox/inventario y 403 en ventas/admin. La prueba envió dos eventos a
Azure y reconcilió venta `completed_demo` y recepción `received_demo`; el saldo
del SKU sintético volvió exactamente de 10 a 10. La base respondió `ok`, las
dos suscripciones de alarma estaban confirmadas y 24/24 lecturas autenticadas
de pedidos/outbox dieron 200 con concurrencia 6 (p95 264.37 ms).

La variante que pasa por el dominio HTTPS no logró iniciar sesión. Un probe
sanitizado devolvió HTTP 403 con `Server: cloudflare`, un `CF-Ray` y sin
`X-Request-ID` del portal; el mismo secreto QA funciona en la prueba de
loopback. Esto señala un rechazo en la ruta proxied de Cloudflare, no un
problema de certificado ni una credencial de admin inválida. No se crearon
pedidos en los intentos HTTPS fallidos. Falta revisar el evento Cloudflare
asociado al Ray ID y permitir el POST legítimo a `/api/auth/login` sin
desactivar el proxy ni abrir el origen públicamente. No se afirma que el login
de navegador real ya se haya verificado.

Las pruebas unitarias locales de `tests/cloud` pasaron: 16/16. La integración
productiva EC2→Azure se verificó por loopback de la app EC2; el paso por el
dominio público queda pendiente por el bloqueo anterior.
