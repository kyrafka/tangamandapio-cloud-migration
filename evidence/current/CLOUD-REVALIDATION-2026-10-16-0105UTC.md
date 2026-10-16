# Revalidación post-v18 — 16/10/2026, 01:05 UTC

## Resultado ejecutivo

El dominio publica HTTPS: la negociación TLS termina correctamente y HTTP
redirige a HTTPS con `301`. Sin embargo, la aplicación no está disponible:
portada, `/health`, `/ready` y `/platform` devuelven `503` por HTTPS en la
comprobación del 16/10 a las 01:02 UTC. El entorno no se considera operativo
hasta recuperar la salud del origen.

## AWS

- `aws sts get-caller-identity` autenticó en la cuenta Academy `841113066612`.
- `cloudformation:DescribeStacks` fue denegado explícitamente por la política
  `voc-cancel-cred`. Por tanto, esta sesión no permite confirmar el estado actual
  de los destinos del ALB, el ASG, RDS ni el drift. No se intentó eludir la
  política.
- El release v18 había completado `UPDATE_COMPLETE` a las 00:42:53 UTC. En la
  primera comprobación posterior el balanceador aún respondió; después el
  origen ALB devolvió 503. No hay evidencia suficiente para atribuir la causa
  sin consultar el target group y los registros de instancia.
- No se modificó infraestructura durante esta revalidación.

## Azure y flujo sintético

La Function `tangama-wms-261008` figura `Running`, `httpsOnly=true`, en West US;
`/api/health` devolvió 200. El E2E sintético más reciente ejecutó la aplicación
de release local con SQLite temporal hacia la Function Azure: la solicitud sin
clave devolvió 401 y el productor no autorizado 400, sin persistir esos probes.
Una venta fue aceptada por Queue/Function como
`demo_fulfillment_completed`; una recepción compensatoria terminó como
`demo_restock_completed`; el ledger ficticio regresó exactamente al saldo de
partida. El conteo de poison queue fue cero antes y después; solo se consultó
metadato y no se leyó ni borró ningún mensaje. Los dos eventos válidos quedan
en la auditoría Blob de Azure.

Este E2E acredita Azure y el ledger sintético, no el origen AWS/RDS ni una ruta
privada entre nubes. El WMS es funcional para la simulación académica; no mueve
existencias físicas.

## Pruebas locales

La puerta local más reciente aprobó 209 pruebas, frontend/build, CloudFormation,
Terraform (formato y validación de las raíces configuradas), mocks de red y
auditoría de dependencias. Son pruebas locales; no rehabilitan la disponibilidad
AWS ni sustituyen el smoke autenticado post-v18.

## Pendientes de cierre

1. Recuperar permiso legítimo de lectura del plano de control AWS; consultar
   salud de targets, ASG, eventos/logs y estado de RDS. Resolver la causa del 503
   antes de otro cambio de aplicación o infraestructura.
2. Cuando el portal esté sano, repetir contra v18 el login, permisos de Admin,
   Comercial y Operaciones, venta/compra, outbox paginado (45 eventos en 30+15)
   y reconciliación con Azure; verificar que cada escritura sintética vuelve a
   su línea base.
3. Revalidar drift de CloudFormation y plan Terraform sin aplicar cambios a
   ciegas. RDS sigue documentado como Single-AZ con retención de backup de un
   día; el restore aislado previo sí produjo RTO/RPO observados, pero no se ha
   demostrado failover Multi-AZ.
4. La red privada AWS–Azure sigue pendiente. La integración HTTPS pública no
   la sustituye; AWS Academy ya denegó la creación de la VPN en un preflight.
5. Ejecutar carga representativa y observar autoscaling (la prueba de 24
   lecturas/concurrencia 6 no demuestra el objetivo de 3,000 usuarios), y
   guardar evidencia actual de monitor/invocaciones/alarma.
6. Pruebas de navegador autenticado del importador CSV y módulos, WebRTC con dos
   navegadores y grabación consentida siguen sin verificación reciente.
7. El buzón interno `portal_only` no entrega por SMTP externo. El relay solo se
   prueba localmente; debe desplegarse/configurarse si el alcance exige correo
   saliente real.
8. Completar evidencia de Cost Analysis Azure/AWS, capturas de consola y
   sincronizar este corte en la entrega/GitHub. Preparar la demostración oral.

La matriz cualitativa se mantiene en
[`core/04_matriz_rubrica.md`](../../core/04_matriz_rubrica.md); este informe no
asigna una nota numérica.
