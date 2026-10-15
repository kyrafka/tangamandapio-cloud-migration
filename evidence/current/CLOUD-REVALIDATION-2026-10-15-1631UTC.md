# Revalidación AWS, Azure y Chrome — 15/10/2026, 16:31 UTC

Corte de solo lectura sobre el despliegue actual. La prueba visual se hizo
exclusivamente en la pestaña ya abierta de Chrome; no se usó localhost ni se
controlaron otras ventanas.

## AWS

- STS autenticó el perfil default en la cuenta académica 841113066612.
- CloudFormation tangamandapio-live-20261013: UPDATE_COMPLETE; el estado
  informado es IN_SYNC. La detección explícita más reciente terminó a las
  16:12 UTC.
- ASG tangamandapio-asg: mínimo/deseado/máximo 2/2/5; ambas EC2
  InService/Healthy y los dos targets del ALB healthy.
- ALB activo; HTTP/80 redirige a HTTPS y HTTPS/443 reenvía al target group.
  ACM para tangamandapio.kendellnm.me figura ISSUED, en uso y vigente hasta
  2027-04-30.
- RDS tangamandapio-postgres: available, cifrada, privada, Single-AZ y
  retención de backup de un día. No se cambió la base.
- CloudWatch: siete alarmas con acciones habilitadas; seis OK y la alarma de
  scale-in de Target Tracking en ALARM, con el ASG ya en su mínimo de dos.

## Azure

- Suscripción Azure for Students: Enabled.
- Function tangama-wms-261008: Running y HTTPS-only.
- GET /api/health del host de la Function respondió HTTP 200:
  status=ok, service=tangamandapio-wms.
- La última consulta de Application Insights (16:12 UTC) encontró 141
  solicitudes en seis horas y cero fallidas; incluye llamadas de health,
  eventos de fulfillment y consulta de poison queue. No se generó un evento
  nuevo en esta revalidación.
- El plan Terraform Azure incluyó el archivo local protegido de destinatarios
  de alertas y terminó sin cambios a las 16:12 UTC; no se ejecutó apply.

## Interfaz en Chrome

- La portada pública y el panel de login cargan en
  https://tangamandapio.kendellnm.me/. Se probó el cambio claro/oscuro y se
  restauró oscuro; el panel de acceso se cerró y reabrió.
- En la misma pestaña, /health mostró status=ok con marca de tiempo
  2026-10-15T16:30:07.651372+00:00. Después se volvió a la portada, con el
  panel de login abierto y el ambiente sonoro restaurado al estado inicial.
- No se introdujeron credenciales. No se recorrieron visualmente módulos
  privados ni roles; requieren sesión iniciada por el usuario.

## Rendimiento y límites observados

- 100 sondas /health desde una EC2 hacia loopback (concurrencia 10): 100/100
  exitosas, 1.335 s de duración, p95 139.09 ms y máximo 143.6 ms. Evidencia:
  [resultado JSON](aws/AWS-PERF-EC2-LOOPBACK-2026-10-15-1618.json).
- La carga Python desde un cliente externo contra el dominio público recibió
  403 de Cloudflare en 100/100 solicitudes automatizadas. Chrome sí carga la
  portada y /health; por ello no se relajó la protección ni se interpreta el
  403 del cliente sintético como caída del portal. Se necesita un plan de
  carga aprobado que respete Cloudflare para medir el ALB.
- La prueba E2E autenticada por el hostname directo del ALB siguió la
  redirección HTTPS y falló la validación de certificado porque el certificado
  solo cubre el dominio público. No escribió pedidos. La E2E de loopback en
  EC2 pasó previamente; la ruta autenticada desde el navegador con el dominio
  correcto aún requiere sesión manual.
- No se demuestra capacidad para 3,000 usuarios, recuperación Multi-AZ,
  VPN privada AWS–Azure ni WebRTC audiovisual entre dos navegadores.

No se modificaron recursos cloud durante esta revalidación.
