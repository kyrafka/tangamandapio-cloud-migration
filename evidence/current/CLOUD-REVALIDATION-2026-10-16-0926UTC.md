# Reconciliación IaC y revalidación cloud — 16/10/2026, 09:25–09:26 UTC

## AWS

- AWS STS válido; CloudFormation `tangamandapio-live-20261013` terminó
  `UPDATE_COMPLETE` a las 09:25:23 UTC. El change set desplegado modificó solo
  `InServiceCapacityAlarm.AlarmDescription` in-place (`Replacement=False`);
  no cambió EC2, RDS, red, ALB ni capacidad del grupo.
- El stack desplegado ahora contiene los defaults del artefacto v18 y las cinco
  reglas de seguridad de parámetros presentes en
  `iac/cloudformation/aws-lab.yaml`. La comparación estructural halló los 53
  recursos y sus definiciones iguales; las únicas diferencias remanentes están
  en algunas descripciones de parámetros/salidas/reglas, no en defaults ni en
  recursos.
- Drift fresco terminado 09:26:12 UTC: `IN_SYNC`, cero recursos divergentes.
  Dos EC2 y dos targets del ALB siguen sanos; health del portal HTTPS/TLS 200,
  HTTP redirige 301. Azure Function health HTTPS/TLS 200.
- RDS sigue `available`, privada y cifrada, Single-AZ con retención de un día.
  No se alteraron parámetros de base de datos.
- La vista WAF sigue apagada (`EnableWaf=false`), sin ACL regional. No se habilitó
  por costo; se pidió aprobación antes de activar el control.

## Validación local

`tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 225 pruebas Python, 14 Node, 40 transacciones aisladas,
Vite build, auditorías de dependencias sin vulnerabilidades conocidas,
CloudFormation validado, Terraform `fmt`/`init`/`validate` y 5 pruebas mock de
red/costo. No hizo `apply` ni operaciones cloud.

PT-DR-01, ejecutada en el mismo corte (09:06–09:17), restauró desde snapshot con
marcador y conteos coincidentes, RTO 258 s/RPO superior observado 8 s; snapshot
y copia temporal fueron eliminados y su ausencia quedó verificada. No demuestra
failover Multi-AZ. La base sigue Single-AZ.

## Pendientes que siguen abiertos

No se probaron recorrido visual autenticado/CSV ni WebRTC entre dos navegadores;
tampoco una falla transitoria live con reintento, carga sostenida/3,000 usuarios
ni failover Multi-AZ. VPN AWS–Azure sigue bloqueada por SCP que niega
`CreateCustomerGateway`; no hay VNet del proyecto. WAF requiere aprobación de
costo. El WMS continúa siendo ledger de inventario sintético.
