# Autoevaluación de cierre — propuesta cloud Tangamandapio

**Corte:** 08/10/2026. **Uso:** revisión interna; no sustituye la calificación
del docente ni una prueba de sustentación.

## Auditoría adicional de fuentes — 16/10/2026

Se cotejaron directamente la hoja específica `rúbrica proyecto_qod3szrctm (3).xlsx`
y el PDF general `rúbrica de evaluacion de proyecto de fin de ciclo_llss4pnf0z.pdf`
que están en Descargas. Las cuatro copias XLSX tienen SHA-256 idéntico. Sus 14
máximos suman 18.5, aunque la celda TOTAL imprime 20. El PDF general organiza
otros bloques (diseño de red, virtualización, servicios TI, cloud,
documentación y defensa); sus máximos visibles por bloque suman 90. No es la
misma escala ni explica los 1.5 puntos que faltan en la rúbrica de nube.

No se normalizan los pesos ni se combinan ambas escalas. Por ahora la evaluación
es cualitativa y ligada a evidencia; el docente debe confirmar cuál instrumento
aplica y cómo pondera el máximo anunciado. Los hashes y el cotejo están en la
[evidencia de nube y fuentes de rúbrica](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0341UTC.md).

## Revalidación cloud — 13/10/2026, 23:50 America/Chicago

AWS STS autenticó; CloudFormation seguía `UPDATE_COMPLETE`, el ALB tenía 2/2
destinos `healthy` y RDS estaba disponible, cifrada, Single-AZ y con un día de
backup. El portal local respondió `/health` y `/ready` con HTTP 200. En Azure,
el grupo `rg-tangamandapio-rebuild-wus` figuró `Succeeded`, la Function
`tangama-wms-261008` `Running`/HTTPS-only y `/api/health` respondió 200. Azure
CLI sí está instalado, pero fuera del `PATH` de PowerShell; la lectura previa
que lo declaró no disponible fue incompleta. No se modificaron recursos.

La cifra **11.75/20** y el rango **15–16/20** quedan retirados: ninguno es una
nota defendible. La rúbrica fuente suma 18.5 puntos en sus 14 criterios, aunque
imprime 20, y no asigna equivalencias numéricas a sus descriptores. El 11.75
usó una conversión porcentual inventada; el 15–16 no se sustentó con una
evaluación numérica criterio por criterio. **No se penaliza que el laboratorio
esté apagado en el escenario hipotético**, pero levantar la infraestructura no
cierra por sí solo las pruebas o funciones faltantes. Hasta que el docente
aclare el total y la escala, la valoración actual debe ser cualitativa, no una
nota ni un rango numérico.

La tabla posterior de 11.00/20 se conserva solo como transcripción histórica de
un corte anterior; no debe reutilizarse como calificación. La matriz cualitativa
y las brechas vigentes están en
[`04_matriz_rubrica.md`](04_matriz_rubrica.md). Evidencia detallada en la
[revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-13.md), el
[inventario AWS](../evidence/current/aws/AWS-INVENTARIO-2026-10-13.md) y la
[revisión local](../evidence/current/LOCAL-LIVE-RECHECK-2026-10-13.md).

Como antecedentes (no estado vigente), consulta
[AZURE-RECONSTRUCCION-2026-10-12.md](../evidence/current/azure/AZURE-RECONSTRUCCION-2026-10-12.md)
y el [mapa histórico 08/10](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md).

## Alcance de la comparación

El análisis inicial contrastó la plantilla del proyecto, la descripción del
proyecto y la rúbrica específica de 14 criterios. La auditoría del 16/10 añadió
el PDF general descrito arriba, que es un instrumento distinto. La descripción
y plantilla escritas mencionan expresamente AWS + OCI, incluyendo
VPC/VCN; el alumno reporta que el docente confirmó presencialmente AWS + Azure,
sin OCI. La confirmación no está respaldada por escrito en el repositorio; debe
explicarse en el informe y anexarse si está disponible. No se inventa una VCN:
el criterio de redes aún requiere VNet/VPN demostrable.

