# Revalidación de disponibilidad AWS–Azure — 16/10/2026, 05:44–06:10 UTC

## Resultado actual

- El FQDN `https://tangamandapio.kendellnm.me` resuelve por Cloudflare y la
  verificación TLS termina correctamente (`ssl_verify_result=0`). Sin embargo,
  `/` y `/health` devolvieron HTTP 503 desde el borde Cloudflare. HTTP termina
  redirigiendo a HTTPS y también recibe 503.
- Se probó el origen conocido directamente. ALB HTTP/80 respondió 301 hacia
  HTTPS; una solicitud HTTPS al ALB con el `Host` del dominio devolvió HTTP 503
  desde `awselb/2.0`. Esto ubica el fallo después del listener HTTPS, en el
  servicio/origen detrás del balanceador. No confirma por sí solo el estado de
  cada destino ni la causa exacta. Consultas repetidas a las 05:51 y 05:58 UTC
  volvieron a recibir 503 del health público y del origen directo; TLS del
  dominio siguió válido.
- STS rechazó el token AWS recién compartido con `InvalidClientTokenId`. El
  token se usó solo en variables del proceso de prueba; no se guardó ni se
  reemplazó el perfil local `default`. No se hicieron cambios en AWS.
- Azure for Students figura `Enabled`. El grupo
  `rg-tangamandapio-rebuild-wus` figura `Succeeded`; Function
  `tangama-wms-261008` figura `Running`/HTTPS-only y sus siete funciones están
  indexadas. `https://tangama-wms-261008.azurewebsites.net/api/health` respondió
  HTTP 200 con TLS válido y `{"status":"ok","service":"tangamandapio-wms"}`.
- El inventario ARM de solo lectura contó 10 recursos en el grupo: una Function
  y un plan, una Storage Account, un Key Vault, un workspace Log Analytics, un
  componente Application Insights, dos alertas métricas y dos Action Groups.
  No se imprimieron direcciones de receptores ni secretos.
- A las 06:04 UTC, STS rechazó el token AWS recién recibido con
  `InvalidClientTokenId`. No se sobrescribió el perfil local y no se hicieron
  cambios en AWS.
- A las 06:09 UTC se repitió el flujo E2E contra Azure desde el release local:
  Function `Running`, venta sintética entregada por outbox y completada como
  `demo_fulfillment_completed`, recepción compensatoria `demo_restock_completed`
  y ledger ficticio restaurado al saldo base. Salida `LIVE_E2E=PASSED`, código
  de salida 0. No fue tráfico originado desde EC2/RDS.
- En la sonda posterior de las 06:10 UTC, el health público aún respondió HTTP
  503 desde Cloudflare; el health de la Function Azure respondió HTTP 200 con
  TLS válido.
- Terraform consultó el backend remoto Azure con las variables de reconstrucción
  y alertas locales; el plan terminó `No changes` a las 05:57 UTC. No se guardó
  un plan aplicable ni se ejecutó `apply`.

## Flujo Azure sintético

Entre aproximadamente 05:45 y 05:47 UTC se ejecutó
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

Una repetición a las 06:09 UTC volvió a aprobar autenticación y sesión, alta de
contrapartes sintéticas, venta ERP, outbox durable, lectura/reconciliación del
resultado y recepción compensatoria; el ledger volvió al saldo inicial. IDs de
auditoría Azure: venta `evt-0cf05101ca0942a09ff51610ba99ab4c` y compensación
`evt-795a36230f7843c7978b675dbae3d58d`. Los resultados fueron
`demo_fulfillment_completed` y `demo_restock_completed`. Salida 0. Sigue siendo
una prueba con release local y SQLite temporal; no prueba EC2/RDS, disponibilidad
del portal AWS ni conectividad privada.

## Siguiente paso necesario

El portal público está actualmente indisponible aunque HTTPS y el listener de
redirección respondan. Con una sesión AWS Academy aceptada hay que consultar
sin cambios el stack, ASG, target group y logs; identificar por qué el ALB
devuelve 503; corregir y volver a verificar `/`, `/health`, `/ready`, login y
roles antes de afirmar que el proyecto quedó levantado. No reiniciar ni
desplegar a ciegas. Después siguen pendientes la pasada visual de módulos y
WebRTC entre dos navegadores reales, además de brechas de rúbrica ya registradas
(VPN privada, failover Multi-AZ, WAF y capacidad sostenida).
