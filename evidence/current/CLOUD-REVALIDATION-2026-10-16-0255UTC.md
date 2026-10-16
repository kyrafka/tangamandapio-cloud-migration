# Revalidación final de esta pasada — 16/10/2026, 02:55 UTC

## AWS en vivo

- AWS Academy STS aceptó el token temporal compartido por el usuario para la
  cuenta `841113066612` (rol `voclabs`). Se actualizó el perfil local `default`
  del AWS CLI y se comprobó la identidad desde ese perfil. El secreto no se
  copió al repositorio ni a esta evidencia.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE` (última
  actualización reportada: 16/10/2026 00:27:59 UTC). ApplicationURL:
  `https://tangamandapio.kendellnm.me`.
- ALB `active`, internet-facing; listener 443 HTTPS con certificado ACM
  `ISSUED` para el FQDN. Listener 80 devuelve redirección a HTTPS 443.
- ASG `tangamandapio-asg`: mínimo/deseado 2, máximo 5; ambas instancias
  `InService`. Los dos destinos del target group están `healthy` en puerto 8080.
- Comprobaciones externas: `/`, `/health` y `/ready` por HTTPS respondieron
  200; `http://…/` redirigió con 301 al FQDN HTTPS.
- RDS `tangamandapio-postgres`: `available`, PostgreSQL 18.3, `db.t3.micro`,
  privada, cifrada, Single-AZ y retención automática de un día. La instancia no
  es Multi-AZ. La restauración aislada PT-DR-01 ya aprobó el 15/10 (RTO 260 s;
  límite superior RPO 8 s); no se repitió para evitar costo y residuos.

No se modificó infraestructura durante esta revalidación. El único cambio
persistente fuera del repositorio fue la actualización autorizada del perfil
local AWS CLI `default`; no se imprimió el token en las salidas.

## Azure y recorrido funcional

- `Azure for Students` continúa `Enabled`; `tangama-wms-261008` responde 200 en
  `/api/health`. La última consulta de Application Insights está documentada
  en [el corte de módulos y telemetría de 02:40](CLOUD-REVALIDATION-2026-10-16-0240UTC.md).
- El E2E AWS→Azure, importación sintética, permisos API, ledger ficticio,
  módulos Admin/Finanzas, buzón interno y cola poison pasaron en la prueba
  documentada de 02:31–02:40 UTC. No equivale a inventario físico, correo
  externo ni contabilidad legal.

## Puerta local reproducible

`tests/run_local_quality.ps1 -ValidateTerraform` terminó `QUALITY_GATE=APROBADA`
sin operaciones cloud. Pasaron 209 pruebas unitarias; frontend Vite build,
auditorías locales de dependencias, `cfn-lint`/validación CloudFormation,
Terraform `fmt`/`init`/`validate`, pruebas de navegación y CSV, guardas de costo,
seguridad y red simuladas. Los cinco tests mock de Terraform pasaron. La suite
no aplica IaC ni sustituye una prueba de navegador/producción.

## Brechas vigentes

- El login automatizado a través del proxy Cloudflare devolvió 403; el smoke
  autenticado directo al ALB con TLS válido pasó. Aún falta el ingreso visual
  desde Chrome por el FQDN y revisar el evento/rule de Cloudflare.
- No hay Web ACL AWS. La microcarga funcional 24/24 (concurrencia 6, p95
  399.77 ms) no demuestra 3,000 usuarios ni el autoscaling bajo carga.
- La VPN/red privada está bloqueada por una SCP explícita de AWS Academy al
  intentar `CreateCustomerGateway`; la suscripción Azure activa no tiene VNet.
  La integración actual AWS→Azure usa HTTPS público; no se eludió la SCP.
- RDS sigue Single-AZ y con backup de un día; PT-DR-01 no prueba failover ni
  SLA. La causa del 503 histórico no se atribuyó.
- WebRTC entre dos navegadores, recorrido visual de CSV y capturas recientes de
  consolas/monitor aún no están verificados. SMTP externo tampoco está
  configurado: el correo comprobado es interno al portal.

El estado por criterio y los límites de la autoevaluación están en la
[matriz de evidencia](../../core/04_matriz_rubrica.md). La rúbrica local pesa
18.5 aunque su encabezado dice 20; no se inventó una conversión oficial.
