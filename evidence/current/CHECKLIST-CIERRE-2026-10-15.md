# Checklist de cierre — corte 15/10/2026, 01:37 UTC

Esta hoja sustituye como estado vigente al checklist del 14/10; los informes
anteriores se conservan como evidencia histórica. No asigna una nota.

## Comprobado en este corte

- [x] AWS CLI `default` autenticado por STS en la cuenta Academy `841113066612`;
  el token temporal no se guardó en Git ni en el repositorio.
- [x] CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; una
  detección nueva confirmó `IN_SYNC`, cero recursos discrepantes.
- [x] Release v11 confirmado por SSM en las dos EC2; servicio activo. ASG
  mínimo/deseado 2, máximo 5; dos destinos del target group `healthy`.
- [x] ALB `/`, `/health` y `/ready` devolvieron HTTP 200; `/api/admin/users`
  sin sesión devolvió 401. Portal todavía HTTP, sin dominio ni TLS confiable.
- [x] RDS `available`, privada, cifrada, 20 GB, Single-AZ, retención automática
  de backup de un día. La infraestructura AWS coincide con CloudFormation en el
  corte; no se actualizó RDS en este release.
- [x] E2E autenticado v11 por SSM: Admin, Comercial y Operaciones; reglas 200/403;
  importación sintética, venta `completed_demo`, recepción `received_demo`, dos
  eventos entregados por Azure y ledger demo 10→10. La carga RDS 24/24 fue de
  solo lectura, desde EC2 por loopback (no por ALB).
- [x] Azure for Students autenticada; inventario de recursos del grupo
  `rg-tangamandapio-rebuild-wus` incluye Function, Storage, Key Vault, Application
  Insights y reglas de alertas.
- [x] Function `tangama-wms-261008` `Running`, `httpsOnly=true`; health HTTPS
  200. Application Insights consultado en vivo: 17 solicitudes en 24 h, cero
  fallidas; dos registros exitosos de `process_fulfillment_message` y dos de
  `receive_fulfillment_event`. Ver
  [evidencia Azure Monitor](azure/AZURE-MONITOR-INVOCACIONES-2026-10-15.md).
- [x] Gate local del 15/10: 165 pruebas Python, 14 Node, 40 transacciones
  aisladas, build, auditorías de dependencias, validaciones CloudFormation y
  Terraform `fmt`/`validate`/mocks; sin cambios cloud.
- [x] Terraform 1.16.0 Linux, igual a GitHub Actions: los cinco entornos pasan
  `fmt`, `init -backend=false -lockfile=readonly` y `validate`; pruebas mock
  5/5. Lockfiles completados con los hashes Linux faltantes sin cambiar
  versiones de proveedores.
- [x] Código, IaC y evidencia del corte publicados en GitHub, branch
  `codex/aws-v11-deploy-sync`, commit publicado `327549f`; `main` no se modificó. El token
  AWS y las contraseñas no forman parte del commit.
- [x] Checks de GitHub Actions en `327549f`: backend/flujo, frontend e
  infraestructura AWS/Azure, los tres `success`.
- [x] Revalidación tras actualizar el token: Azure Function `Running`,
  HTTPS-only y health 200; la consulta de VNets devolvió lista vacía.
- [x] Preflight VPN repetido: AWS Academy deniega explícitamente
  `ec2:CreateCustomerGateway` por SCP; dry-run sin creación. No se instaló la
  extensión Azure solicitada por la CLI ni se generaron cargos.

## Pendiente, sin marcar como completado

- [ ] Importar un CSV desde el navegador y verificar previsualización y
  persistencia en el portal desplegado. Parser, plantilla y límites están
  cubiertos por pruebas automatizadas, pero eso no es una prueba UI.
- [ ] Recorrido visual autenticado de Admin, Comercial y Operaciones. Se observó
  el acceso público; no se enviaron contraseñas al ALB HTTP porque las
  credenciales viajarían sin cifrado.
- [ ] Carga transaccional de ventas a través del ALB/RDS y análisis de capacidad
  para 3,000 usuarios. Las sondas de `/health` y las lecturas loopback no prueban
  esa capacidad.
- [ ] Entrega extremo a extremo de alertas Azure. La telemetría de invocaciones
  confirma actividad, no notificación.
- [ ] State remoto y privado de Terraform Azure. Los state y respaldos actuales
  están en la máquina local e ignorados por Git; conservarlos y migrarlos con un
  procedimiento revisado antes de reconstruir desde otro entorno.
- [ ] Conectividad privada AWS–Azure: no desplegada ni verificada; un intento
  Site-to-Site previo fue rechazado por SCP. El E2E usa HTTPS público.
- [ ] WebRTC de audio/video bidireccional con dos navegadores reales.
- [ ] Dominio y HTTPS confiable del portal, al final del cierre acordado.
- [ ] Capturas visuales crudas actuales para inventario AWS y monitor Azure; la
  evidencia de este corte es salida estructurada/registro, no captura de
  consola.
- [ ] Cualquier cambio posterior en el branch debe volver a pasar CI antes de
  considerarse validado.

## Límites del prototipo

El saldo WMS es un ledger sintético, no inventario físico. Finanzas no es
contabilidad legal; el buzón interno no es un servicio de correo corporativo ni
SMTP público. La expansión internacional y 3,000 usuarios concurrentes son
objetivos de arquitectura, no capacidad ya demostrada. La rúbrica y su
discrepancia de puntaje siguen en
[`../../core/04_matriz_rubrica.md`](../../core/04_matriz_rubrica.md).
