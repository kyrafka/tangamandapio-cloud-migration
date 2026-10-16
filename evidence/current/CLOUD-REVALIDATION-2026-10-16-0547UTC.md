# Revalidación de disponibilidad AWS–Azure — 16/10/2026, 05:44–05:51 UTC

## Resultado actual

- El FQDN `https://tangamandapio.kendellnm.me` resuelve por Cloudflare y la
  verificación TLS termina correctamente (`ssl_verify_result=0`). Sin embargo,
  `/` y `/health` devolvieron HTTP 503 desde el borde Cloudflare. HTTP termina
  redirigiendo a HTTPS y también recibe 503.
- Se probó el origen conocido directamente. ALB HTTP/80 respondió 301 hacia
  HTTPS; una solicitud HTTPS al ALB con el `Host` del dominio devolvió HTTP 503
  desde `awselb/2.0`. Esto ubica el fallo después del listener HTTPS, en el
  servicio/origen detrás del balanceador. No confirma por sí solo el estado de
  cada destino ni la causa exacta. Una segunda consulta cerca de las 05:51 UTC
  volvió a recibir 503 del health público y del origen directo; TLS del dominio
  siguió válido.
- STS rechazó el token AWS recién compartido con `InvalidClientTokenId`. El
  token se usó solo en variables del proceso de prueba; no se guardó ni se
  reemplazó el perfil local `default`. No se hicieron cambios en AWS.
- Azure for Students figura `Enabled`. El grupo
  `rg-tangamandapio-rebuild-wus` figura `Succeeded`; Function
  `tangama-wms-261008` figura `Running`/HTTPS-only y sus siete funciones están
  indexadas. `https://tangama-wms-261008.azurewebsites.net/api/health` respondió
  HTTP 200 con TLS válido y `{"status":"ok","service":"tangamandapio-wms"}`.

## Flujo Azure sintético

Entre aproximadamente 05:45 y 05:47 UTC se volvió a ejecutar
`tests/run_live_azure_erp_smoke.py` con su opt-in explícito. La prueba mantuvo
SQLite en una carpeta temporal y no usó la EC2 ni RDS desplegadas. Guards:
401 sin Function key, 400 para origen no autorizado y evento rechazado no
persistido. La venta sintética se procesó como `demo_fulfillment_completed`,
la compra compensatoria como `demo_restock_completed`, y el ledger ficticio
volvió al saldo inicial. La cola poison reportó cero antes y después usando
solo metadatos. Los eventos válidos permanecen en la auditoría Azure:

- Venta: `evt-f46efe05278649738520a7d5bce08a63`.
- Compensación: `evt-bd7f8a28d17143bdb9543148518d20a5`.

Resultado: `LIVE_E2E=PASSED` para el flujo local→Azure. No es una prueba
AWS→Azure desde EC2/RDS ni conectividad privada.

## Siguiente paso necesario

El portal público está actualmente indisponible aunque HTTPS y el listener de
redirección respondan. Con una sesión AWS Academy aceptada hay que consultar
sin cambios el stack, ASG, target group y logs; identificar por qué el ALB
devuelve 503; corregir y volver a verificar `/`, `/health`, `/ready`, login y
roles antes de afirmar que el proyecto quedó levantado. No reiniciar ni
desplegar a ciegas. Después siguen pendientes la pasada visual de módulos y
WebRTC entre dos navegadores reales, además de brechas de rúbrica ya registradas
(VPN privada, failover Multi-AZ, WAF y capacidad sostenida).
