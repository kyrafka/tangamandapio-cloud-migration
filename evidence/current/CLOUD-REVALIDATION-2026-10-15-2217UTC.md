# Revalidación AWS/Azure y E2E — 15/10/2026, 22:17–22:24 UTC

## Estado verificado

- AWS STS autenticó la cuenta de laboratorio `841113066612`. CloudFormation
  `tangamandapio-live-20261013` permanece `UPDATE_COMPLETE`; la detección de
  drift iniciada en este corte terminó `DETECTION_COMPLETE` / `IN_SYNC`, con
  cero recursos desviados.
- El stack conserva el release v16
  `20261015-edge-cache-safe-landing-v16-python312` y SHA-256
  `94b9bea7808368fb46f771196bdae792e26babd6aaf22718a9d1917daf0996fe`.
  El dominio configurado es `tangamandapio.kendellnm.me`.
- ASG `tangamandapio-asg`: mínimo/deseado 2, máximo 5; ambas EC2 `InService` y
  `Healthy`. El target group tiene 2/2 destinos `healthy`.
- Portal externo: HTTPS `/`, `/health` y `/ready` devolvieron 200; HTTP redirige
  a HTTPS con 301. No se cambió infraestructura en esta revalidación.
- RDS `tangamandapio-postgres`: `available`, cifrada y privada; Single-AZ,
  `db.t3.micro`, 20 GB y retención automática de backup de un día. No se alteró
  la base ni se ejecutó failover.
- De siete alarmas métricas con acciones habilitadas, seis estaban `OK`. La
  alarma Target Tracking de reducción estaba `ALARM` porque la CPU media
  (~1.05%) está bajo su umbral de 42%; el ASG ya está en su mínimo de dos. No
  corresponde a un target no saludable.

## Flujo real AWS → Azure y permisos

El smoke autenticado ejecutado desde una EC2 usó el ALB de origen con el dominio
y validación TLS, evitando depender del proxy Cloudflare para esta prueba.

- Admin autenticó y consultó el módulo de alarmas; SNS reportó dos suscripciones
  confirmadas y cero pendientes. No se cambió la lista ni se mandaron correos.
- Comercial tuvo 200 en ventas ERP y 403 en outbox, WMS y administración.
  Operaciones tuvo 200 en outbox/WMS y 403 en ventas y administración.
- La importación del SKU QA ya existente preservó su saldo. La venta sintética
  llegó por RDS/outbox al worker Azure como `completed_demo`; la compra
  compensatoria terminó `received_demo`. Ambos eventos quedaron entregados y
  el ledger ficticio regresó de 10 a 10.
- 24 lecturas autenticadas de ventas, compras y outbox: 24/24 HTTP 200,
  concurrencia 6, p95 193.71 ms. Es una prueba corta desde una instancia, no
  demuestra carga de 3,000 usuarios ni escalado bajo carga.
- Azure Function `tangama-wms-261008`: `Running`, Linux, HTTPS-only; siete
  funciones habilitadas; `/api/health` devolvió 200. Application Insights en la
  última hora registró 89 solicitudes sin fallos; `process_fulfillment_message`
  tuvo 8 invocaciones/0 fallos y `receive_fulfillment_event` 9/0.
- Terraform Azure ejecutó un plan vivo usando el state configurado y el archivo
  local protegido de destinatarios: `No changes`. No se guardó un plan ni se
  ejecutó `apply`.
- El commit `a51e7b7` quedó publicado en `codex/aws-v11-deploy-sync`. Su GitHub
  Actions run `38816653227` terminó `success` en los tres jobs: backend/flujo,
  frontend e infraestructura.
- También se ejecutó el smoke Azure directo: guardas de ingreso 401/400 sin
  persistir el evento no autorizado, venta y reposición sintéticas procesadas,
  con el saldo de demo restaurado. Los registros de eventos QA permanecen en
  la auditoría Azure.

## Calidad local y defecto del arnés resuelto

La puerta `tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 182 pruebas Python, 14 Node, 40 transacciones aisladas,
build Vite, auditorías de dependencias, `cfn-lint`, seis raíces Terraform
validadas y pruebas mock de costo/red/recuperación. El paquete Azure
`364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d` coincide
con el código fuente.

La primera pasada del E2E AWS llegó a completar y compensar venta/reposición,
pero falló en la carga de lectura por usar `urlopen` en vez del opener propio
del destino. Se corrigió el arnés para reutilizar el transporte elegido (incluido
el bypass controlado de proxy para ALB-origen) y se agregó una prueba unitaria.
La ejecución posterior pasó completa. El código de producción no requería un
despliegue para este arreglo, porque el cambio está en el arnés de pruebas.

## Pendiente, sin darlo por cerrado

- No se completó la inspección visual autenticada de Admin/Comercial/Operaciones
  ni la importación CSV en Chrome: Computer Use terminó al no poder determinar
  con confianza la URL activa. No se intentó sortear esa barrera ni se cambió
  ninguna contraseña.
- No se probó WebRTC con dos navegadores reales.
- No existe conexión privada AWS–Azure; AWS Academy había denegado por SCP la
  creación de Customer Gateway. Este E2E usa HTTPS público, no VPN/BGP.
- RDS sigue Single-AZ con un día de retención; el restore aislado previamente
  medido no prueba failover Multi-AZ.
- La carga es acotada, no valida 3,000 usuarios. WMS continúa siendo un ledger
  sintético, no inventario físico.
- El cambio del arnés y la evidencia se sincronizaron con GitHub. `gh` no está
  instalado localmente; el estado de Actions se consultó por la API del repo.

No se guardaron credenciales AWS/Azure en el repositorio ni en este informe.
