# Tangamandapio S.A.C. — centro de operaciones cloud

Proyecto académico de arquitectura para una distribuidora peruana ficticia. El caso base contempla 450 colaboradores, 220 cuentas internas, centros en Lima, Arequipa y Trujillo y hasta 3,000 usuarios externos concurrentes durante campañas. La expansión internacional es una meta de diseño, no una capacidad ya desplegada o medida.

## La idea principal

Portal B2B y ERP son dominios funcionales distintos: el portal sirve a distribuidores/clientes y el ERP a los equipos internos. Para este prototipo se presentan juntos en la misma web y usan el inicio de sesión y los permisos existentes; sus tablas y APIs están separadas por módulo. Si la escala operativa lo exige, el ERP puede extraerse después como servicio independiente. Azure conserva la autoridad del inventario WMS; el ERP envía ventas y recepciones, pero no mantiene otra copia de existencias. La mensajería ERP persiste dentro del portal y ahora admite un relay SMTP configurable; en local, Compose usa Mailpit como receptor de prueba, no como correo público ni buzones corporativos.

El catálogo parte de 12 SKU sintéticos y se amplía desde ERP → Maestros con la plantilla Excel (guardar como CSV UTF-8 antes de importar). La carga admite hasta 500 productos y sincroniza el catálogo con el ledger de Azure; las ventas y recepciones modifican saldos ficticios de forma idempotente, no representan inventario físico. En la comprobación viva del 16/10 a las 02:10 UTC, la consola AWS mostró 14 SKU (12 de catálogo y 2 de QA), 45 eventos de outbox y la consulta autenticada de un evento a Azure devolvió `demo_restock_completed`. Detalles en la [importación de catálogo sintético](evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md) y la [revalidación AWS](evidence/current/aws/AWS-REVALIDACION-LIVE-2026-10-16-0137UTC.md).

El proyecto hermano se usa como referencia del problema del datacenter corporativo centralizado, no como fuente de las cifras de Tangamandapio. La arquitectura objetivo, responsabilidades, candidatos ERP/correo y fases están en [core/12_arquitectura_empresarial_portal_erp_correo.md](core/12_arquitectura_empresarial_portal_erp_correo.md).

## Estado vigente

**Última revalidación: 16/10/2026, 02:10 UTC.** El portal HTTPS, `/health` y
`/ready` respondieron 200. CloudFormation informa `UPDATE_COMPLETE`; Auto Scaling
tiene 2/2 instancias `InService`/`Healthy` y ambos destinos del ALB están
saludables. La consola autenticada cargó métricas CloudWatch, catálogo, outbox
paginado y las tres cuentas; la consulta de un evento existente desde la consola
devolvió `demo_restock_completed` en Azure. El primer render mostró datos en
carga y la tabla de usuarios se completó al refrescar; queda anotado como
intermitencia visual, no como falla persistente.

RDS está `available`, Single-AZ, con retención de backup de un día. WAF no está
desplegado. El drift `IN_SYNC` observado antes fue para 39 recursos compatibles
de los 47 y no valida salud de aplicación. No se alteraron recursos cloud en
esta revalidación. Las credenciales temporales AWS se actualizaron solo en el
perfil local y no se copiaron a documentación.

**Azure:** `Azure for Students` está `Enabled`; la Function sigue `Running` y
HTTPS-only. El smoke vivo del 16/10 a la 01:47 ejecutó el paquete local hacia
Azure: los guards devolvieron 401/400, una venta sintética se procesó y su
compensación restauró el ledger demo. No acredita el recorrido desde EC2; los
eventos sintéticos permanecen en el almacenamiento de auditoría.

La puerta local pasó 209 pruebas unitarias, build Vite, auditorías frontend y
de dependencias, `cfn-lint`, validación AWS de CloudFormation y `fmt`/`init`/
`validate` más cinco pruebas mock de Terraform; no aplicó infraestructura.
GitHub Actions pasó el quality gate del commit `aab64cc` (run
[38839629336](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38839629336)).
Véanse la [evidencia AWS/Azure](evidence/current/aws/AWS-REVALIDACION-LIVE-2026-10-16-0137UTC.md),
el [estado de IaC](iac/README.md) y la [matriz cualitativa](core/04_matriz_rubrica.md).

### Corte histórico (02:58 UTC)