La carpeta `deliverables/` contiene varios **Entregables 1** y también
`Proyecto_Final_Cloud_Tangamandapio_AWS_Azure.docx`. Este último sí es un
informe final consolidado, pero su corte es 08/10/2026 (fecha de informe
09/10/2026) y por eso no incorpora la reconstrucción Azure del 12/10 ni su
inventario y prueba viva. El archivo `ZUNIGA_JOSE_EXAMEN_CLOUD.docx` describe
un ejercicio separado de EC2, VPC y S3. No se presenta ese examen como informe
final de la arquitectura AWS–Azure.

## Cómo se estiman los puntos

La revisión anterior probó una conversión de **100% / 75% / 50% / 0%** por
nivel y contó “No evaluable” como cero; la rúbrica no confirma esa fórmula.
Tanto 11.00/20 como 11.75/20 son transcripciones históricas de cálculos
inválidos, y 15–16/20 fue una proyección no sustentada. No se debe inferir que
faltan 8.25 puntos ni presentar esos valores como nota. El estado apagado no
resta en el escenario hipotético; la matriz actual indica qué evidencia falta
para los descriptores. El alumno reporta aceptación presencial de AWS–Azure:
debe describirse el E2E HTTPS demostrado por separado de la red privada
VPC/VNet/VPN, que aún no está probada.

## Tabla histórica de la revisión no oficial — corte 08/10/2026

Los niveles y valores de abajo preservan el borrador anterior, que asignó una
conversión porcentual no indicada por el docente. Se mantienen como registro de
auditoría, no como evaluación vigente. Para brechas actuales usar la matriz
cualitativa enlazada arriba.

