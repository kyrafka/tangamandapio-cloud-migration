# Revalidación de EC2 y balanceador — 14/10/2026, 03:12 America/Chicago

> **Evidencia histórica anterior al intento v11.** Las sondas HTTP 200 y los
> cortes descritos abajo son de la madrugada del 14/10; no acreditan que la
> aplicación siga sana después de la actualización posterior. La comprobación
> más reciente está en
> [AWS-DESPLIEGUE-V11](AWS-DESPLIEGUE-V11-2026-10-14.md).

## Confirmación tras candidato v6 — 03:40 America/Chicago

STS todavía autentica, pero Auto Scaling `DescribeAutoScalingGroups` continúa
denegado por el `explicit deny` `voc-cancel-cred`. GET anónimos al ALB
confirmaron que `/api` y `/health` aún incluyen `instance`; la evidencia no
retiene el hostname. `/api/admin/users` devuelve `401` y `/metrics` devuelve
`200` sin sesión (no se leyó el cuerpo). El hardening v6
preparado localmente todavía no está publicado y no se modificó AWS.

## Seguimiento HTTP — 03:25 America/Chicago

Una nueva pasada GET desde el equipo local encontró el ALB respondiendo HTTP
`200` en `/`, `/health` y `/ready`; `/api/admin/users` anónimo devuelve `401`.
Cinco solicitudes consecutivas a `/health`, con dos segundos entre ellas,
respondieron `200` (5/5).
En una segunda serie, diez solicitudes a `/health` dieron 10/10 y dos valores
distintos en `instance`; la aplicación confirma que al menos dos backends
respondieron. La API de control sigue denegada, por lo que no se infiere el
conteo total ni el estado formal `Healthy` del target group.
El cuerpo público expone esos nombres DNS privados desde `/api` y `/health`.
Se corrigió en el candidato local v6, pero no está desplegado; el release vivo
sigue exponiendo ese dato.
Por ello, el `503` que se veía a las 03:12 y el fallo `502` posterior no son el
estado HTTP actual. Sin embargo, el rol `voclabs` sigue sin permitir leer
`autoscaling:DescribeAutoScalingGroups` ni
`elasticloadbalancing:DescribeLoadBalancers` por un `explicit deny` de
`voc-cancel-cred`, así que no puedo afirmar desde este corte que haya dos
targets sanos o identificar qué cambió. No se hicieron cambios en AWS.

## Estado observado

- La consola AWS Academy quedó con el laboratorio `Ready` después de iniciarlo;
  el presupuesto de Vocareum mostraba USD 24.10 usados de USD 50 en la captura
  de inicio. La consola de facturación AWS mostraba USD 19.36 del mes y un
  pronóstico de USD 24.02. Son medidores distintos, no deben sumarse ni
  confundirse.
- El stack `tangamandapio-live-20261013` se había visto
  `UPDATE_COMPLETE` y `IN_SYNC`; eso describe la plantilla aplicada al stack,
  no la salud de la aplicación.
- El ALB `tangamandapio-alb` figura `Active`, internet-facing. El target group
  `tangamandapio-tg` está asociado, pero la consola muestra **0 destinos
  registrados**.
- El ASG `tangamandapio-asg` tiene deseada 2, mínimo 2 y máximo 4. A las 03:12
  el estado seguía `Actualización de capacidad` y su vista de instancias marcaba
  **0**. Las lecturas HTTP del ALB devolvieron `503` en `/`, `/health` y
  `/ready`.
- El historial de Auto Scaling supera 100 eventos. Los intentos recientes
  terminan con `Instance became unhealthy while waiting for instance to be in
  InService state` y `Client.InternalError: Client error on launch`; uno de los
  pares más recientes comenzó a las 02:50:16 y terminó a las 02:50:20. Esto no
  demuestra que el código de arranque haya alcanzado a ejecutarse y **no
  identifica por sí solo la causa raíz**.
- El ASG usa `tangamandapio-app`, versión 5 de una plantilla con cinco
  versiones; la versión predeterminada es 1. La versión 5 muestra Amazon Linux
  2023, `t3.micro`, `LabInstanceProfile`, el grupo de seguridad de aplicación y
  las dos subredes privadas (AZ `us-east-1a` y `us-east-1b`). El user data
  instala Python 3.12, descarga el artefacto privado verificado y configura el
  servicio. No se editó la plantilla.
- AWS STS autenticó como sesión `voclabs`, pero la CLI devolvió una denegación
  explícita al consultar `ec2:DescribeLaunchTemplateVersions`. La consola de
  CloudTrail también mostró `AccessDeniedException`; por eso no fue posible
  consultar el evento API que podría explicar el `Client.InternalError`.
- Azure usa la suscripción habilitada `Azure for Students`. El grupo actual es
  `rg-tangamandapio-rebuild-wus` (no el antiguo nombre `rg-tangamandapio-261005-wus`);
  allí aparece la Function `tangama-wms-261008`. Su endpoint público HTTPS
  `/api/health` respondió `200` con `status=ok` y `service=tangamandapio-wms`.
- La interfaz local `http://127.0.0.1:8080/` abrió en Chrome y mostró el inicio
  de sesión, los controles de usuario/contraseña y el aviso de que no hay
  registro público. No se ingresaron credenciales; esto verifica la pantalla
  pública, no las vistas autenticadas.
- En un smoke local a las 03:17, `/`, `/health` y `/ready` respondieron `200`;
  `/api/admin/users` sin sesión respondió `401`, como corresponde. No se
  consultó información administrativa autenticada.

## Cambios realizados

No se aplicó IaC, no se modificaron recursos ni se reiniciaron instancias. Las
operaciones cloud de esta revalidación fueron de lectura; el único cambio de
estado de esta sesión fue iniciar el laboratorio AWS Academy para disponer de
la sesión de consola solicitada.

## Conclusión del corte de las 03:12 (superada por el seguimiento HTTP)

En el corte de las 03:12, el portal AWS no estaba disponible: el balanceador no
tenía destinos y respondía `503`, aunque el stack CloudFormation existiera.
Ese estado HTTP fue reemplazado por el seguimiento de las 03:25, cuando las
sondas públicas respondieron `200`. Los intentos EC2 y la auditoría detallada
descritos arriba no bastan para atribuir la recuperación a una causa específica.

Para cerrar la verificación de AWS hay que obtener permiso/visibilidad para
leer el ASG y el target group y confirmar los destinos saludables. Si vuelve a
fallar, obtener el motivo del rechazo desde
un evento EC2/CloudTrail o el detalle del servicio Auto Scaling, verificar la
política del laboratorio y la cuota/tipo de instancia permitidos, corregir solo
la causa confirmada y esperar dos destinos `Healthy`. Después se deben repetir
`/`, `/health`, `/ready`, inicio de sesión y la barrera de administración. No
debe desplegarse una segunda pila ni tocar RDS para intentar resolver este 503.
