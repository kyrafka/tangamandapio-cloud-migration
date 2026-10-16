# Revalidación cloud y recuperación RDS — 16/10/2026, 09:05–09:17 UTC

## Estado en vivo

- AWS STS aceptó la sesión del laboratorio. CloudFormation `tangamandapio-live-20261013`
  está `UPDATE_COMPLETE`; detección fresca de drift finalizó a las 09:05 UTC con
  `IN_SYNC` y cero recursos divergentes.
- Las dos instancias EC2 están `InService`/`Healthy`; ambos destinos del ALB están
  `healthy`. Sus volúmenes raíz están `in-use` y cifrados con KMS. El portal en
  `https://tangamandapio.kendellnm.me/health` respondió 200 con verificación TLS
  correcta; HTTP respondió 301 hacia HTTPS.
- Azure health respondió 200 con verificación TLS correcta. AWS y Azure CLI
  autenticaron en este corte; no se aplicó Terraform ni CloudFormation.
- RDS principal sigue `available`, privado y cifrado; Single-AZ, retención de
  backup de un día, última ventana recuperable observada 09:09:58 UTC. No se
  cambiaron estos parámetros.

## PT-DR-01 — restauración desde snapshot

La prueba puntual terminó `PASSED`. El ensayo creó un marcador SQL sintético,
snapshot `tng-dr-snap-20261016090651` y copia de restauración
`tng-dr-restore-20261016090651`. La copia abrió privada y cifrada; el marcador
anterior al snapshot y los conteos de las tablas de negocio coincidieron con el
checkpoint. RTO observado: 258 s; límite superior medido para RPO: 8 s.

La limpieza automática reportó `verified`; una consulta posterior confirmó que
ya no existen la copia ni el snapshot temporales. La base principal quedó
`available`. Esto demuestra restauración a partir de snapshot y verificación de
datos, no failover Multi-AZ ni una garantía general de RPO/RTO.

## Alarmas y controles pendientes

- La alarma administrada de scale-in target tracking está `ALARM` porque CPU
  promedio (~1.1%) permanece bajo el umbral de 42%; es la señal de reducción de
  capacidad, no una alarma de salud. En la revisión ambos targets y alarmas de
  disponibilidad/5xx estaban sanos.
- `EnableWaf=false` y `list-web-acls` no devolvió ACL. CloudFormation describe
  WAF como costo con aprobación explícita; no se habilitó ni se generó ese costo.
- No existe VPN privada AWS–Azure: AWS Academy niega `CreateCustomerGateway` por
  SCP. Siguen abiertas la inspección visual autenticada/CSV, WebRTC con dos
  navegadores, falla/reintento inducido, carga sostenida, WAF y failover
  Multi-AZ. El ledger WMS continúa siendo sintético.

## Alcance de los cambios

Este corte solo revalidó servicios y ejecutó PT-DR-01 con recursos temporales
aislados. No se desplegó código de aplicación ni se aplicó IaC.