| # | Criterio y máximo | Nivel / estimación | Evidencia y brecha determinante |
|---:|---|---:|---|
| 1 | Análisis del problema y requerimientos · 1.0 | Excelente · **1.00** | El caso ficticio, problema central, usuarios, restricciones y requisitos funcionales/no funcionales están descritos en el Entregable 1 y el registro maestro. Mantener trazabilidad requisito→prueba en el informe final. |
| 2 | Diseño de arquitectura cloud · 2.0 | Bueno · **1.50** | Hay diagramas y separación coherente: AWS transaccional; Azure procesa el WMS asincrónico. Falta consolidar el diagrama final con estados real/objetivo y sin componentes no desplegados. |
| 3 | Redes VPC/VCN · 2.0 | En proceso · **1.00** | La VPC AWS segmentada, rutas, gateways y puertos están en IaC/evidencia histórica; no hay VCN OCI ni VNet Azure integrada. El alumno reporta aceptación oral de AWS–Azure, pero la red Azure y la conexión privada siguen pendientes. |
| 4 | Cómputo, almacenamiento y BD · 1.5 | Bueno · **1.125** | EC2/ALB/ASG, RDS y S3 AWS, más Function, Queue y Blob Azure. Azure verificó `/api/health` 200 y KQL registró 6 invocaciones del trigger de Queue con 0 fallos observados; esto no convierte el ledger en inventario comercial ni revalida AWS. |
| 5 | Seguridad cloud · 2.5 | En proceso · **1.25** | El diseño/código incorpora RBAC, SG, DB privada, WAF, secretos y controles de Blob/Queue. Azure exige HTTPS, tiene Blob privado y autenticación FTP/SCM básica apagada. La limitación persistida de intentos de login ya existe en ambas variantes del portal y está cubierta por pruebas locales; siguen pendientes dominio HTTPS confiable, cookie Secure, MFA/identidad corporativa, roles actuales en AWS y red privada Azure. La estimación 1.25 corresponde al corte provisional y no se recalcula con este cambio aislado. |
| 6 | Alta disponibilidad y escalabilidad · 1.5 | En proceso · **0.75** | Evidencia histórica: ALB/ASG en dos AZ y una terminación controlada repuso dos nodos con health `ok`. El 13/10 se midió en Docker local `/health` con 1000 solicitudes y concurrencia 50 (p95 68.34 ms, cero errores); no es carga transaccional ni demuestra escalado del ASG. Faltan prueba de escala bajo carga en nube y RTO medido; puntaje provisional no recalculado. |
| 7 | Monitoreo y observabilidad · 1.0 | En proceso · **0.50** | KQL en Application Insights confirma actividad reciente: 6 ejecuciones de `process_fulfillment_message` y 0 fallos observados en las últimas 48 h. La enumeración actual de Azure Queue solo muestra la cola primaria, no una poison queue; queda sin demostrar cómo alertar/recuperar poison futuro. El Action Group sigue sin receptores y faltan captura del dashboard y prueba de recuperación. |
| 8 | Infrastructure as Code · 1.5 | Bueno · **1.125** | CloudFormation AWS y Terraform Azure están organizados. El 12/10 Terraform creó el entorno Azure desde state vacío y el plan posterior quedó sin drift; AWS no se revalidó en este corte. Los states locales no se versionan. |
| 9 | Backup, RTO/RPO y recuperación · 1.5 | En proceso · **0.75** | Una copia RDS PITR temporal se restauró y validó con una lectura de 10 tablas; la copia se eliminó. Falta medir y acordar formalmente RTO/RPO, así que no se marca como cerrado. |
| 10 | Arquitectura AWS–OCI / multicloud · 1.5 | En proceso · **0.75** | El alumno reporta aprobación oral para AWS + Azure, aunque el XLSX nombra OCI. El 13/10 el artefacto AWS desplegado en EC2 completó outbox→Azure Queue/Function y una recepción compensatoria en SQLite temporal; el stock demo volvió al baseline. No se demuestra VPC/VNet/VPN y OCI no se presenta como implementado. |
| 11 | Costos y optimización · 0.5 | En proceso · **0.25** | Hay recomendaciones de apagar/limpiar y controlar el laboratorio; falta una estimación mensual reproducible, supuestos de tráfico/retención y comparación de alternativas/costo real. |
| 12 | Pruebas técnicas · 1.0 | Bueno · **0.75** | La puerta local aprobó 79 pruebas en el corte informado. El 13/10 el artefacto desplegado en EC2 pasó un E2E outbox→Azure Queue/Function→reconciliación, con compensación y stock 24→23→24; el estado del evento fue correlacionable. Faltan escala/alarma, restauración con integridad/RTO-RPO, roles productivos en navegador y pruebas A/V reales. |
| 13 | Documentación técnica · 0.5 | En proceso · **0.25** | Existe un informe final consolidado, con diagramas, matriz de pruebas y anexos; quedó fechado al corte 08/10. El memo Azure del 12/10 está actualizado, pero falta integrarlo al DOCX final, capturar inventario/monitor desde los portales y resolver la discrepancia AWS–OCI frente a AWS–Azure con constancia docente si está disponible. |
| 14 | Sustentación y defensa técnica · 0.5 | No evaluable · **0.00** | No se puede inferir dominio oral desde el repositorio. Requiere demo en vivo y explicar decisiones, costos, fallos y límites. |
|  | **Total** | **11.00 / 20** | Estimación interna bajo la conversión indicada, no nota docente. |

## Validaciones de la revisión 08/10 (histórico)

- **Unitarias:** `app/tests` 22/22; `app/azure_function_tests` 14/14;
  `app/aws_release/tests` 23/23. La suite AWS tarda cerca de 96 s por el costo
  deliberado del hashing de contraseñas. La puerta local ahora agrega auditorías
  de dependencias y build seguro aislado.
- **Frontend/seguridad:** `pnpm run build:check` terminó en `app/web/dist` sin
  reemplazar `app/src/static`. La auditoría reportó 0 vulnerabilidades altas o
  críticas en dependencias frontend de producción; se actualizó `source-map-js`
  1.2.1→1.2.2. `pip-audit` no halló vulnerabilidades conocidas en el lock Python
  con hashes, que consolida los tres manifiestos de ejecución y herramientas CI.
- **IaC:** `terraform fmt`/`validate` pasaron en `demo` y `azure-demo`; `cfn-lint`
  pasó en las dos plantillas AWS. `init` usó lockfile de solo lectura. No se hizo
  `apply` ni se creó ningún recurso.