**Corte histórico: 15/10/2026, 02:58 UTC.** AWS `default` autenticó por STS en la cuenta académica `841113066612`; el ALB `tangamandapio-alb` estaba `active`, sus dos destinos `healthy` y `/health` respondió 200 bajo una microcarga de 120 solicitudes/8 concurrentes. Ese endpoint ejecutaba `SELECT 1`, por lo que probó disponibilidad de la ruta ALB→aplicación→RDS, no ventas. CloudFormation `tangamandapio-live-20261013` estaba `UPDATE_COMPLETE`; la detección de drift (02:36 UTC) terminó `IN_SYNC`, cero diferencias. El release `20261014-landing-loading-v11-python312` estaba activo en dos instancias `InService`. La VPC separaba ALB público, aplicación privada y RDS aislada; RDS estaba `available`, cifrada, privada, 20 GB, Single-AZ y con backup de un día. Las cinco alarmas CloudWatch estaban `OK` con acciones habilitadas. Azure for Students estaba `Enabled`; la Function `Running`, `httpsOnly=true` y `/api/health` respondió 200 en esa revalidación. El [checklist posterior](evidence/current/CHECKLIST-CIERRE-2026-10-15.md) prevalece sobre este corte histórico.

El artefacto v11 fue publicado en el bucket privado versionado con cifrado SSE-S3, y la actualización se aplicó con la política CloudFormation `AutoScalingRollingUpdate` de lote uno y dos instancias mínimas en servicio. El primer método de refresh fue denegado por la SCP del laboratorio; se revirtió y sustituyó por el mecanismo gradual permitido, que completó correctamente. No se modificaron RDS ni la red.

No se aplicó Terraform ni se modificó infraestructura Azure en este corte. Function `tangama-wms-261008` sigue `Running`, `httpsOnly=true` y `/api/health` respondió HTTPS 200 después del ejercicio de recuperación. Application Insights reportó en su consulta previa de 24 h 17 solicitudes y cero fallidas; el E2E vivo posterior volvió a confirmar procesamiento de eventos. Son datos agregados, no sustituyen una correlación por evento ni una captura del dashboard. El WMS/ledger contiene datos sintéticos y no representa inventario físico.

Los E2E autenticados desde AWS y las pruebas de restore RDS descritos en los
cortes anteriores son evidencia histórica, no se repitieron en esta
revalidación. El smoke de Azure de las 18:56 fue local→Azure y el inventario es
un ledger sintético. Siguen pendientes conexión privada AWS–Azure, recorridos
visuales autenticados de roles, CSV desde archivo en la UI, carga transaccional
por ALB, evidencia independiente de entrega de alertas Azure y WebRTC A/V entre
dos navegadores. Dominio y HTTPS sí están activos. Ver [matriz de rúbrica](core/04_matriz_rubrica.md),
[checklist de cierre](evidence/current/CHECKLIST-CIERRE-2026-10-15.md) y
[preflight VPN](evidence/current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

La puerta local más reciente terminó aprobada: **181 pruebas Python, 14 Node,
40 transacciones aisladas**, auditorías de dependencias sin vulnerabilidades
conocidas, build Vite, CloudFormation y Terraform `fmt`/seis `validate`/cinco
tests mock; no hizo `apply`. Las pruebas aisladas no miden capacidad para 3,000
usuarios. Repetición: `.\tests\run_local_quality.ps1 -ValidateTerraform`;
[QA local del 15/10](evidence/current/CLOUD-REVALIDATION-2026-10-15-1856UTC.md).

La rama `codex/aws-v11-deploy-sync` está publicada hasta `977f437` y el quality
gate remoto pasó (`38792459084`). `main` no se modificó; el workflow no despliega
recursos cloud.

## Estructura

- `core/`: caso, arquitectura empresarial, propuesta cloud, rúbrica y hoja de ruta.
- `app/`: portal B2B, API, Function Azure de demostración y pruebas.
- `iac/`: CloudFormation de AWS y Terraform de Azure; revisar estado antes de aplicar.
- `orchestration/`: puertas y secuencia controlada de reconstrucción.
- `evidence/current/`: evidencia y mapas fechados, con límites de cada afirmación.
- `deliverables/`: documentos académicos existentes; no asumir que un Entregable 1 es el informe final.

Se conserva una copia local restringida del state anterior a la migración como
respaldo; no se versiona. Los estados activos están en el backend remoto Azure y
sus planes vivos no mostraron cambios. El buzón interno no es un servicio de
correo corporativo ni la pila AWS tiene SMTP productivo configurado. El
[checklist vigente](evidence/current/CHECKLIST-CIERRE-2026-10-15.md) distingue
lo demostrado de lo pendiente.
