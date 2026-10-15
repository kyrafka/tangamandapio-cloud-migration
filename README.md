# Tangamandapio S.A.C. — centro de operaciones cloud

Proyecto académico de arquitectura para una distribuidora peruana ficticia. El caso base contempla 450 colaboradores, 220 cuentas internas, centros en Lima, Arequipa y Trujillo y hasta 3,000 usuarios externos concurrentes durante campañas. La expansión internacional es una meta de diseño, no una capacidad ya desplegada o medida.

## La idea principal

Portal B2B y ERP son dominios funcionales distintos: el portal sirve a distribuidores/clientes y el ERP a los equipos internos. Para este prototipo se presentan juntos en la misma web y usan el inicio de sesión y los permisos existentes; sus tablas y APIs están separadas por módulo. Si la escala operativa lo exige, el ERP puede extraerse después como servicio independiente. Azure conserva la autoridad del inventario WMS; el ERP envía ventas y recepciones, pero no mantiene otra copia de existencias. La mensajería ERP persiste dentro del portal y ahora admite un relay SMTP configurable; en local, Compose usa Mailpit como receptor de prueba, no como correo público ni buzones corporativos.

El catálogo trae 12 SKU sintéticos y se amplía desde ERP → Maestros con la plantilla Excel (editar y guardar como CSV UTF-8 antes de importar). La carga admite hasta 500 productos, valida el archivo completo y sincroniza el catálogo con el ledger de Azure. El saldo inicial solo se aplica a SKU nuevos; actualizar fichas conserva existencias. Las ventas y recepciones modifican saldos sintéticos de forma idempotente; no representan inventario físico. El release v11 está desplegado en AWS y verificado en dos instancias. Detalles funcionales y pruebas: [importación de catálogo sintético](evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md) y [evidencia de v11](evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

El proyecto hermano se usa como referencia del problema del datacenter corporativo centralizado, no como fuente de las cifras de Tangamandapio. La arquitectura objetivo, responsabilidades, candidatos ERP/correo y fases están en [core/12_arquitectura_empresarial_portal_erp_correo.md](core/12_arquitectura_empresarial_portal_erp_correo.md).

## Estado vigente

**Última revalidación cloud: 15/10/2026, 14:30 UTC; UI/E2E: 14:45 UTC.** El perfil AWS autenticó en la
cuenta académica; CloudFormation está `UPDATE_COMPLETE`, el ALB está activo,
HTTPS/443 sirve la aplicación y HTTP/80 redirige a HTTPS. Sus dos destinos y
las dos instancias EC2 están saludables; `/health` y `/ready` respondieron 200.
RDS está disponible, cifrada y privada, pero sigue Single-AZ con un día de
retención. La Function de Azure está `Running`, `httpsOnly=true` y
`/api/health` respondió 200. En Chrome se probó la portada, el acceso, la
validación de campos, el teclado y el ancho móvil de 390 px. El 14:45 se volvió
a revisar en esa pestaña el tema claro/oscuro y el formulario vacío; el modo
claro se ve con contraste bajo y se restauró el oscuro. No se autenticó, así
que las vistas internas y los roles no se marcan como probados visualmente. Un
E2E adicional por el dominio HTTPS se detuvo en login con HTTP 403, antes de
crear pedidos o eventos; la causa exacta no se confirmó. La compuerta local
pasó 176 pruebas Python, 14 Node y validaciones de build/IaC, sin aplicar
cambios cloud. GitHub Actions aprobó los tres jobs del commit `ee26e47` a las
14:51 UTC ([ejecución](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38754842826)). Consultar el [corte cloud](evidence/current/CLOUD-REVALIDATION-2026-10-15-1430UTC.md)
y el [seguimiento Chrome/E2E](evidence/current/CLOUD-UI-SMOKE-2026-10-15-1445UTC.md)
para distinguir resultados y límites.

### Corte histórico (02:58 UTC)

**Corte vigente: 15/10/2026, 02:58 UTC.** AWS `default` autenticó por STS en la cuenta académica `841113066612`; el ALB `tangamandapio-alb` está `active`, sus dos destinos están `healthy` y `/health` respondió 200 bajo una microcarga de 120 solicitudes/8 concurrentes. Ese endpoint ejecuta `SELECT 1`, por lo que prueba disponibilidad de la ruta ALB→aplicación→RDS, no ventas. CloudFormation `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; la última detección de drift (02:36 UTC) terminó `IN_SYNC`, cero diferencias. El release `20261014-landing-loading-v11-python312` está activo en dos instancias `InService`. La VPC separa ALB público, aplicación privada y RDS aislada; RDS está `available`, cifrada, privada, 20 GB, Single-AZ y con backup de un día. Las cinco alarmas CloudWatch están `OK` con acciones habilitadas. Azure for Students está `Enabled`; la Function está `Running`, `httpsOnly=true` y `/api/health` respondió 200 en la revalidación a las 02:58 UTC. El [corte completo](evidence/current/CHECKLIST-CIERRE-2026-10-15.md) distingue comprobaciones de pendientes.

El artefacto v11 fue publicado en el bucket privado versionado con cifrado SSE-S3, y la actualización se aplicó con la política CloudFormation `AutoScalingRollingUpdate` de lote uno y dos instancias mínimas en servicio. El primer método de refresh fue denegado por la SCP del laboratorio; se revirtió y sustituyó por el mecanismo gradual permitido, que completó correctamente. No se modificaron RDS ni la red.

No se aplicó Terraform ni se modificó infraestructura Azure en este corte. Function `tangama-wms-261008` sigue `Running`, `httpsOnly=true` y `/api/health` respondió HTTPS 200 después del ejercicio de recuperación. Application Insights reportó en su consulta previa de 24 h 17 solicitudes y cero fallidas; el E2E vivo posterior volvió a confirmar procesamiento de eventos. Son datos agregados, no sustituyen una correlación por evento ni una captura del dashboard. El WMS/ledger contiene datos sintéticos y no representa inventario físico.

El E2E vivo del 15/10 autenticó Admin, importó un SKU QA, registró venta y recepción compensatoria, entregó ambos eventos a Azure y dejó el ledger 10→10. Comercial y Operaciones recibieron los 200/403 previstos en la matriz API. La restauración PT-DR-01 del 15/10 verificó los datos, midió RTO 260 s/RPO superior observado 8 s y limpió recursos temporales. El WMS sigue siendo un ledger sintético. Siguen pendientes conexión privada AWS–Azure, recorridos visuales autenticados de roles, prueba CSV desde archivo en la UI, carga transaccional por ALB, evidencia independiente de entrega de alertas Azure y WebRTC A/V entre dos navegadores. Dominio y HTTPS ya están activos y no son brechas actuales. Ver [matriz de rúbrica](core/04_matriz_rubrica.md), [checklist de cierre](evidence/current/CHECKLIST-CIERRE-2026-10-15.md) y [preflight VPN](evidence/current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

La puerta local más reciente terminó aprobada: **176 pruebas Python, 14 Node, 40 transacciones aisladas**, auditoría de dependencias sin vulnerabilidades conocidas, build Vite, `cfn-lint` y Terraform `fmt`/`validate`/tests; no hizo `apply` ni escrituras cloud. Las pruebas aisladas no miden capacidad para 3,000 usuarios. Repetición: `.\tests\run_local_quality.ps1 -ValidateTerraform`; [QA local del 15/10](evidence/current/QA-LOCAL-2026-10-15.md).

El commit `ee26e47` fue publicado en `codex/aws-v11-deploy-sync` y sus tres
checks de GitHub Actions (backend/flujo, frontend e infraestructura AWS/Azure)
terminaron `success`. `main` no se modificó.

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