- **Última observación cloud documentada (21:26 UTC, no reconsultada en esta
  tarea):** CloudFormation `UPDATE_COMPLETE`, drift `IN_SYNC`, 2 destinos sanos;
  RDS privado/Multi-AZ/cifrado/7 días y PITR temporal validado. Azure aceptó un
  pedido sintético y el ledger demo fue idempotente. `AUTO_DISPATCH_EVENTS=true`
  quedó activo, pero no hay evidencia de un nuevo pedido después del cambio.
  Quedó documentado un mensaje poison histórico en una revisión anterior; la
  enumeración Azure actual solo encontró `fulfillment-events`, por lo que debe
  reconciliarse la ubicación/estado de aquel mensaje antes de sustentar. La
  bitácora no es estado permanente.
- **Documento:** se pudieron leer los DOCX y XLSX fuente, pero la máquina no
  tiene LibreOffice (`soffice`) para renderizar páginas. Ningún DOCX original
  fue editado ni se afirma revisión visual de su maquetación.

## Qué falta para cerrar la sustentación

1. Reflejar al inicio del informe final que, según el alumno, el docente aceptó
   presencialmente AWS–Azure frente al texto AWS–OCI; anexar constancia escrita
   si está disponible.
2. Crear el **informe final** (no reutilizar un Entregable 1 como si fuera el
   final): arquitectura final, inventario probado, seguridad, escalabilidad,
   integración, costos, RTO/RPO, pruebas con resultados y referencias.
3. Azure se revalidó el 12/10 y quedó sin drift. Al corte predespliegue 00:22
   el lab no tenía recursos de aplicación; desde el corte 01:14 AWS tiene el
   stack activo, dos instancias sanas y RDS conectado (ver evidencia AWS
   13/10). Antes de reconstruir de nuevo, mantener el flujo bootstrap y revisar
   el change set para que no reemplace la base ni elimine el snapshot.
4. La ruta ERP local→Azure ya pasó un ciclo de venta y recepción compensatoria;
   probar ahora pedido y correlación originados por la instancia AWS. Aclarar
   la ubicación del poison histórico antes de cualquier acción y documentar la
   política de poison futuro sin reencolar mensajes a ciegas. El ledger sigue
   siendo ficticio, no un WMS empresarial.
5. Medir RTO/RPO y demostrar alarma/recovery y escala del ASG en una ventana y
   presupuesto controlados; la restauración PITR aislada sí se probó.
6. Completar prueba de micrófono/cámara bidireccional en dos navegadores/redes;
   probar permisos y cierre sin almacenar una llamada sin consentimiento.
7. Capturar inventario AWS y monitor Azure desde consola/Chrome en PNG directo;
   la evidencia del 12/10 es registro CLI/HTTP, no screenshot. Redactar
   información personal y vincular cada imagen a una prueba.
8. Al final, cerrar dominio propio, certificado ACM confiable, redirección,
   cookie `Secure`, accesibilidad y verificación final de costos.

## Actualización de evidencia Azure — 12/10/2026

Azure for Students aparece `Enabled`, sin consulta del saldo. Se aplicaron 14
recursos; el inventario del grupo mostró 10 recursos superiores; el plan
posterior no encontró drift. La Function responde `Running`/HTTPS. La prueba
viva verificó `401` sin clave, `400` para productor ajeno, `202 queued`,
`202 queued_duplicate` y `demo_fulfillment_completed`; el stock ficticio pasó
25→24 una sola vez. Otra prueba viva recorrió ERP local→outbox→Azure Queue/Function
y reconciliación, seguida por una recepción que restauró el stock a su valor
inicial. Consulta KQL a Application Insights (últimas 48 h) mostró 6 ejecuciones
del trigger `process_fulfillment_message`, 0 fallos observados, además de 7
recepciones de eventos y 21 consultas de estado, también sin fallos observados.
Hay dos alertas, pero el Action Group no tiene destinatarios. AWS no
se revalidó ni originó un evento en esta ejecución. El detalle está en
[`AZURE-RECONSTRUCCION-2026-10-12.md`](../evidence/current/azure/AZURE-RECONSTRUCCION-2026-10-12.md).
La consulta de Cost Management aún no produjo una cifra: consumo devolvió
`pretaxCost=None` y la API de consulta rechazó la definición usada. No afirmar
saldo suficiente ni costo cero hasta verificar Cost Analysis en el portal.
Esta prueba no basta para subir el puntaje conservador **11.00/20** sin cerrar
red, integración AWS→Azure y recuperación/observabilidad.

