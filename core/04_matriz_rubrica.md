# Matriz de evidencia por criterio — actualización 15/10/2026, 04:11 UTC

## Conclusión de calificación

No se puede defender una nota numérica con la rúbrica disponible. Sus 14 pesos
suman **18.5**, aunque la celda final declara 20, y no asigna equivalencias
numéricas a Excelente/Bueno/En proceso/Deficiente. Por eso se retiran tanto el
cálculo anterior **11.75/20** como la proyección **15–16/20**: la primera usó una
conversión inventada; la segunda no tenía una suma criterio por criterio. El
estado apagado del laboratorio no se descuenta en un supuesto de despliegue, pero
desplegar los recursos tampoco cierra por sí solo los criterios que requieren
funciones y pruebas demostrables. Hace falta que el docente aclare el total y la
conversión antes de estimar una nota. La tabla siguiente es cualitativa y lista
evidencia y trabajo pendiente, no puntos.

La fuente analizada es la rúbrica final `rúbrica proyecto_qod3szrctm (3).xlsx`
(14 criterios); el resumen histórico de cálculos retirados está en
[la evaluación previa](10_evaluacion_rubrica_entregable_final_2026-10-08.md).
Para el estado AWS más reciente, consulta el
[despliegue v11 y su recuperación](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).
Los cortes sanos anteriores se conservan en el
[despliegue AWS previo](../evidence/current/aws/AWS-DESPLIEGUE-2026-10-14.md), el
[inventario AWS](../evidence/current/aws/AWS-INVENTARIO-2026-10-13.md), la
[revalidación Azure](../evidence/current/azure/AZURE-PLAN-PAQUETE-2026-10-13.md)
y la [revalidación anterior a v11](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

## Revalidación anterior — 15/10/2026, 04:11 UTC

AWS STS autenticó en la cuenta Academy 841113066612; ALB activo, 2/2 destinos
healthy, portada y /health 200. ASG 2/2/5; RDS available, privada, cifrada,
20 GB, Single-AZ y backup de un día. CloudFormation UPDATE_COMPLETE; estado
visible IN_SYNC (detección más reciente registrada a las 02:36 UTC). De siete
alarmas métricas, seis OK y una TargetTracking de escala baja INSUFFICIENT_DATA;
todas con acciones habilitadas. Listener ALB solo HTTP/80.

El E2E desde EC2 por SSM autenticó Admin, completó venta completed_demo y
recepción received_demo, entregó dos eventos a Azure y devolvió el ledger demo
a 10→10. Comercial y Operaciones obtuvieron los 200/403 previstos. Las 24
lecturas autenticadas fueron 24/24 HTTP 200, p95 277.17 ms, concurrencia 6,
por loopback, no por el ALB. Azure /api/health devolvió HTTPS 200.

Terraform leyó los dos estados remotos Azure; los planes de azure-rebuild y
azure-tfstate terminaron No changes. El contenedor es privado y requiere Entra;
shared-key está deshabilitado, TLS mínimo 1.2 y HTTPS obligatorio. La red
pública de la cuenta sigue habilitada. Gate local 165 Python, 14 Node, 40
transacciones aisladas, build y auditorías aprobados. GitHub Actions del commit
39617c9 terminó success. El detalle está en
[la revalidación del 15/10](../evidence/current/CLOUD-REVALIDATION-2026-10-15-0410UTC.md).

## Actualización posterior — 15/10/2026

Con la sesión temporal AWS renovada, STS autenticó la cuenta Academy. El E2E
vivo posterior volvió a dejar CloudFormation `UPDATE_COMPLETE`, los dos
destinos ALB `healthy`, el health del portal en HTTP 200 y el health de Azure
en HTTPS 200. Admin consultó el estado de SNS (2 confirmadas, 0 pendientes);
Comercial y Operaciones obtuvieron 403 en esa ruta. No se cambiaron
suscripciones ni se mandaron correos. El flujo ERP sintético entregó venta y
recepción a Azure y dejó el ledger demo en 10→10; 24 lecturas RDS dieron 24/24
HTTP 200 (p95 2,005.03 ms, concurrencia 6, por loopback EC2). La nueva
compuerta local pasó 169 pruebas unitarias, 14 Node, 40 transacciones
aisladas, build y IaC; GitHub Actions del commit `034a06e` terminó con los tres
jobs exitosos. La evidencia detallada y sanitizada está en
[el smoke de alarmas y permisos](../evidence/current/aws/AWS-ALARM-SUBSCRIPTIONS-ROLE-SMOKE-2026-10-15.md).

## E2E vigente por ALB — 15/10/2026, 05:33 UTC

La prueba autenticada se dirigió al ALB público: Admin, Comercial y Operaciones
respetaron la matriz 200/403; catálogo, venta y recepción sintéticas completaron
el ciclo portal→RDS/outbox→Azure; dos eventos fueron entregados y el ledger demo
quedó en 10→10. Las 24 lecturas por el ALB dieron 24/24 HTTP 200, p95 216.61 ms
a concurrencia 6. Esto prueba el recorrido acotado, no capacidad para 3,000
usuarios. Evidencia: [E2E por ALB](../evidence/current/aws/AWS-PORTAL-ERP-AZURE-ALB-E2E-2026-10-15-0533UTC.json).

## Corte histórico — 15/10/2026, 02:58 UTC

Revalidación anterior: AWS STS autenticó en la cuenta
Academy `841113066612`; ALB `active`, 2/2 destinos `healthy` y una microcarga
de 120 sondas `/health` 200 a concurrencia 8; Azure `/api/health` también dio
200 en la misma revalidación. CloudFormation
continúa `UPDATE_COMPLETE`; la detección de las 02:36 UTC terminó `IN_SYNC` con
cero recursos discrepantes. El target group conserva 2/2 destinos
`healthy`; ALB `/health` respondió 200 a las 02:45. RDS `tangamandapio-postgres`
sigue `available`, privada y cifrada. El ejercicio PT-DR-01 aislado restauró
una copia SQL, verificó marcador y tablas, midió RTO 260 s/RPO superior
observado 8 s y confirmó la limpieza de instancia/snapshot temporales.
El E2E portal EC2→RDS/outbox→Azure terminó `LIVE_E2E_PASSED`: Admin importó un
SKU QA, venta `completed_demo`, recepción `received_demo`, dos eventos
entregados y saldo 10→10; las reglas API de Comercial/Operaciones devolvieron
los 200/403 esperados. Veinticuatro lecturas autenticadas fueron 24/24 HTTP
200, p95 476.1 ms, concurrencia 6, en una EC2 (no por ALB y no representa 3,000
usuarios). Azure Function continúa `Running`, HTTPS-only y health 200. La
conectividad privada sigue sin VNet/VPN: AWS Academy denegó
`CreateCustomerGateway` por SCP. El branch `codex/aws-v11-deploy-sync` está
publicado en `fa8224e`; la puerta local aprobó 165 Python, 14 Node, 40
transacciones aisladas, build, auditorías, CloudFormation y Terraform. GitHub
Actions para `fa8224e` completó con éxito sus tres jobs: backend/flujo,
frontend e infraestructura AWS/Azure. CSV desde
archivo/UI, recorrido visual de roles, carga por ALB, entrega Azure alertas,
state remoto privado, VPN, WebRTC y HTTPS siguen sin evidencia completa. No se
asigna nota: la rúbrica suma 18.5 en pesos aunque declara 20 y no define
conversión numérica por descriptor.

Los bloques fechados más abajo conservan resultados de cortes anteriores; no
deben interpretarse como estado posterior a v11. El resumen y la tabla de esta
primera sección reflejan la última evidencia disponible.

## Estado cualitativo por criterio

| # | Criterio | Evidencia disponible (corte indicado) | Brecha para el descriptor más alto |
|---:|---|---|---|
| 1 | Análisis del problema y requerimientos · 1.0 | Caso, restricciones y requisitos están documentados; el crecimiento multisede/internacional está separado de capacidades ya desplegadas. | Mantener la trazabilidad requisito→componente→prueba en el informe final y defender los supuestos ante el docente. |
| 2 | Diseño de arquitectura cloud · 2.0 | Arquitectura AWS–Azure, diagramas y separación entre estado implementado y objetivo están documentados; AWS atiende el portal y Azure procesa eventos de demostración. | Presentar el diseño y justificar decisiones/capacidad objetivo en la sustentación. |
| 3 | Redes VPC/VCN · 2.0 | VPC AWS `10.10.0.0/16`, subredes públicas/privadas/aisladas en dos AZ y security groups encadenados ALB:80→app:8080→DB:5432; lectura viva posterior con los destinos saludables. | No hay VNet ni rutas/VPN privadas AWS–Azure. Con el token nuevo, `CreateCustomerGateway --dry-run` fue denegado por un `explicit deny` SCP; tampoco existe VNet en la suscripción Azure. Requiere habilitación del administrador de la cuenta AWS y provisionar la red Azure; no sortear la política. HTTPS público no sustituye conectividad privada. Ver [preflight](../evidence/current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md). |
| 4 | Cómputo, almacenamiento y BD · 1.5 | v11 desplegado: dos EC2 `InService`, dos destinos ALB `healthy`, ASG mínimo/deseado 2 máximo 5; RDS disponible/cifrada/privada, Single-AZ, backup un día. Restore SQL aislado del 15/10 comprobó marcador e integridad con RTO 260 s y RPO superior observado de 8 s. | No se ha demostrado Multi-AZ ni failover automático; el ledger Azure es ficticio. |
| 5 | Seguridad cloud · 2.5 | E2E del 15/10 por ALB: Admin autenticó; matriz viva API Comercial/Operaciones verificó rutas 200/403, incluida la gestión de suscripciones SNS; `/api/admin/users` anónimo devolvió 401 en corte previo. Security groups no exponen EC2/RDS a Internet; Azure exige Function key y rechazó origen no autorizado sin persistencia. | Falta revisión visual autenticada en navegador. ALB continúa sin HTTPS confiable; dominio/certificado siguen diferidos. |
| 6 | Alta disponibilidad y escalabilidad · 1.5 | Prueba histórica de Target Tracking 2→3 y despliegue gradual v11 conservó dos instancias saludables. E2E por ALB el 15/10 completó venta/recepción y dos eventos a Azure; 24 lecturas autenticadas 24/24 HTTP 200, concurrencia 6, p95 216.61 ms. ASG actual 2/2, dos EC2 `InService`/`Healthy`, máximo 5. | Esta carga acotada no demuestra capacidad para 3,000 usuarios ni failover Multi-AZ; falta prueba de carga transaccional representativa y dimensionamiento, además de HA de RDS. |
| 7 | Monitoreo y observabilidad · 1.0 | Siete alarmas métricas CloudWatch con acciones habilitadas: seis `OK`; la alarma TargetTracking de escala baja está `ALARM` por CPU < 42%, con ASG ya en mínimo 2. SNS conserva dos suscripciones confirmadas; el usuario confirmó recepción de alerta y recuperación, pero no se archivó captura independiente. Action Group Azure y sus dos receptores están habilitados; Application Insights reportó 17 solicitudes/24 h y cero fallidas en el corte anterior; el E2E confirma dos eventos demo procesados. | Faltan capturas visuales de dashboards y evidencia independiente de la bandeja. Contadores agregados no sustituyen correlación de negocio. |
| 8 | Infrastructure as Code · 1.5 | CloudFormation desplegó `AutoScalingRollingUpdate`; stack `UPDATE_COMPLETE`, estado visible `IN_SYNC` (última detección registrada 15/10 02:36 UTC). Los estados Azure están en backend remoto; planes vivos de `azure-rebuild` y `azure-tfstate` dieron `No changes`. Contenedor privado/Entra, shared-key deshabilitado, TLS 1.2; red pública de cuenta aún habilitada. | No hay IaC aplicada para la red privada. Mantener una copia local restringida del state de bootstrap como respaldo; habilitar red privada/firewall para el backend cuando exista un runner autorizado. No versionar state ni secretos. |
| 9 | Backup, RTO/RPO y recuperación · 1.5 | Restore aislado del 15/10 validó marcador y conteos de tablas de negocio; RTO 260 s, RPO superior observado 8 s, instancia privada/cifrada y limpieza temporal verificada. | Presentar que RPO es un límite observado de esta prueba, no garantía; RDS está en Single-AZ y no se probó failover Multi-AZ. |
| 10 | Arquitectura AWS–OCI / multicloud · 1.5 | Acuerdo oral para usar AWS–Azure; E2E por ALB portal→RDS/outbox→Azure Queue/Function del 15/10 entregó venta/recepción sintéticas y ledger 10→10. | No hay conexión privada AWS–Azure; no presentar Azure como OCI ni afirmar inventario comercial. |
| 11 | Costos y optimización · 0.5 | Existe cálculo reproducible de precio público AWS, basado en inventario y supuestos explícitos; se documentaron optimizaciones y sensibilidad. | El subtotal AWS ($91.92/mes) excluye variables; Azure Storage/Queue y el costo real del programa académico siguen sin medición/captura de Cost Analysis. La proyección es orientativa, no una factura. |
| 12 | Pruebas técnicas · 1.0 | Suite local completa: 167 Python (159 subtests), 14 Node, build, `cfn-lint` y Terraform fmt; CI validará los cambios del runner. E2E vivo por ALB autenticó Admin, importó catálogo, completó venta/recepción portal→RDS/outbox→Azure; matriz API 200/403 y 24/24 lecturas p95 216.61 ms. Restore RDS medido. | Falta carga transaccional representativa, CSV desde UI, evidencia de entrega de alertas Azure y revisión visual. WebRTC sigue diferido. |
| 13 | Documentación técnica · 0.5 | README, matriz y evidencia actualizados con E2E por ALB y restore del 15/10, RTO/RPO, salud y limpieza. | Faltan capturas actuales del inventario AWS y monitor Azure (el usuario las recopilará) y revisar visualmente el informe final. |
| 14 | Sustentación y defensa técnica · 0.5 | No evaluable desde archivos o código. | Demostrar el entorno y explicar arquitectura, decisiones, costos, pruebas y límites ante el docente. |

## Actualización de evidencia — 14/10/2026, 01:44–01:51 America/Chicago

Terraform Azure consultó la suscripción activa y terminó `No changes` (sin
`apply`); AWS STS volvió a autenticar, CloudFormation reportó
`UPDATE_COMPLETE`, los dos destinos siguieron `healthy` y RDS continuó
disponible, cifrada y privada con Single-AZ/retención de un día. La compuerta
local aprobó 122 pruebas Python, 8 de navegación por rol, build, auditorías y
validaciones IaC. El usuario confirmó haber recibido los avisos SNS de alarma y
recuperación sintéticas; no hay captura independiente de la bandeja ni una
alarma disparada por métrica real. Ninguna de estas comprobaciones prueba la
VPN privada, un WMS comercial, sesiones autenticadas en navegador ni WebRTC
entre navegadores. Véanse la [revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md),
[QA local](../evidence/current/QA-LOCAL-2026-10-14.md) y
[prueba SNS](../evidence/current/aws/AWS-ALARM-TEST-2026-10-14.md).

## Preflight AWS–Azure VPN — 14/10/2026, 02:17 America/Chicago

AWS STS autenticó, pero CloudFormation devolvió `AccessDenied` y las consultas
EC2 de VPN devolvieron `UnauthorizedOperation`. La prueba de autorización
`CreateCustomerGateway --dry-run` fue denegada sin crear recursos. Azure está
autenticado y `Enabled`, pero `rg-tangama-private-network` no existe. No se
desplegó nada ni se incurrieron cargos nuevos. La conexión privada sigue sin
demostrar y necesita autorización de red AWS y reconstrucción Azure. Ver
[evidencia detallada de preflight](../evidence/current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

## Smoke público — 14/10/2026, 02:20 y 02:45 America/Chicago

El ALB AWS vigente devolvió 503 en portada, health, readiness y rutas admin;
la lectura posterior a QA de las 02:45 confirmó que persiste.
Azure `/api/health` respondió 200; local respondió 200 en `/`, `/health` y
`/ready`, y 401 en la API admin anónima. El 503 no identifica por sí solo la
causa, y las consultas de inventario AWS están denegadas. Se retira cualquier
afirmación de disponibilidad AWS actual hasta recuperar acceso y repetir la
verificación. Ver [corte cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

En una lectura posterior de solo lectura (02:03), el stack entregó los tamaños
vigentes usados por el [modelo de costo reproducible](13_estimacion_costos_cloud_2026-10-14.md):
ASG mínimo/deseado 2 × `t3.micro`, RDS PostgreSQL `db.t3.micro`/20 GB gp3,
Single-AZ, 1 día de backup, ALB, NAT Gateway y dos secretos. El subtotal público
AWS de $91.92/mes depende de 730 h, 1 LCU y 10 GB de NAT; no representa una
factura ni incluye todos los cargos. El costo variable de Storage/Queue Azure
no se estimó sin volumen real.

## Revalidación viva — 14/10/2026, 00:58 America/Chicago

AWS autenticó por STS; CloudFormation está `UPDATE_COMPLETE`/`IN_SYNC`, los dos
destinos están `healthy` y RDS `available`, cifrada, privada, Single-AZ y con
backup de un día. El ALB `/health` devolvió HTTP 200 con DB `ok`. Azure confirmó
la Function `Running`, `httpsOnly=true`, Linux/West US; `/api/health` respondió
200 y Application Insights registró dos ejecuciones de
`process_fulfillment_message`, código 0 y ninguna fallida. La alarma se probó
con cambio de estado sintético `OK → ALARM → OK`; SNS aceptó ambas acciones y
CloudWatch restauró `OK`, pero no se confirmó llegada a las bandejas. No hubo
despliegues ni cambios permanentes. Evidencia: [corte cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md), [alarma](../evidence/current/aws/AWS-ALARM-TEST-2026-10-14.md).

## Revalidación viva — 13/10/2026, 23:50 America/Chicago

AWS STS autenticó; CloudFormation seguía `UPDATE_COMPLETE`, los dos destinos
del ALB estaban `healthy` y RDS `available`, cifrada, Single-AZ y con backup de
un día. El portal local respondió `/health` y `/ready` con HTTP 200. Azure
respondió `/api/health` con 200; el grupo figuró `Succeeded` y la consulta ARM
de la Function devolvió `Running`, HTTPS-only y el host
`tangama-wms-261008.azurewebsites.net`. La CLI de Azure sí está instalada en el
host, fuera del `PATH` de PowerShell; la lectura anterior que decía que no estaba
disponible fue incompleta. Fueron comprobaciones de solo lectura: no hubo cambios
en AWS o Azure. No se volvió a ejecutar un E2E en este corte.

## Registro histórico (no usar para estado ni cálculo vigente)

## Seguimiento vivo previo — 13/10/2026, 23:41–23:43 (supersedido)

AWS STS aceptó la sesión. CloudFormation sigue `UPDATE_COMPLETE`, el ALB tuvo
2/2 destinos `healthy`, `/health` y `/ready` respondieron 200, y RDS continuó
disponible/cifrada, Single-AZ y con retención de un día. Sin sesión, el panel de
administración redirigió con 303 y las dos APIs admin consultadas respondieron
401. En esa comprobación inicial se concluyó incorrectamente que Azure CLI no
estaba disponible; la CLI estaba instalada fuera de `PATH`. La relectura exitosa
de ARM quedó registrada a las 23:50 en la sección vigente de este documento. No
hubo cambios de recursos. Evidencia en
[corte cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md).

## Revalidación de evidencia viva — 13/10/2026, 23:00

AWS fue consultado nuevamente: el stack siguió `UPDATE_COMPLETE`, 2/2 targets
healthy y health/readiness 200; RDS continuó cifrada y disponible, pero
Single-AZ con retención de un día. Azure ARM localizó la Function en el grupo
`rg-tangamandapio-rebuild-wus`, `Running`/HTTPS-only, con hash de release
coincidente; el endpoint health dio 200. El E2E ERP-local→Queue/Function
completó venta y recepción compensatoria, con el ledger ficticio restituido a
su saldo inicial. Esto robustece la evidencia del criterio 12, pero no cierra
sesiones de rol live, conectividad privada ni WMS real. Ninguna banda de criterio
cambia por esta comprobación. La cifra anterior **11.75/20 queda retirada**
porque los pesos enumerados en la fuente no suman el total impreso y no hay
conversión numérica oficial por nivel. Esta limitación impide convertir la
proyección hipotética 15–16/20 en una calificación exacta.
Evidencia detallada en la
[revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md) y el
[E2E Azure](../evidence/current/azure/AZURE-ERP-E2E-2026-10-13.md).
Un Terraform plan Azure contra el state y ZIP actuales devolvió `No changes`
(exit 0, sin apply), reforzando la reconciliación IaC del criterio 8. Esto no
sustituye la verificación de drift de CloudFormation ni prueba conectividad
privada.

## Reevaluación tras el release AWS v4 — 13/10/2026, 22:47

Se aplicó la misma conversión explícita del informe (Excelente 100%, Bueno
75%, En proceso 50%, Deficiente 0%) a los 14 criterios y se revisó la evidencia
live nueva. La cifra previa **11.75/20 queda retirada** por la inconsistencia
de pesos descrita al inicio; el release verificable mejora la evidencia dentro de las bandas Bueno
ya asignadas a cómputo/BD, disponibilidad, IaC y pruebas, pero no basta para
elevar su nivel. Seguridad continúa en proceso porque solo se comprobó la
frontera anónima live; faltan sesiones autenticadas de todos los roles y TLS
confiable. No hay VNet/VPN privada AWS–Azure ni escala transaccional bajo carga.
PT-DR-01 ya verificó marcador SQL y 14 tablas, RTO 289 s, RPO superior 14 s y
limpieza; no se repitió en este corte. Faltan cálculo reproducible de costos y
sustentación. El informe final DOCX y las capturas crudas de
consola/navegador también siguen pendientes. El nuevo estado live está en la
[revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md).

**Seguimiento vivo — 13/10/2026, 20:10 America/Chicago:** el E2E compensado
posterior al release Azure concluyó venta y recepción con el ledger demo de
vuelta a la línea base; la cola poison reportó 0 mensajes sin exponer payloads.
El health público Azure y readiness local respondieron 200. En la consulta más
reciente, AWS STS respondió `ExpiredToken`; antes, con STS válido, la política
`voc-cancel-cred` denegó `DescribeStacks`. Se requiere sesión nueva para volver
a autenticar y autorización del laboratorio para leer/desplegar. Esto no
demuestra la VPN ni tráfico desde EC2, por lo que no cambia la estimación
provisional **11.75/20**. Véase la [revalidación actual](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md).

**Corte posterior — 13/10/2026, 19:20 America/Chicago:** el consumidor Azure
ahora valida de nuevo el tipo de evento en la frontera de Queue. Pasó la
compuerta completa (120 pruebas), se aplicó mediante Terraform solo el Blob de
release y la configuración de la Function, y el plan posterior quedó sin
cambios. La prueba viva rechazó un tipo no permitido con HTTP 400 antes de
persistirlo; esto fortalece seguridad, pruebas e IaC, pero no convierte el
ledger ficticio en un WMS comercial ni demuestra la VPN. AWS STS acepta el
token actual, mientras `DescribeStacks` sigue denegado explícitamente; no se
desplegó el candidato AWS. Se conserva **11.75/20** como autoevaluación
provisional sin recalcular: el cambio no cierra los huecos de red multinube,
verificación del release AWS y sustentación. Véanse el [release Azure](../evidence/current/azure/AZURE-RELEASE-EVENT-TYPE-GUARD-2026-10-13.md)
y la [revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md).

**Alcance:** el alumno comunicó que el docente confirmó presencialmente que se
puede usar AWS–Azure. OCI no está implementado. La aceptación verbal no está
respaldada por un documento en el repositorio; explicar el acuerdo en el informe
y adjuntar constancia si está disponible. Esta autoevaluación no es una nota
docente ni presume cumplimiento de VNet/VPN por tener Azure Functions.

**Corte de evidencia — 13/10/2026, 18:43 America/Chicago:** el E2E Azure más
reciente procesó una venta y su recepción compensatoria por Queue/Function y
restauró el ledger ficticio; el ERP de prueba se ejecutó localmente, no desde
EC2. AWS STS aceptó la sesión, pero `voc-cancel-cred` denegó
`cloudformation:ListStacks`; el ALB respondió salud, mientras las dos rutas de
administración publicadas siguen en 404. No se cambió infraestructura ni se
recalculó la estimación 11.75/20: estas pruebas fortalecen el flujo Azure y la
evidencia operativa, pero no cierran red privada, release AWS ni los otros
criterios incompletos. `DescribeStacks` también fue denegado por nombre exacto,
así que no basta con evitar el listado: AWS debe permitir lectura del stack
conocido para ejecutar el preflight. Véanse la [revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md)
y la [prueba E2E](../evidence/current/azure/AZURE-ERP-E2E-2026-10-13.md).

**Control de acceso ERP — 13/10/2026, 19:00 America/Chicago:** la auditoría
encontró que `/api/erp/overview` filtraba agregados financieros a roles sin
`finance:read`. El backend y las interfaces local/release se corrigieron para
devolver y presentar únicamente las métricas autorizadas. La regresión se
reprodujo antes de corregir y después pasaron las pruebas para Ventas, Datos
maestros, Finanzas y Administración en ambos backends. La compuerta completa
quedó en 118 pruebas; el candidato v2 tiene hash registrado en la evidencia
local y no se ha subido a AWS. Esto mejora el criterio de seguridad, pero no
cambia la estimación ni corrige el despliegue live, que permanece pendiente de
lectura CloudFormation.

**Actualización de evidencia:** la puerta local aprobó 81 pruebas unitarias,
auditoría de dependencias, build frontend, lint de CloudFormation y validación
de Terraform. Los scripts de red pasan análisis sintáctico y pruebas locales
del mapeo BGP y guardas de costo/limpieza; la sonda de restore pasa un round-trip
de empaquetado. La puerta incluye la recuperación idempotente de la contraseña
admin por versión de secreto y una guarda simulada que bloquea la eliminación
cuando el template desplegado no protege el snapshot. Azure Functions suma
21/21 pruebas; esto no equivale a conectividad entre nubes ni recuperación RDS.
Azure fue reconstruido el 12/10 y la prueba viva de Function, Blob/Queue e
idempotencia pasó; Terraform volvió a planear sin drift. También pasó un ciclo vivo ERP local
→ outbox → Azure Queue/Function → reconciliación, con venta sintética y
recepción compensatoria que devolvió el stock ficticio al valor inicial. Esta
prueba no fue originada por AWS ni demuestra integración desde la instancia
desplegada o conectividad privada AWS→Azure. El chequeo independiente más
reciente de AWS se documenta abajo; sus permisos de inventario no bastaron para
confirmar recursos.
El 12/10 se repitió ese ciclo con el artefacto local preparado para AWS: venta
y recepción compensatoria aprobadas; el corte anterior de Application Insights
registró 15 solicitudes/0 fallos. En la consulta final hubo 114 solicitudes y
5 fallos del worker con excepciones categorizadas como
checksum/mismatch, consistentes con la prueba poison sintética; falta confirmar
correlación por operación. La cola poison estaba vacía al revalidar.
El 12/10 se aplicaron en Azure la cola poison, el permiso de lectura mínimo y la
ruta autenticada que devuelve solo su conteo. Un mensaje sintético con checksum
inválido agotó los reintentos y llegó a poison; se verificó el marcador y se
limpió el mensaje de prueba. El conteo final quedó en 0. También se cambió el
release de la Function a un Blob privado inmutable, descargado con identidad
administrada; `terraform plan` posterior no encontró drift ni eliminaciones.
En el corte de 13/10 AWS STS aceptó la sesión nueva y se restauró de forma
aislada un snapshot PostgreSQL cifrado. La prueba activó el secreto maestro y
limpió la instancia temporal y su subnet group; no verificó SQL ni midió
RTO/RPO. El corte previo al despliegue no tenía recursos del portal activos.
Después, CloudFormation desplegó el portal: stack `UPDATE_COMPLETE`, drift
`IN_SYNC`, dos instancias `t3.micro` sanas en dos zonas y ALB HTTP 200. Las dos
instancias pasaron `/health` y `/ready` con PostgreSQL `ok`. RDS está privado,
cifrado, Single-AZ y con un día de backups. El detalle comprobable está en
[`AWS-DESPLIEGUE-2026-10-13.md`](../evidence/current/aws/AWS-DESPLIEGUE-2026-10-13.md).
La lectura inicial Azure autenticada desde EC2 devolvió 401 por una clave
desfasada en Secrets Manager. Se sincronizó con la clave vigente y se
reemplazaron ambas EC2 gradualmente. El proceso en las dos logró HTTP 200 al
catálogo.

Después, el artefacto desplegado recorrió desde EC2 un E2E aislado: outbox
`delivered`→Azure Queue/Function, venta demo aplicada y recepción
compensatoria; el stock ficticio regresó 24→23→24. La base SQLite temporal se
eliminó, RDS no se modificó y los blobs sintéticos permanecen en Azure. Una
caída controlada anterior también repuso dos instancias `InService`/`Healthy`;
el ALB quedó en 2/2 destinos sanos y `/health` con base `ok`. No se midió RTO
ni escalado por carga en la nube. El 13/10 se midió `/health` local en Docker:
1000 solicitudes a concurrencia 50, p95 68.34 ms y cero errores; el resultado
no caracteriza escrituras transaccionales ni ASG. El admin de producción impone cambio de contraseña y
por eso su endpoint respondió 428; no se omitió el control.

Siguen pendientes VNet/VPN AWS–Azure, escalado automático medido en nube,
notificación de alertas, roles en navegador y cambio de contraseña en el
artefacto desplegado, integridad de datos restaurados y RTO/RPO cronometrada,
A/V real, dominio/HTTPS propio y capturas crudas actuales. El puntaje 11/20 se conserva
como autoevaluación provisional basada en un corte anterior; no se recalculó
tras este despliegue y no reemplaza la rúbrica oficial.

**Actualización de evidencia — 13/10/2026, 04:37 America/Chicago:** el release
Azure con ZIP reproducible se aplicó mediante un plan restringido al Blob del
paquete y la configuración de la Function. La Function quedó Running,
HTTPS-only; health y un E2E de venta/compensación pasaron; el plan posterior fue
`No changes`. Esto fortalece la evidencia de implementación Azure, pruebas e
IaC para el flujo de negocio demo, pero el E2E parte del ERP local: no demuestra
tráfico desde EC2 ni red privada. En AWS, STS acepta el token actual pero
`voc-cancel-cred` deniega lecturas de inventario; no hay nuevo estado operativo
confirmado. El 11/20 sigue siendo el total del corte previo, no una reevaluación
posterior a estos hechos.

**Corte de seguimiento — 13/10/2026, 04:53 America/Chicago:** se volvió a
validar el perfil AWS `default` con la terna entregada más recientemente. El
identificador coincide y los campos están presentes, pero STS rechazó el token;
no se hizo ningún cambio de infraestructura y no se pudo inspeccionar AWS
Academy. Azure for Students respondió `Enabled` y el endpoint HTTPS de health de
la Function devolvió HTTP 200; la consulta ARM de estado quedó sin respuesta y
no acredita inventario. La batería local aprobó de nuevo 81 pruebas y todas las
validaciones estáticas. También se endureció el arnés DR: RTO desde solicitud
del restore, sin backups automáticos extra para la copia y guardas locales para
ambos invariantes; esto todavía no es un restore SQL vivo. Este corte no permite aumentar la estimación de la
rúbrica ni afirmar que AWS esté disponible; **11/20 sigue siendo un cálculo
anterior no reevaluado**.

En la última revalidación cloud (03:19 del 13/10), STS autenticó, pero la
política `voc-cancel-cred` denegó el inventario AWS y el DNS del ALB no resolvió;
el despliegue sano descrito arriba es histórico. A las 03:39 pasó la compuerta
local con 81 pruebas y se reconstruyó el portal Docker preservando datos, sin
`apply` cloud. Por tanto, el 11.00/20 sigue siendo la autoevaluación del corte
anterior, no un puntaje vigente reevaluado. Ver [revalidación actual](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Endurecimiento local de red — 13/10/2026, 05:07 America/Chicago:** el
preflight de despliegue VPN compara CIDR AWS/Azure, asociación de route table y
subred del gateway; falla cerrado si la consulta AWS no distingue
`AccessDenied` de “stack no existe”, y solicita aprobación adicional si los
parámetros del stack existente cambian. Cuatro casos simulados y la puerta
completa (81 pruebas, lint/build/IaC) pasaron. No se aplicó la VPN ni se probó
conectividad; AWS sigue sin autenticar. No asigno puntos por túneles reales.

**Seguimiento local — 13/10/2026, 05:23 America/Chicago:** AWS CLI `default`
coincide exactamente con la terna recibida, pero STS responde `ExpiredToken`;
no se modificaron recursos ni se verificó inventario. El preflight quedó con
7 escenarios mock: denegación, stack ausente, actualización bloqueada/aprobada,
CIDR AWS, tabla de rutas incorrecta y ASN Azure inesperado. La puerta completa
con `-ValidateTerraform` aprobó 83 pruebas,
auditorías, build, CloudFormation, formato/validate y 2 tests mock del gate de
costo. No se recalcula la rúbrica: estas pruebas locales no acreditan VPN,
restore real ni salud actual de AWS. Azure `/api/health` devolvió HTTP 200 a las
05:17, pero `az functionapp show` agotó 30 segundos antes del smoke; no se
publicó evento ni se considera ejecutado un nuevo E2E.

**Preflight VPN reforzado — 13/10/2026, 05:28 America/Chicago:** se verifica
que los IDs de las dos IP públicas de Azure sean exactamente los asociados al
gateway activo-activo. El octavo caso mock rechaza una IP no asociada. Los ocho
escenarios VPN y la puerta completa con 83 pruebas, auditorías, build,
CloudFormation y Terraform pasan localmente. Sigue sin demostrarse la VPN viva;
el puntaje anterior 11/20 no se recalcula con pruebas mock.

**Rate limiting de autenticación — 13/10/2026, 06:02 America/Chicago:** el
backend local ahora aplica bloqueo temporal persistido en la base de datos,
comparte el contador entre instancias de Flask, incrementa fallos atómicamente,
devuelve `429`/`Retry-After`, limpia fallos tras login correcto y guarda la clave
IP/usuario como HMAC. Tres pruebas verifican persistencia entre instancias,
reinicio del contador y fallos concurrentes; la release AWS tiene una prueba
adicional de flujo y la migración 0008 limpia las claves legibles heredadas.
La puerta completa con `-ValidateTerraform` aprobó 87 pruebas, auditorías,
build, CloudFormation, Terraform y guards mock. No se recalcula el 11/20: esto
no demuestra MFA, pruebas de roles en producción, VPN, HTTPS confiable ni otros
criterios cloud pendientes.

**Seguridad de sesión local — 13/10/2026, 06:23 America/Chicago:** se añadió
protección CSRF por defecto al backend local: token aleatorio en la sesión,
cabecera obligatoria para toda escritura, verificación de `Origin`/`Referer` y
rotación al autenticar. La suite integral pasó 91 pruebas; el portal Docker
local respondió con base sana y se verificó `403` sin token, `204` con token,
rotación de token y bundle actualizado. No se recalcula el 11/20: estas pruebas
no certifican MFA, roles en una sesión de navegador, CSRF detrás del ALB/HTTPS,
ni el estado actual de AWS/Azure.

**Gestión de contraseñas local — 13/10/2026, 06:45 America/Chicago:** se
implementó cambio propio y obligatorio de claves temporales, restablecimiento
por administrador con secreto temporal de una sola entrega, auditoría sin
secreto, revocación de sesiones y migración aditiva para bases existentes.
Las pruebas focalizadas y la puerta integral pasaron (**94 pruebas**); el portal
Docker local sirve el bundle nuevo y `/health` confirma base sana. Esto cierra
la implementación local de ese flujo, no la verificación de roles por
interacción manual ni su presencia en AWS desplegado. En este mismo corte STS
rechazó el perfil local con `ExpiredToken`; no hubo acciones cloud. Ver la
[revalidación detallada](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Revalidación cloud — 13/10/2026, 08:20 America/Chicago:** AWS STS acepta la
nueva sesión; CloudFormation confirma el stack `IN_SYNC` (0 recursos con drift),
la instancia principal RDS permanece Single-AZ/1 día y el snapshot manual
cifrado sigue disponible. En Azure, una prueba viva confirmó el recorrido
ERP/outbox→Queue/Function→conciliación y revirtió el movimiento en el ledger
demo al saldo inicial; el portal ejecutado fue local, no EC2, y el WMS sigue
ficticio. Terraform Azure no propone cambios. La VPN temporal no se pudo crear
porque AWS Academy deniega `ec2:CreateCustomerGateway` y Azure se limpió. Estos
resultados fortalecen evidencia de integración/operación, pero no prueban red
privada ni WMS real, por lo que **11/20 sigue siendo la última estimación
provisional; esta nota no la recalcula ni la presenta como nota del docente**.

**Recuperación RDS — 13/10/2026, 08:57 America/Chicago:** pasó PT-DR-01 en
AWS con marcador SQL incluido en el snapshot, conteos iguales en 14 tablas de
negocio, RTO medido de 289 s y RPO superior de 10 s. La restauración temporal
fue privada/cifrada y cleanup verificó la eliminación de copia, snapshot de
prueba y marcadores; RDS principal sigue disponible. Esto mejora evidencia de
recuperación, pero no acredita conectividad privada AWS–Azure ni eleva por sí
solo la estimación global. El detalle está en
[`AWS-DR-RESTORE-2026-10-13.md`](../evidence/current/aws/AWS-DR-RESTORE-2026-10-13.md).
El **11/20** se mantiene como cálculo anterior sin reevaluar; no se otorgan
puntos cloud por la prueba local.

**Guarda previa a la VPN — 13/10/2026, 11:43 America/Chicago:** el script
`deploy_aws_vpn.ps1` ahora ofrece `-AwsPreflightOnly`, una etapa AWS de solo
lectura que valida sesión, stack estable, VPC/CIDR y tabla de rutas antes de
crear recursos facturables en Azure. Una denegación corta el flujo antes de
consultar o aprovisionar Azure; los permisos de creación siguen sin probarse y
CloudFormation es quien los determina. Pasaron 9 escenarios mock y la puerta
local de 94 pruebas, auditorías y build. No hubo `apply` ni túneles; esta mejora
de seguridad operacional no cierra el criterio de red multinube ni suma puntos
de conectividad. El preflight real también se detuvo en la lectura del stack
AWS antes de consultar Azure, por lo que no se creó el gateway facturable. El
total provisional 11.75/20 no se recalcula.

**Estado actual de AWS Academy — 13/10/2026, 06:49 America/Chicago:** al abrir
una pestaña nueva, el laboratorio mostró `Terminated`, temporizador `00:00` y
`No running instance` (presupuesto visible $22/$50). El contador 3:58 de la
pestaña anterior estaba desactualizado. La CLI confirmó `ExpiredToken`; la
interfaz de control bloqueó la acción antes de iniciar el laboratorio. No se
hicieron cambios en AWS y el estado de la cuenta/stack permanece sin inventario
actual. El usuario deberá volver a iniciar la sesión cuando el control de
navegador esté disponible o aportar credenciales renovadas; no se asignan puntos
de despliegue por el estado local.

**Línea base local de rendimiento — 13/10/2026, 06:54 America/Chicago:**
1000 consultas de lectura a `/health` con concurrencia 50 terminaron con p95
68.34 ms y cero errores en el contenedor local. Es evidencia de smoke/load local,
no de autoscaling, throughput de transacciones ni HA cloud; no modifica el nivel
provisional de escalabilidad. Los JSON y alcance están descritos en la
[revalidación actual](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Prueba temporal de red privada AWS–Azure — 13/10/2026:** STS aceptó el token
vigente del perfil local `default`. La VPC del portal era `10.10.0.0/16` y su
tabla de rutas de aplicación coincidía con el output del stack; no había VPN
Gateway en la VPC. Azure no tenía el grupo/VNet destinados a la prueba. Los dos
tests de costo Terraform pasaron. Azure rechazó la SKU retirada `VpnGw1`; se
actualizó IaC a `VpnGw1AZ` y el test ahora comprueba explícitamente esa SKU.
El gateway Azure temporal llegó a `Succeeded` con BGP/activo-activo, pero AWS
Academy denegó `ec2:CreateCustomerGateway` mediante una SCP explícita. No se
crearon conexiones VPN AWS ni pudo probarse ningún túnel. El rollback AWS cerró
y el registro de stack se eliminó; Terraform destruyó los 9 recursos Azure y
confirmó el grupo inexistente y estado vacío. La conectividad multinube queda
pendiente de permisos AWS Academy; no se eleva el 11/20 por esta prueba fallida.
Ver evidencia y alcance en
[`REVALIDACION_ESTADO_2026-10-13.md`](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Reevaluación posterior — 13/10/2026, 10:10 America/Chicago:** el criterio 6
se mantiene en Bueno (1.125/1.5). El ASG hizo scale-out automático de 2 a 3
con CPU sintética; en una segunda observación, tras preparar manualmente el
deseado en 3, la alarma inferior redujo automáticamente la capacidad a 2 a las
10:04:19. El ALB quedó 2/2 healthy, `/health` respondió 200 y la detección de
drift terminó `IN_SYNC`. Se prueba el mecanismo de ambos sentidos, no capacidad
transaccional ni 3,000 usuarios. El criterio 9 se mantiene en Bueno (1.125/1.5):
PT-DR-01 restauró el marcador y verificó conteos iguales en 14 tablas; RTO=289 s,
RPO superior=10 s, limpieza verificada. Bajo la misma conversión interna
100/75/50/0, el total estimado actual permanece **11.75/20**. No es calificación
docente; siguen abiertas la red privada, WMS real, dominio/HTTPS y escala
empresarial. Ver [prueba de escalado](../evidence/current/aws/AWS-AUTOSCALING-2026-10-13.md),
[restore RDS](../evidence/current/aws/AWS-DR-RESTORE-2026-10-13.md) y
[estado vivo](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Revalidación de acceso AWS — 13/10/2026, 11:52 America/Chicago:** se aplicó
la nueva terna temporal al perfil `default`; el identificador coincide, no hay
credenciales `AWS_*` de entorno y STS autentica `841113066612`. Las lecturas de
VPC, EC2, ASG, ELB, RDS, VPN y CloudFormation siguen denegadas explícitamente
por `voc-cancel-cred`. No se modificó infraestructura ni se pudo confirmar su
estado actual. La VPN continúa pendiente; esta autenticación válida no demuestra
conectividad multinube, así que el total provisional **11.75/20 no se aumenta**.
Ver [corte detallado](../evidence/current/aws/AWS-REVALIDACION-STS-2026-10-13.md).

**Estado Azure observado — 13/10/2026, 12:06 America/Chicago:** la Function
continúa `Running` y `/api/health` responde HTTP 200, pero el plan real es Linux
Consumption `Y1`, con acceso público habilitado y sin integración VNet. Esto
descarta presentar el endpoint actual como privado por solo crear una VPN. La
migración a Flex/plan compatible, Private Endpoint, DNS privado y prueba desde
la VPC queda abierta. La IaC de red ahora declara la subnet delegada `/27` y
pasó validate + 2 tests, pero no se aplicó; el puntaje provisional
**11.75/20 no cambia**. La suite local de 94 tests aprobó en este corte; no
sustituye las pruebas de conectividad
ni el estado de infraestructura AWS que la política actual impide leer.
El smoke compensado de las 12:16 también volvió a pasar en Azure (venta y
recepción demo, saldo 24→23→24), pero fue originado por el proceso local y no
por EC2; por tanto no cierra la conexión privada AWS–Azure ni cambia el puntaje.

**Preparación de Flex privada y token AWS — 13/10/2026, 12:46 America/Chicago:**
STS volvió a aceptar la nueva terna temporal en `default`, pero la política
`voc-cancel-cred` denegó las lecturas de inventario AWS. El grupo Azure
`rg-tangama-private-network` no existe, por lo que no se hizo un plan ni un
apply cloud. Se añadió localmente el root blue-green
`iac/environments/azure-flex-private`, con Private Endpoint/DNS e identidad
administrada, además de una opción Route 53 acotada al FQDN de Function y una
compuerta de costo. Pasaron 3/3 tests Flex, 13 escenarios mock de preflight y
la compuerta completa con 94 pruebas, `cfn-lint`, build y Terraform. No se
recalcula: **11.75/20** continúa siendo la autoevaluación del último corte de
recursos realmente desplegados; IaC local validada no es evidencia de una VPN
ni de integración desde EC2. Véanse [estado actual](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md)
y [validación Flex](../evidence/current/azure/AZURE-FLEX-IAC-VALIDACION-2026-10-13.md).

**Revalidación AWS con token nuevo — 13/10/2026, 13:15 America/Chicago:** STS
autenticó `default` en la cuenta académica. Después de un 503 transitorio a las
13:08, el ASG reemplazó por sí solo las instancias: ahora hay 2/2 `InService` y
`Healthy`, el target group tiene 2/2 destinos sanos, y `/`, `/health` y `/ready`
responden HTTP 200; la base responde `ok`. RDS sigue Single-AZ con backup de 1
día, el ALB es HTTP-only, no hay VPN AWS y Azure continúa público. La puntuación
provisional previa no se recalcula con esta prueba de salud parcial; los
criterios de red privada multinube, recuperación/backup y HTTPS siguen abiertos.
Ver [inventario AWS](../evidence/current/aws/AWS-INVENTARIO-2026-10-13.md) y
[corte vivo](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Prueba temporal y limpieza de VPN — 13/10/2026, 14:46 America/Chicago:** el
gateway Azure llegó a `Succeeded`, pero AWS Academy denegó
`ec2:CreateCustomerGateway` por una SCP explícita. CloudFormation revirtió; se
eliminó el stack fallido y no quedaron conexiones AWS. Terraform destruyó los
10 recursos Azure temporales y el grupo dedicado ya no existe. No hubo túneles,
rutas BGP ni tráfico privado; por tanto, no suma al criterio de conectividad ni
al puntaje provisional **11.75/20**. Se corrigieron y validaron las plantillas
para una futura repetición, que depende de una autorización AWS que no puede
eludirse. Ver [evidencia de interoperabilidad](../evidence/current/azure/AZURE-AWS-INTEROP-2026-10-13.md)
y [estado revalidado](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Evaluación de alternativa Tailscale — 13/10/2026, 14:53 America/Chicago:**
AWS STS autenticó y su VPC `10.10.0.0/16` existe. Azure no lista ninguna VNet;
el servicio Tailscale local corre, pero su cliente está en `NoState`/offline.
Se prepararon una topología propuesta y un preflight local de solo lectura con
4 pruebas mock aprobadas; además, la puerta local completa aprobó 98 pruebas,
Terraform `fmt`/`validate` y cinco pruebas mock Terraform. No se registraron routers, aprobaron rutas ni cursó tráfico
privado. No suma al criterio de interconexión; la puntuación provisional sigue
en **11.75/20**. Tailscale solo podría presentarse como overlay si se demuestra
tráfico entre subredes y se confirma que el docente acepta esa sustitución;
no equivale a la VPN administrada IPsec/BGP. Ver
[diseño Tailscale](../iac/environments/aws-azure-tailscale/README.md) y
[relectura de prerequisitos](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Verificación funcional sin VPN — 13/10/2026, 15:18–15:28 America/Chicago:**
el release ERP local procesó por HTTPS público una venta y su reversa mediante
Azure Queue/Function; el ledger demo volvió 24→23→24. Alrededor de las 15:28,
AWS tenía 2/2 destinos ALB sanos, `/health` con PostgreSQL `ok` y `/ready` en
HTTP 200; Azure `/api/health` también devolvió 200. La lectura RDS de 15:15 lo
confirmó disponible, privado, Single-AZ y con un día de backups. La detección
CloudFormation de 15:30 terminó `IN_SYNC` con cero recursos drifted, aunque no
certifica Azure Terraform. Esto demuestra
el servicio de aplicación en ambas nubes, pero no convierte la prueba local en
tráfico originado en EC2 ni establece conectividad privada. El túnel queda para
el final; VPN/Tailscale no está desplegado. Se mantienen **11.75/20
provisionales**, sin reevaluación oficial ni puntos inferidos por esta prueba;
ver [E2E](../evidence/current/azure/AZURE-ERP-E2E-2026-10-13.md) y
[estado cloud](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Rúbrica final, dominio y recuperación repetida — 13/10/2026:** se verificó
la rúbrica final XLSX, distinta de la rúbrica breve del Entregable 1 en DOCX.
La final tiene 14 criterios por 20 puntos. No incluye dominio/HTTPS como
renglón separado. El criterio 5 sí pide cifrado, mínimo privilegio y controles
de red; el criterio 12 pide evidencias de pruebas de seguridad y conectividad,
entre otras. Por eso HTTPS válido fortalece esos criterios, aunque no da puntos
automáticos por sí solo. El ALB HTTP-only sigue siendo una brecha de seguridad
y de prueba. La plantilla CloudFormation ya deja listo el listener ACM opcional;
no se activa hasta controlar un dominio y completar la validación DNS.

PT-DR-01 se repitió sobre RDS: marcador y conteos verificados, RTO 289 s, RPO
superior observado 14 s y limpieza sin temporales. No se recalcula aquí la
autoevaluación provisional **11.75/20**; el puntaje docente es desconocido. Ver
[prueba DR](../evidence/current/aws/AWS-DR-RESTORE-2026-10-13.md) y
[estado AWS/Azure](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

**Seguimiento de monitoreo — 13/10/2026, 16:23 America/Chicago:** se añadieron
al tema SNS los dos destinatarios autorizados por el usuario. AWS lista dos
suscripciones confirmadas y las cinco alarmas tienen una acción SNS; no se
disparó una alerta sintética. La alarma CPU usa el intervalo real de la métrica.
La detección final de CloudFormation quedó `IN_SYNC` (cero drift), con ALB 2/2
sano y health de Azure 200. Esto cierra la configuración de notificaciones,
pero no prueba que haya ocurrido una alarma real ni mide costo. La autoevaluación
continúa en **11.75/20 provisional**; no se suman puntos sin revisar la rúbrica
completa y contar con aceptación documentada del docente sobre AWS–Azure. Véase
[el detalle](../evidence/current/aws/AWS-OBSERVABILIDAD-2026-10-13.md).

**Actualización de evidencia — 13/10/2026, 16:12 America/Chicago:** la sesión
AWS volvió a confirmar el stack, la salud del ALB (2/2 targets), RDS privado y
cifrado, y el cifrado AES256 de los dos buckets. El change set revisado modificó
solo `HighCPUAlarm` sin reemplazos; ahora usa períodos de cinco minutos y
missing-data indeterminado. La batería local llegó a 98 pruebas unitarias más
build, auditoría e IaC. Se comprobó HTTP 401 en cuatro rutas de negocio sin
sesión y health 200 en AWS/Azure. Esto mejora evidencia de monitoreo y seguridad,
pero no prueba roles autenticados, correo de alarmas, un WMS real ni conectividad
IP privada. AWS→Azure sigue funcionando por HTTPS público; VPN queda aplazada al
cierre. La nota **11.75/20 continúa siendo una autoevaluación provisional del
corte previo**, no se sube automáticamente por este cambio y requiere una
reevaluación criterio por criterio y la aceptación del docente sobre AWS–Azure.
Véase [el detalle](../evidence/current/aws/AWS-OBSERVABILIDAD-2026-10-13.md).

## Revalidación posterior al despliegue — 14/10/2026, 08:42–09:16 America/Chicago

Esta sección prevalece sobre los cortes anteriores del mismo día; las notas
11.75/20 y 15–16/20 siguen retiradas y no se infiere una nota. La rúbrica
disponible suma 18.5 puntos aunque su total impreso dice 20, y faltan
equivalencias numéricas oficiales.

| Criterio | Evidencia nueva | Estado/brecha que permanece |
|---|---|---|
| 3 · Redes VPC/VCN | VPC/ASG/ALB/RDS revalidados en AWS; servicio Azure activo. | No se desplegó VNet/ruta/VPN privada AWS–Azure; AWS Academy denegó `CreateCustomerGateway` en el intento temporal. |
| 4 · Cómputo, almacenamiento y BD | AWS v9 2/2 saludable; Function Azure renovada; RDS disponible, cifrada y privada. | RDS sigue Single-AZ y backups de un día; ledger WMS es ficticio. |
| 5 · Seguridad | Hardening v9 desplegado: sin campos de host/DB en endpoints públicos, `/metrics` 404, admin API anónima 401; login admin exige cambio de contraseña. | No se completó aún ese cambio ni la prueba de cada rol autenticado en navegador; ALB aún HTTP. |
| 8 · IaC | CloudFormation del template local aplicado, `UPDATE_COMPLETE` y drift `IN_SYNC`; Terraform Azure después del paquete terminó `No changes`. | Esos resultados certifican los recursos administrados en este corte, no dominio/HTTPS ni recursos de red privada no desplegados. |
| 10 · Multinube | Function Azure actualizada y smoke compensado pasó con Queue/Function; Azure conserva eventos sintéticos. | Ese productor fue local/SQLite, no EC2. El test productivo se bloqueó intencionalmente en HTTP 428 de cambio obligatorio; no se reporta tráfico privado ni WMS real. |
| 12 · Pruebas | Compuerta local 140 pruebas Python y 8 Node, build/auditorías/IaC; AWS post-deploy endpoints/SSM; Azure post-deploy E2E. | Falta cerrar acceso autenticado por rol, E2E iniciado desde AWS tras cambiar la contraseña, alarma Azure real y WebRTC entre dos navegadores. |
| 13 · Documentación | Evidencia AWS, Azure, seguridad y corte cloud actualizados con hashes, estados y límites. | No se archivaron capturas de consola en este corte; el usuario indicó que recogerá esas evidencias. |

El reporte pormenorizado está en [revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md), [release AWS](../evidence/current/aws/AWS-DESPLIEGUE-2026-10-14.md) y [E2E Azure](../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md). El cambio de contraseña admin queda pendiente de decisión del usuario antes de cualquier alteración de esa credencial.

## Revalidación adicional — 14/10/2026, 09:20–09:24 America/Chicago

AWS permaneció `UPDATE_COMPLETE`, con 2/2 destinos sanos, RDS disponible y
probes del ALB `200/200/200/200/404/401` para portada, health, readiness, API,
metrics y administración anónima, respectivamente. Azure health devolvió 200 y
Terraform terminó `No changes`. La Action Group Azure mantiene dos receptores
habilitados; el endpoint de prueba oficial de alertas no funciona con la
suscripción gratuita. No se modificó infraestructura. Véase el detalle en la
[revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

## Actualización posterior: credenciales, roles y transacciones QA — 14/10/2026, 10:18 America/Chicago

Esta actualización sustituye los estados anteriores que decían que el cambio de
clave/admin y el E2E productivo seguían pendientes. El login admin ya no fuerza
cambio de clave; las tres cuentas QA están en Parameter Store `SecureString`.
Autorización autenticada por API/rutas protegidas: admin 200 en consola y ERP;
Comercial 200 en ventas y 403 en administración/operaciones; Operaciones 200 en
WMS/outbox y 403 en ventas/admin. No equivale a una inspección visual del
navegador.

Se verificó el recorrido productivo desde el portal AWS/RDS a Azure Queue/Function
con tres ventas y una recepción sintéticas. Los estados fueron
`completed_demo`/`received_demo`; 7/7 eventos outbox están `delivered`, con seis
documentos financieros demo. Los saldos ficticios terminaron en su línea base
18/24/40. Esto cubre integración de aplicación entre nubes por HTTPS público,
no VPN privada ni un WMS comercial. Sigue pendiente HTTPS confiable del portal,
VPN (diferida), WebRTC entre dos navegadores y captura visual de roles.

## Relectura de nube/IaC — 14/10/2026, 10:37 America/Chicago

AWS permanece `UPDATE_COMPLETE`, deriva reportada `IN_SYNC`, ALB `/health=200`,
2/2 targets sanos y RDS `available`/cifrada/privada. La configuración real sigue
Single-AZ con 1 día de backup, por lo que el criterio de resiliencia conserva
esa brecha. Azure Function `Running` y health 200; el Terraform activo concluyó
`No changes` sin `apply`. Ver
[el corte actualizado](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

## Mejora local posterior — catálogo sintético, 14/10/2026

Se incorporaron doce SKU ficticios y la carga de hasta 500 filas desde Excel
(edición de plantilla `.xlsx`, guardado como CSV UTF-8, vista previa e
importación validada) al módulo ERP. Azure conserva la autoridad del ledger
sintético: una ficha existente no reemplaza su saldo y los SKU nuevos reciben
su saldo inicial. Las pruebas verifican que los nuevos códigos puedan recorrer
ventas y que una entrega duplicada no repita el movimiento. Esto mejora la
demostración del proceso de negocio; no afirma inventario físico, WMS comercial,
ni un despliegue de esta revisión. El candidato AWS v10 aún no está publicado,
y esta mejora local no recalcula ni modifica la autoevaluación de la rúbrica.
Ver [evidencia de la importación](../evidence/current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md).

## Estado posterior al despliegue, E2E y microcarga — 14/10/2026, 12:17 America/Chicago

La frase anterior sobre el candidato v10 era correcta al corte local, pero quedó
superada por el despliegue completado después. AWS v10 y el paquete Azure
`364cf88c…` están publicados; ambos pasaron las comprobaciones de salud y
reconciliación descritas en [la evidencia de despliegue](../evidence/current/DEPLOY-CATALOGO-SINTETICO-2026-10-14.md).
Esta actualización no modifica el puntaje autoestimado de la matriz. El E2E
portal AWS v10/base de datos/outbox → Azure se repitió dos veces con venta y
recepción sintéticas y saldo reconciliado. Una microcarga adicional ejecutó 24
lecturas autenticadas en una EC2, concurrencia 6, p95 304 ms y 24/24 HTTP 200;
no atravesó el ALB ni prueba escalado a 3,000 usuarios. Falta la importación CSV
desde navegador autenticado, además de VPN privada, HTTPS de dominio y WebRTC
entre dos navegadores. La reconciliación IaC vigente es AWS `IN_SYNC` y Azure
Terraform `No changes`.

## Revalidación posterior — 14/10/2026, 12:25–12:34 America/Chicago

La sonda pública de las 12:25 contradice la disponibilidad descrita arriba:
AWS ALB devolvió 503 en portada y `/health`. STS autenticó, pero
`cloudformation:DescribeStacks` y `ssm:DescribeInstanceInformation` quedaron
denegados por `voc-cancel-cred`; no se afirma estado actual de stack, targets,
EC2 o RDS. Azure health respondió 200. Entre 12:30 y 12:32, el smoke vivo
Azure confirmó Function `Running`/HTTPS-only, guards 401/400, poison metadata
en cero y venta/recepción compensatoria con saldo demo restaurado; el productor
fue local/SQLite, no AWS. El detalle está en la
[revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md) y el
[E2E Azure](../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md).

El parser y el backend de importación pasaron 6 y 5 pruebas focalizadas; aún
falta el recorrido visual del CSV. El control del navegador no pudo verificar
la URL activa, así que no se navegó AWS Academy. Próximo paso para AWS: recuperar
una sesión de consola autorizada o permisos de lectura suficientes, diagnosticar
el 503 sin crear una pila paralela y repetir las pruebas de roles e integración
portal→RDS→Azure. La matriz no asigna nota numérica: pesos publicados suman 18.5,
no 20, y el docente debe aclarar escala/ponderación.

En el corte local también pasaron 2/2 pruebas dirigidas de consola y autorización
del release AWS, que cubren seis roles y sus rutas/API protegidas sobre bases
aisladas; no sustituyen el smoke de roles en la nube ni la inspección visual.

## Actualización de QA local — 14/10/2026, 12:42–12:44 America/Chicago

La compuerta integral repetida sobre el árbol actual aprobó 155 pruebas Python,
8 Node, PT-PERF-02 (40 transacciones aisladas), build Vite, auditorías de
dependencias, validación CloudFormation y Terraform, más pruebas mock para VPN,
red privada Azure y guardas de recuperación. No aplicó infraestructura ni
actualiza el puntaje autoestimado. En el chequeo cloud de las 12:46, AWS STS
autenticó pero `elbv2:DescribeLoadBalancers` fue denegado y el ALB siguió en
503; Azure health respondió 200. Evidencia detallada en
[`QA-LOCAL-2026-10-14.md`](../evidence/current/QA-LOCAL-2026-10-14.md) y
[`CLOUD-REVALIDATION-2026-10-14.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

## Gate ampliado de CSV — 14/10/2026, 12:56 America/Chicago

La puerta integral ahora ejecuta también `pnpm run test:csv`, evitando que las
pruebas existentes de importación queden fuera del comando de QA estándar. La
repetición aprobó 155 pruebas Python y 14 Node (8 de permisos, 6 de CSV), además
de build, auditorías, validación IaC y gates mock. No prueba la interfaz
autenticada ni cambia el estado cloud; el ALB seguía en 503 y Azure health dio
200 en el chequeo de las 12:46. Véase la evidencia de
[QA local](../evidence/current/QA-LOCAL-2026-10-14.md).

## Smoke HTTP local — 14/10/2026, 13:00 America/Chicago

Los puertos locales 8080 y 8081 devolvieron `GET /` HTTP 200 con título
`Tangamandapio Cloud` y `GET /health` HTTP 200 (`status=ok`). Fue una lectura
anónima; confirma disponibilidad de ambos servidores locales, no el ingreso,
los módulos protegidos ni el flujo CSV visual.

El workflow de GitHub también quedó configurado para ejecutar navegación por
rol (8 tests) e importación CSV (6 tests) antes del build. YAML y suites se
validaron localmente; el workflow remoto aún no se ejecutó porque no se publicó
ningún commit.
