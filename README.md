# Tangamandapio S.A.C. — centro de operaciones cloud

Proyecto académico de arquitectura para una distribuidora peruana ficticia. El caso base contempla 450 colaboradores, 220 cuentas internas, centros en Lima, Arequipa y Trujillo y hasta 3,000 usuarios externos concurrentes durante campañas. La expansión internacional es una meta de diseño, no una capacidad ya desplegada o medida.

## La idea principal

Portal B2B y ERP son dominios funcionales distintos: el portal sirve a distribuidores/clientes y el ERP a los equipos internos. Para este prototipo se presentan juntos en la misma web y usan el inicio de sesión y los permisos existentes; sus tablas y APIs están separadas por módulo. Si la escala operativa lo exige, el ERP puede extraerse después como servicio independiente. Azure conserva la autoridad del inventario WMS; el ERP envía ventas y recepciones, pero no mantiene otra copia de existencias. La mensajería ERP persiste dentro del portal y ahora admite un relay SMTP configurable; en local, Compose usa Mailpit como receptor de prueba, no como correo público ni buzones corporativos.

El catálogo trae 12 SKU sintéticos y se amplía desde ERP → Maestros con la plantilla Excel (editar y guardar como CSV UTF-8 antes de importar). La carga admite hasta 500 productos, valida el archivo completo y sincroniza el catálogo con el ledger de Azure. El saldo inicial solo se aplica a SKU nuevos; actualizar fichas conserva existencias. Las ventas y recepciones modifican saldos sintéticos de forma idempotente; no representan inventario físico. El release v11 está desplegado en AWS y verificado en dos instancias. Detalles funcionales y pruebas: [importación de catálogo sintético](evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md) y [evidencia de v11](evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

El proyecto hermano se usa como referencia del problema del datacenter corporativo centralizado, no como fuente de las cifras de Tangamandapio. La arquitectura objetivo, responsabilidades, candidatos ERP/correo y fases están en [core/12_arquitectura_empresarial_portal_erp_correo.md](core/12_arquitectura_empresarial_portal_erp_correo.md).

## Estado del proyecto

**Corte vigente: 15/10/2026, 00:34 UTC.** El perfil AWS `default` autentica por STS en la cuenta académica `841113066612`. CloudFormation `tangamandapio-live-20261013` está en `UPDATE_COMPLETE`; drift terminó `IN_SYNC`. El release `20261014-landing-loading-v11-python312` está activo en las dos instancias `InService`: SSM confirmó en ambas la revisión, el servicio activo y `/health` local HTTP 200. El target group tiene exactamente dos destinos `healthy`; el ASG quedó mínimo/deseado 2, máximo 5, sin nodos terminando. El ALB devolvió HTTP 200 para `/`, `/health` y `/ready`; `/api/admin/users` anónimo devolvió 401. La VPC separa ALB público, aplicación privada y RDS aislada, con reglas ALB:80→app:8080→DB:5432. RDS está `available`, cifrada, privada, 20 GB, Single-AZ y con retención de backups de un día. Las cinco alarmas CloudWatch consultadas están `OK` y con acciones habilitadas. La prueba E2E AWS→Azure sobre v11 pasó; [el corte completo](evidence/current/CLOUD-REVALIDATION-2026-10-15.md) registra resultados y límites.

El artefacto v11 fue publicado en el bucket privado versionado con cifrado SSE-S3, y la actualización se aplicó con la política CloudFormation `AutoScalingRollingUpdate` de lote uno y dos instancias mínimas en servicio. El primer método de refresh fue denegado por la SCP del laboratorio; se revirtió y sustituyó por el mecanismo gradual permitido, que completó correctamente. No se modificaron RDS ni la red.

Azure no se modificó durante esta continuación. A las 00:17 UTC, Function `tangama-wms-261008` respondió `/api/health` HTTP 200; Terraform no se aplicó. El WMS/ledger mantiene datos sintéticos y no representa inventario físico. La prueba v11 envió venta y recepción sintéticas y verificó ambos eventos entregados por la integración.

La prueba E2E autenticada se repitió sobre v11: Admin, Comercial y Operaciones; venta/recepción sintéticas; dos eventos outbox entregados por Azure; stock demo 10→10. El ledger no es un WMS comercial. PT-DR-01 probó restauración RDS el 13/10, con RTO 289 s y RPO observado 14 s. Siguen pendientes dominio/HTTPS, conectividad privada AWS–Azure, revisión visual manual de todos los roles, WebRTC real entre dos navegadores y carga transaccional por ALB/RDS a capacidad objetivo. El alcance y las limitaciones están en la [matriz de rúbrica](core/04_matriz_rubrica.md), [checklist de cierre](evidence/current/CHECKLIST-CIERRE-2026-10-14.md) y [preflight VPN](evidence/current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

La puerta local más reciente terminó aprobada: **165 pruebas Python, 14 Node, 40 transacciones aisladas**, auditoría de dependencias sin vulnerabilidades conocidas, build Vite, `cfn-lint` y Terraform `fmt`/`validate`/tests; no hizo `apply` ni escrituras cloud. Las pruebas aisladas no miden capacidad para 3,000 usuarios. Repetición: `.\tests\run_local_quality.ps1 -ValidateTerraform`; [QA local del 15/10](evidence/current/QA-LOCAL-2026-10-15.md).

## Estructura

- `core/`: caso, arquitectura empresarial, propuesta cloud, rúbrica y hoja de ruta.
- `app/`: portal B2B, API, Function Azure de demostración y pruebas.
- `iac/`: CloudFormation de AWS y Terraform de Azure; revisar estado antes de aplicar.
- `orchestration/`: puertas y secuencia controlada de reconstrucción.
- `evidence/current/`: evidencia y mapas fechados, con límites de cada afirmación.
- `deliverables/`: documentos académicos existentes; no asumir que un Entregable 1 es el informe final.

La compuerta integral actual pasó 163 pruebas Python y 14 Node (roles/CSV),
40 transacciones aisladas, build Vite, auditoría de dependencias, CloudFormation,
Terraform y mocks; no hizo escrituras cloud. El restore SQL RDS y el E2E
AWS→Azure están probados previamente; este corte actualizó los estados, hashes,
telemetría, cola poison y la prueba de lectura por ALB. Pendientes completos en
el [checklist de cierre](evidence/current/CHECKLIST-CIERRE-2026-10-14.md);
también consulta [QA local](evidence/current/QA-LOCAL-2026-10-14.md),
[estado cloud](evidence/current/CLOUD-REVALIDATION-2026-10-14.md) y
[catálogo](evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md). Para
repetir la compuerta completa en Windows:

```powershell
.\tests\run_local_quality.ps1 -ValidateTerraform
```

El state de Terraform Azure no se versiona y permanece en esta copia local: antes de operar desde otra máquina, configurar un backend remoto privado o recuperar ese state con seguridad. Las cuentas y la mensajería local no son directorio ni correo corporativo de producción. La pila AWS no tiene SMTP productivo configurado en este corte.