### Corte previo al despliegue — 13/10/2026, 00:22 America/Chicago

AWS STS aceptó las credenciales nuevas. La prueba de recuperación aislada
restauró el snapshot PostgreSQL cifrado, cambió la clave maestra a gestión de
RDS/Secrets Manager después de restaurar y borró la instancia temporal y su
subnet group. El snapshot fuente sigue disponible; no se consultaron tablas ni
se midió RTO/RPO. El inventario posterior mostró cero recursos de aplicación
EC2/ALB/RDS. Azure health respondió HTTP 200, pero el estado `Running` de la
Function no se revalidó hoy; la falta de VNet/VPN procede del corte del 12/10.
La puerta local aprobó 79 pruebas, auditorías Python/frontend, build frontend,
CloudFormation y Terraform format/validate. Se mantiene la autoevaluación
provisional conservadora **11.00/20**: la restauración técnica no demuestra
integridad de datos, operación del portal restaurado, red privada ni RTO/RPO.

### Revalidación posterior — 13/10/2026, 01:14 America/Chicago

Tras recibir la sesión nueva, AWS STS autenticó con `default`. El stack
`tangamandapio-live-20261013` quedó `UPDATE_COMPLETE` y CloudFormation drift
`IN_SYNC`. El ALB devolvió HTTP 200 en `/` y `/health`; dos instancias
`t3.micro`, distribuidas entre dos zonas, quedaron sanas. Sondas directas en
ambas devolvieron `/health` y `/ready` con PostgreSQL `ok`. RDS está privado,
cifrado, Single-AZ, con una retención de backup de un día y secreto maestro
administrado `active`. El change set final no reemplazó la base ni ejecutó
acciones de eliminación. Evidencia: [`AWS-DESPLIEGUE-2026-10-13.md`](../evidence/current/aws/AWS-DESPLIEGUE-2026-10-13.md).

Este nuevo corte mejora la evidencia de cómputo/BD, disponibilidad básica e
IaC aplicada, pero **no se recalculó el total de 11.00/20**. Aún no prueba
escalado por carga ni failover RDS. Además, una lectura autenticada del catálogo
Azure iniciada desde EC2 devolvió 401 con la clave vigente de AWS; la integración
AWS→Azure y su red privada no están aprobadas. Siguen pendientes roles en
navegador, integridad/RTO/RPO de restauración, HTTPS propio y sustentación. No
reportar la estimación anterior como nota actualizada hasta revisar criterio
por criterio con la rúbrica y pruebas nuevas.

Los archivos de especificación y rúbrica originales son fuentes de evaluación,
no autorizaciones para desplegar recursos. La matriz breve está en
[`04_matriz_rubrica.md`](04_matriz_rubrica.md); el estado de evidencia se
mantiene en [`evidence/README.md`](../evidence/README.md).

### Corte local posterior — 13/10/2026, 03:39 America/Chicago

Se cerró una brecha de integridad de auditoría en la administración: las
mutaciones críticas ahora comparten transacción con su evento de auditoría, y
un fallo de auditoría revierte el alta. La regresión pasó en el portal local y
en el artefacto release. La compuerta completa quedó en 81 pruebas aprobadas;
además, los 7 tests ERP específicos del release también pasaron. Build,
auditorías e IaC estáticos pasaron sin `apply`; el stack local se reconstruyó y
quedó sano preservando datos. La publicación AWS sigue sin confirmación: a las
03:19 AWS STS autenticó, pero la política `voc-cancel-cred` denegó inventario y
el ALB no resolvió por DNS. Por ello, no se suman puntos de despliegue a la
autoevaluación anterior **11.00/20** ni se la considera una calificación actual.

