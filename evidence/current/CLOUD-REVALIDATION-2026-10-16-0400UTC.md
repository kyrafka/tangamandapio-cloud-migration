# Revalidación viva AWS–Azure y diagnóstico de sonda — 16/10/2026, 04:00 UTC

## Comprobaciones de solo lectura

- AWS STS aceptó el perfil local `default` para la cuenta Academy `841113066612`.
- CloudFormation `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; el
  último drift registrado sigue `IN_SYNC` (03:31 UTC).
- `https://tangamandapio.kendellnm.me/health` devolvió HTTP 200. ACM está
  `ISSUED` hasta 30/04/2027; el ALB está activo, 443 reenvía a la aplicación y
  80 redirige a HTTPS.
- ASG `tangamandapio-asg`: deseado/mínimo 2, máximo 5; ambas EC2 están
  `InService/Healthy` y ambos targets están `healthy`.
- Azure WMS `https://tangama-wms-261008.azurewebsites.net/api/health` respondió
  HTTP 200 con TLS validado.
- RDS `tangamandapio-postgres` sigue `available`, cifrada, privada, Single-AZ y
  con backup retention de un día.
- No hay Web ACL regional en AWS. La alarma target-tracking de escala-baja está
  `ALARM` por CPU alrededor de 1% bajo 42%; el ASG no baja de dos instancias.
  Las alarmas de servicio consultadas permanecen `OK` y con acciones habilitadas.
- La detección previa de drift y el smoke Admin/Comercial/Operaciones se
  conservan en [la revalidación de 03:41 UTC](CLOUD-REVALIDATION-2026-10-16-0341UTC.md).

## Diagnóstico PT-PERF-01

- Una ejecución de 25 GET a `/health` con Python `urllib`, concurrencia 5,
  terminó 25/25 HTTP 403 (`HTTPError`), p95 799.18 ms. Una reproducción de 3
  GET con concurrencia 1 mostró 3/3 HTTP 403. En una petición se observó
  `Server: cloudflare`; esto indica una respuesta del proxy para ese cliente,
  no un 403 originado en Flask.
- `curl.exe` e `Invoke-WebRequest` al mismo dominio/ruta devolvieron HTTP 200.
  No se identificó la regla Cloudflare que discrimina las solicitudes y no se
  cambió ni sorteó su configuración. Las latencias de respuestas 403 no son una
  medida de capacidad del origen.
- `tests/performance/load_test.py` se mejoró para reportar `status_counts` y
  `error_types` sin almacenar cuerpos de respuesta. Sus dos pruebas nuevas
  pasaron y la compuerta local completa aprobó 215 pruebas unitarias, 14 pruebas
  Node, build/auditorías, `cfn-lint`, validación Terraform y cinco pruebas mock;
  no ejecutó operaciones cloud.

## Infrastructure as Code

- Los parámetros efectivos del stack son el artefacto v18, y el template local
  `iac/cloudformation/aws-lab.yaml` tiene defaults v18.
- El template guardado en AWS conserva defaults de artefacto v16 para key,
  revision y SHA-256. La comparación de 1,251 líneas encontró solo esos tres
  valores y diferencias de codificación en texto descriptivo; no encontró
  diferencias de bloques de recursos. No se intentó una actualización vacía ni
  se modificó infraestructura.

## Publicación

- El commit anterior `da00449d0af0bca79463e17a03a03a3eb56c5487` está publicado y
  su workflow terminó `success`. Este corte y la mejora de diagnóstico local
  quedan listos para publicar y confirmar en GitHub Actions.
- No se escribieron pedidos, compras, eventos, inventario ni recursos cloud en
  esta pasada.
