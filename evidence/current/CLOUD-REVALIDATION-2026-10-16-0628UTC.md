# Diagnóstico de lanzamiento EC2 — 16/10/2026, 06:24–06:28 UTC

**Nota de vigencia (06:54 UTC):** este corte describe el incidente de las 06:07
y el parche local que estaba preparado entonces. El parámetro de excepción
`EncryptRootVolume` fue retirado después; la plantilla conserva cifrado
obligatorio. Sin cambios en template/stack, AWS volvió a lanzar instancias con
EBS cifrado a las 06:39, el portal regresó a health 200 y el drift fresco fue
`IN_SYNC`. La situación operativa actual está en
[CLOUD-REVALIDATION-2026-10-16-0654UTC.md](CLOUD-REVALIDATION-2026-10-16-0654UTC.md).

## Causa raíz confirmada

- CloudTrail registra dos llamadas `kms:Decrypt` denegadas a las 06:07:23 y
  06:07:25 UTC. Los principales eran las instancias de infraestructura EC2 que
  intentaba levantar el ASG; el error identifica una **denegación explícita de
  la SCP de AWS Academy** (`p-hmulyz9e`).
- En el mismo intervalo, Auto Scaling pidió dos instancias `t3.micro` usando
  `lt-06f3e96760bec0cc5`, versión 18. Las dos llegaron a `pending`, fueron
  terminadas con `Client.InternalError` y dejaron el ASG con cero instancias y
  el target group vacío.
- La plantilla aplicada fuerza `Encrypted: true` en el volumen raíz. El AMI
  AL2023 es oficial de AWS y su snapshot base está sin cifrar; la cuenta tiene
  cifrado EBS por defecto desactivado y la plantilla solicita cifrar el volumen
  raíz con `alias/aws/ebs`. Ese flujo requiere la operación KMS que la SCP
  deniega. La cuota de instancias reportada por atributos de cuenta es 20; no
  apunta a un límite de capacidad. No se pudo consultar Service Quotas ni leer
  la SCP con la identidad del laboratorio.
- La secuencia explica el `Client.InternalError` y el 503 por target group sin
  destinos. El último health público observado (06:22 UTC) fue 503. No se
  modificó ningún recurso AWS.

## Compatibilidad preparada localmente

La plantilla ahora expone `EncryptRootVolume`, con `true` como valor seguro por
defecto. Los scripts `deploy.sh` y `rebuild.sh` propagan un override explícito;
la reconstrucción avisa si se solicita disco raíz sin cifrar. Esto permite
conservar cifrado por defecto en entornos normales y, solo si se aprueba, usar
una excepción de laboratorio. RDS y S3 permanecen cifrados. La policy SCP no
puede ser anulada desde el rol del estudiante.

La puerta local después de este cambio terminó aprobada: 218 pruebas unitarias,
14 pruebas Node, 40 transacciones aisladas, build y auditorías sin
vulnerabilidades conocidas; `cfn-lint`, `validate-template`, formato y
validaciones/tests Terraform también pasaron. No aplicó cambios cloud. El nuevo
control del disco raíz tiene pruebas automatizadas específicas.

**No se aplicó el override ni se ejecutó un change set.** Está pendiente la
decisión del usuario entre el override temporal para el lab y esperar al
administrador de AWS Academy para permitir KMS. No presentar el portal como
disponible hasta ver dos instancias `InService`, dos destinos `healthy`, health
200 y login/roles comprobados por el FQDN HTTPS.