### E2E Azure posterior — 13/10/2026, 03:54 America/Chicago

El release ERP ejecutado localmente procesó en la Function viva una venta
sintética y su compensación mediante Queue; los resultados persistidos fueron
`demo_fulfillment_completed`/`demo_restock_completed` y el ledger regresó
24→23→24. Esto fortalece la evidencia de procesamiento Azure, pero no prueba
que el evento se originara desde AWS ni una red privada. No se recalcula la nota
provisional; véase [la evidencia del E2E](../evidence/current/azure/AZURE-ERP-E2E-2026-10-13.md).

### Release Azure y revalidación AWS — 13/10/2026, 04:37 America/Chicago

El empaquetador Azure quedó reproducible; dos builds independientes dieron el
mismo SHA-256. La compuerta completa pasó 81 pruebas, incluyendo 21 de Azure
Functions. Se aplicó un plan Terraform limitado al nuevo Blob content-addressed
y al cambio de configuración de la Function; la Function quedó `Running`,
`httpsOnly=true`, health `ok`, y el plan posterior indicó `No changes`. El E2E
posterior procesó venta y recepción compensatoria, dejó el ledger ficticio en
24 unidades y persistió ambos resultados. Esto demuestra la Function Azure
publicada con el release actual, pero el productor fue el ERP local, no EC2;
no acredita la red privada AWS–Azure ni un WMS real. Véase
[la evidencia de publicación y prueba](../evidence/current/azure/AZURE-PLAN-PAQUETE-2026-10-13.md).

La terna actualizada de AWS quedó en el perfil local `default` y STS autenticó,
pero `ListStacks`, `DescribeInstances`, `DescribeLoadBalancers` y
`DescribeDBInstances` recibieron denegación explícita de `voc-cancel-cred`.
No se revalidó inventario ni se modificó AWS. Por este límite, no asigno puntos
nuevos a cómputo AWS, multinube privada o recuperación. Se conserva 11.00/20
solo como autoevaluación documental anterior; la nota actual requiere revisar
los 14 criterios con la rúbrica oficial, las nuevas pruebas y el estado AWS
después de recuperar permisos. Detalle: [revalidación AWS](../evidence/current/aws/AWS-REVALIDACION-STS-2026-10-13.md).

### Seguimiento de autenticación y health — 13/10/2026, 04:53 America/Chicago

