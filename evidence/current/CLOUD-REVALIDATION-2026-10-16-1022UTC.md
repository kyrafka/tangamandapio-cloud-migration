# Revalidación y avance de WebRTC — 16/10/2026, 10:22 UTC

## Credenciales AWS

- El perfil local `default` se actualizó con las credenciales entregadas en el
  chat. `sts:GetCallerIdentity` las aceptó para la cuenta de laboratorio
  `841113066612`.
- Las lecturas de CloudFormation y Systems Manager fueron denegadas por una
  política explícita `voc-cancel-cred` (`cloudformation:ListStacks` y
  `ssm:DescribeInstanceInformation`). No se consultó ni modificó ningún recurso,
  y no se intentó un despliegue.
- Las credenciales temporales no se copiaron a este repositorio ni a la
  documentación.

## Validación local

- `tests/run_local_quality.ps1`: `QUALITY_GATE=APROBADA`; 230 pruebas unitarias,
  40 transacciones aisladas, build de frontend, auditorías de dependencias,
  validación de CloudFormation y demás validaciones locales.
- Suite de release AWS actual: 20/20.
- Adaptador de configuración ICE: 5/5 pruebas Node.
- `git diff --check`: sin errores.

## WebRTC

- Se añadió un adaptador de frontend que consulta la ruta autenticada
  `/api/voice/ice-config` y establece servidores ICE antes de la negociación.
  Acepta solo esquemas STUN/TURN y mantiene STUN como fallback con timeout;
  las credenciales de vida corta no se imprimen ni persisten.
- El endpoint backend ya admite emitir credenciales TURN temporales firmadas
  con `WEBRTC_TURN_SHARED_SECRET` cuando también se proporcionan URL(s) TURN.
- Esta integración todavía no está desplegada: la sesión no permite leer la
  pila ni Systems Manager debido al `explicit deny`. La configuración del
  proyecto tampoco declara un relay TURN. No hay evidencia nueva de llamada
  bidireccional real; este cambio por sí solo no elimina restricciones NAT.

## Estado de la nube

Los estados del corte anterior de 10:06–10:15 UTC no se deben extrapolar a esta
sesión, porque ahora las consultas de recursos AWS están explícitamente
denegadas. Azure no se revalidó en este corte. Sin acceso de lectura no se puede
afirmar que los recursos sigan activos ni que esta nueva release esté desplegada.