La última terna AWS entregada está presente en el perfil local `default` (sin
registrar sus valores), pero STS rechazó la autenticación. No se inspeccionó la
consola AWS Academy ni se modificó infraestructura; el estado de los recursos
AWS no puede afirmarse. En Azure, la suscripción respondió `Enabled` y la URL
HTTPS de salud de la Function devolvió HTTP 200; la consulta ARM no terminó, así
que esto no es inventario completo ni prueba de VPN. La compuerta local volvió a
aprobar 81 pruebas y las validaciones de IaC, pero no sustituye las pruebas
cloud faltantes. Se ajustó localmente PT-DR-01 para medir RTO desde el inicio
del restore y desactivar/verificar backups automáticos adicionales en la copia
temporal; la puerta aprobó esas guardas, pero no se ejecutó el restore SQL vivo.
La autoevaluación **11.00/20** sigue histórica y no se
recalcula en este corte. Evidencia: [revalidación 04:53](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

### Preflight VPN fortalecido — 13/10/2026, 05:07 America/Chicago

El wrapper de despliegue ahora comprueba CIDR de ambas redes, route table de
app, subnet del gateway y existencia/estado/parámetros del stack; ante errores
de lectura falla cerrado y no inicia `cloudformation deploy`. Cuatro pruebas
mock pasaron, incluida una actualización solo con aprobación explícita. Esto
mejora seguridad del IaC, pero no demuestra que la VPN exista, que sus túneles
estén `UP`, ni que haya rutas en ambas nubes. AWS STS sigue rechazando la terna;
la nota 11.00/20 permanece histórica y no se recalcula.

### Revalidación de credenciales y pruebas — 13/10/2026, 05:23 America/Chicago

El perfil `default` fue reemplazado con la terna exacta entregada en este turno;
`aws configure list` confirmó el origen compartido y STS devolvió
`ExpiredToken`. No hubo operaciones mutantes ni inventario confirmado. El
preflight VPN pasó siete escenarios mock, incluida la validación exacta de la
tabla de aplicación y ASN Azure. El health HTTPS de Azure dio 200, pero
`az functionapp show` agotó 30 segundos antes de recuperar la clave o enviar
eventos; el smoke vivo no se completó ni mutó el ledger. La puerta con
`-ValidateTerraform` pasó 83 pruebas, auditorías de dependencias, build
frontend, CloudFormation, Terraform fmt/init/validate y dos pruebas mock del
gate de costo. Esto aumenta evidencia de calidad local, no de
despliegue/conectividad; la puntuación 11.00/20 sigue siendo histórica y sin
recalcular.

### Asociación de IP públicas VPN — 13/10/2026, 05:28 America/Chicago

El preflight también valida que las dos IP públicas consultadas son las
asociadas realmente al gateway Azure; un octavo escenario mock verifica el
bloqueo de asociaciones incorrectas. La puerta con Terraform pasó 83 pruebas,
dos tests del gate de costo, lint/build y validaciones IaC. No se desplegaron
túneles ni rutas. Esta mejora de seguridad del preflight no acredita puntos de
conectividad y no cambia el 11.00/20 histórico.

### Reevaluación posterior — 13/10/2026, 09:30 America/Chicago

La prueba de escala en AWS llevó el ASG de 2 a 3 instancias cuando la CPU media
superó el umbral de 60%. Los tres destinos llegaron a `healthy` y el ALB siguió
respondiendo HTTP 200. Al detener la carga, la CPU cayó a ~1%, pero la alarma
inferior permaneció en `OK`; se restauró manualmente el deseado a 2. En la
lectura inicial había una instancia en drenaje; la comprobación posterior
confirmó dos instancias y dos destinos sanos. Esto acredita
scale-out automático, no scale-in automático ni capacidad para 3,000 usuarios.
El detalle está en [la evidencia de escalado](../evidence/current/aws/AWS-AUTOSCALING-2026-10-13.md).

La reevaluación cambia el criterio 6 a Bueno (1.125/1.5) por el scale-out
medido, manteniendo la limitación de que fue carga sintética de CPU. El criterio
9 pasa a Bueno (1.125/1.5): restore con marcador SQL, conteos idénticos en 14
tablas, RTO de 289 s, RPO superior de 10 s y limpieza comprobada. Bajo la misma
conversión interna usada arriba, la cifra previa era **11.75/20**; queda
retirada hasta validar los pesos oficiales. Persisten VPN privada, un WMS real,
TLS de dominio, scale-in
automático y escala de negocio. La matriz vigente está en
[`04_matriz_rubrica.md`](04_matriz_rubrica.md); el registro detallado está en
[`REVALIDACION_ESTADO_2026-10-13.md`](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).

### Cierre de prueba automática del ASG — 13/10/2026, 10:10 America/Chicago

La verificación posterior completa la prueba de escalado: el scale-out 2→3 fue
automático por CPU sintética. Para comprobar scale-in sin dejar el ASG por
encima de su mínimo, se elevó manualmente el deseado a 3; vencido el cooldown,
la alarma inferior de Target Tracking redujo automáticamente el deseado de 3 a
2 a las 10:04:19. El drenaje terminó, quedaron dos instancias y dos destinos
`healthy`, `/health` devolvió 200 y CloudFormation terminó `IN_SYNC`. El
criterio 6 permanece en Bueno (1.125/1.5): mecanismo probado, pero no carga
transaccional, recuperación por fallo de AZ ni soporte a 3,000 usuarios. La
cifra previa 11.75/20 queda retirada hasta validar pesos y conversión contra la
rúbrica fuente. Ver [evidencia del ASG](../evidence/current/aws/AWS-AUTOSCALING-2026-10-13.md)
y [revalidación a las 10:10](../evidence/current/REVALIDACION_ESTADO_2026-10-13.md).
