# Registro maestro — núcleo vigente

**Proyecto:** Diseño e implementación de un centro de datos cloud empresarial para Tangamandapio S.A.C.  
**Alumno:** Jose Dario Zuñiga Medina — 202310610  
**Docente:** Fernando Manuel Asin Gomez  
**Corte:** 16/10/2026, 07:03 UTC — AWS/Azure revalidados; E2E integrado y puerta local aprobados

## 1. Caso y objetivo

Tangamandapio S.A.C. es una empresa ficticia peruana de distribución mayorista, retail omnicanal y logística regional. Cuenta con 450 colaboradores, sedes/centros de distribución en Lima, Arequipa y Trujillo, 220 usuarios internos y picos de hasta 3,000 clientes u operadores externos concurrentes durante campañas.

Su datacenter centralizado concentra portal B2B, pedidos, inventario, despacho, archivos, reportes e identidad. La migración elimina puntos únicos de falla, segmenta redes, protege datos, permite crecer por demanda y habilita continuidad comprobable sin detener el negocio.

## 2. Arquitectura objetivo

```text
Clientes y operadores
        |
Internet -> seguridad/HTTPS objetivo -> AWS ALB -> Portal B2B + API escalable -> RDS PostgreSQL privada
                                                   |                         |
                                                   +-> S3 documentos          +-> outbox de eventos
                                                                                     |
                                                                          TLS + event_id
                                                                                     v
Azure Function (integración de demostración) -> Storage Queue -> worker demo -> Blob privado -> Monitor/Log Analytics
```

La solución es **híbrida** mientras datacenter y sedes coexisten con la nube, y **multicloud** porque cada proveedor recibe una responsabilidad empresarial concreta. No se usará una nube privada.

El diagrama representa el flujo académico existente, no un ERP o WMS real: el portal B2B, ERP interno, WMS/operación física, correo corporativo e identidad son sistemas separados. Sus límites y la arquitectura empresarial objetivo se detallan en [12_arquitectura_empresarial_portal_erp_correo.md](12_arquitectura_empresarial_portal_erp_correo.md).

## 3. Responsabilidad por proveedor

| Proveedor | Dominio | Recursos de demostración |
|---|---|---|
| AWS | Venta y transacción crítica | VPC, ALB, ASG/EC2, RDS PostgreSQL, S3, IAM/Secrets Manager, CloudWatch y mecanismo outbox/reintento |
| Azure | Integración de cumplimiento asíncrona de demostración | Function, Storage Queue, Blob privado, Managed Identity/RBAC, Key Vault, Log Analytics y Application Insights; el ledger no es stock empresarial |

Azure es el segundo dominio del alcance operativo AWS–Azure para este proyecto. Según lo comunicado por el alumno, el docente confirmó presencialmente que puede usarse AWS–Azure. OCI no se implementa ni debe presentarse como desplegado; conviene incluir esa confirmación en el informe final y pedir constancia escrita si está disponible.

## 4. Reglas de verdad

1. Diseño, código y despliegue son estados distintos; nunca se presentan como equivalentes.
2. Toda prueba debe incluir captura, fecha, nube, región, recurso, configuración, resultado y limpieza cuando aplique.
3. No se almacenan contraseñas, tokens, claves, DNS efímeros, cuentas ni datos personales en repositorio, capturas o informe.
4. Cada ventana de nube tiene: inventario previo -> validación IaC -> despliegue -> pruebas -> evidencia -> eliminación/apagado -> inventario final.
5. Los antecedentes de `evidence/legacy/` sirven para rescatar procedimientos, no para demostrar este núcleo.

## 4.1 Corte cloud histórico — 15/10/2026, 00:18–00:30 UTC (superado; véase 4.3)

El perfil AWS `default` autentica por STS en la cuenta académica `841113066612`.
CloudFormation `tangamandapio-live-20261013` está en `UPDATE_COMPLETE` y la
detección de drift terminó `IN_SYNC` a las 00:15:27 UTC. El artefacto
`20261014-landing-loading-v11-python312` está activo en las dos EC2
`InService`; SSM confirmó en ambas la revisión exacta, `systemd=active` y
`/health` local 200. El target group tiene dos destinos sanos; las dos
instancias reemplazadas están drenando y terminando. El ASG tiene mínimo y
deseado 2, máximo 5. El ALB devolvió HTTP 200 en `/`, `/health` y `/ready`.
RDS no fue modificada por el change set. El ALB continúa HTTP; dominio y HTTPS
siguen pendientes.

Para v11 se usó el objeto inmutable publicado en el bucket privado con
versionado y cifrado SSE-S3. La puerta integral local previa al cambio pasó:
165 pruebas Python, 14 Node, 40 transacciones aisladas, build, auditoría de
dependencias, `cfn-lint` y Terraform `fmt`/`validate`/tests. El mecanismo
`AutoScalingInstanceRefresh` fue denegado por la SCP de Academy; se recuperó
el rollback y se aplicó con `AutoScalingRollingUpdate`, lote uno y mínimo dos
instancias saludables. La evidencia cronológica está en
[AWS-DESPLIEGUE-V11](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

Reconsulta posterior a la transición (00:18 UTC): el ASG muestra únicamente
dos instancias `InService`, sin nodos terminando; los dos destinos ALB están
`healthy`. RDS `available`, cifrada, privada, Single-AZ, 20 GB, backups de un
día. Las cinco alarmas CloudWatch están `OK`, con acciones habilitadas. Azure
`/api/health` respondió 200. No se aplicó Terraform ni se cambió Azure.

La VPC `10.10.0.0/16` se revalidó: dos subredes públicas de ALB, dos privadas
de aplicación con NAT y dos aisladas de RDS en dos AZ; los security groups
permiten solo ALB:80→app:8080→PostgreSQL:5432. EC2/RDS no tienen ingreso
directo desde Internet. El listener aún no tiene TLS (dominio/HTTPS pendientes).

A las 00:30 UTC el E2E autenticado volvió a pasar sobre v11: Admin, Comercial y
Operaciones tuvieron los permisos esperados; el SKU sintético se importó, la
venta completó, la recepción compensatoria completó y ambos eventos outbox
fueron entregados por Azure. El ledger de demostración se mantuvo en 10→10.
24/24 lecturas autenticadas dieron 200, concurrencia 6, p95 679.98 ms desde
loopback en EC2; no fue una prueba por ALB ni de capacidad para 3,000 usuarios.
La nueva puerta local también pasó: 165 Python, 14 Node, 40 transacciones
aisladas, build, auditoría, `cfn-lint` y Terraform fmt/validate/tests, sin
`apply`. Véase [revalidación del 15/10](../evidence/current/CLOUD-REVALIDATION-2026-10-15.md).

## 4.2 Estado anterior a v11 — 14/10/2026, 14:17 (histórico)

Con el token temporal nuevo, AWS STS autenticó la cuenta `841113066612`. A las 14:13, CloudFormation `tangamandapio-live-20261013` reportó `UPDATE_COMPLETE`/`IN_SYNC`; el ALB está `active`, 2/2 destinos `healthy`, ambas EC2 `t3.micro` `running` y RDS `available`, privada y cifrada, Single-AZ, con 1 día de backup. `DatabaseMultiAZ=false` y `DatabaseBackupRetentionDays=1` coinciden entre el despliegue y la IaC. A las 14:17, `/`, `/health`, `/ready` y `/api` devolvieron 200; `/api/admin/users` y `/api/orders` devolvieron 401 sin sesión y `/metrics` 404 anónimo. No se modificó infraestructura. El ALB sigue solo HTTP, sin dominio ni certificado HTTPS.

La Function Azure `/api/health` devolvió 200 en el mismo corte. La ejecución E2E autenticada desde EC2 v10 pasó: admin `admin`; Comercial y Operaciones cumplieron los 200/403 previstos; importación de SKU por API, venta `completed_demo`, recepción compensatoria `received_demo`, dos eventos outbox `delivered` en Azure Queue/Function y ledger sintético 10→10. También completó 24/24 lecturas autenticadas, concurrencia 6, p95 267.93 ms desde el proceso de una EC2 por loopback; no atravesó ALB ni mide escalabilidad a 3,000 usuarios. Los documentos QA persistidos son sintéticos y auditados. La carga CSV mediante navegador no se ejecutó.

La puerta local terminó aprobada: 163 pruebas Python más 14 Node, PT-PERF-02 40/40, build, auditorías y CloudFormation/Terraform fmt/validate/tests. El lote de hasta 500 SKU y rechazo de 501 se prueba localmente; el flujo API quedó además validado en vivo. PT-DR-01 pasó el 13/10 con marcador SQL, RTO 289 s, RPO observado 14 s y limpieza; no se repitió tras v10. Application Insights reportó 2 eventos aceptados, 2 ejecuciones del consumidor y 0 fallos; el peek poison fue denegado por RBAC sin alterar datos. Pendientes: importación CSV visual, revisión navegador/UX por rol, carga por ALB/ASG, evidencia de entrega de alertas Azure y acceso de solo lectura a conteo poison, decidir/reforzar la resiliencia RDS (Single-AZ/1 día), red privada AWS–Azure (diferida por costo), dominio/HTTPS y A/V WebRTC entre dos navegadores. AWS SNS: el usuario confirmó haber recibido alerta y recuperación; falta archivar evidencia directa para sustentación. Véanse la [revalidación cloud](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md), la [QA local](../evidence/current/QA-LOCAL-2026-10-14.md), el [despliegue AWS](../evidence/current/aws/AWS-DESPLIEGUE-2026-10-14.md) y el [E2E Azure](../evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md).

La arquitectura empresarial, que separa portal B2B, ERP, WMS, correo e identidad y distingue objetivos de lo implementado, está organizada en [12_arquitectura_empresarial_portal_erp_correo.md](12_arquitectura_empresarial_portal_erp_correo.md).

## 4.3 Estado histórico — 16/10/2026, 05:44–06:10 UTC (superado)

El estado descrito en la sección 4.1 ya no representa disponibilidad actual.
El dominio HTTPS conserva TLS válido, pero `/` y `/health` responden HTTP 503;
una consulta directa confirmó que el ALB devuelve 503 en su listener 443. El
listener HTTP redirige a HTTPS. STS rechazó el token AWS nuevo con
`InvalidClientTokenId`, así que ASG, destinos, instancias y logs no se pudieron
consultar ni modificar. No se declara el portal operativo hasta recuperar 200
y repetir pruebas funcionales. El 503 del health público y del origen ALB se
repitió a las 05:51 y 05:58 UTC.

Azure for Students está `Enabled`; `rg-tangamandapio-rebuild-wus` está
`Succeeded` y `tangama-wms-261008` está `Running`/HTTPS-only. El health
desplegado respondió 200 y el E2E sintético local→Azure volvió a pasar, dejando
el saldo ficticio en su línea base y poison count cero. Esto no ejercitó EC2 ni
RDS. El inventario ARM enumeró diez recursos, incluidos telemetría y alertas; el
plan Terraform Azure consultó el backend remoto y quedó `No changes` a las
05:57 UTC; no hubo `apply`. Evidencia:
[corte cloud 06:10 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0547UTC.md).
El E2E local→Azure volvió a pasar a las 06:09 UTC con venta/restock sintéticos
y saldo de ledger restaurado; no se originó en EC2/RDS ni valida la aplicación
AWS, que volvió a devolver 503 en la sonda de las 06:10 UTC. La Function
Azure respondió health 200 en esa misma comprobación.

## 4.4 Corte histórico — 16/10/2026, 06:13–06:28 UTC (superado por 4.5)

El token temporal más reciente se guardó en el perfil local `default` y AWS STS
lo aceptó para la cuenta `841113066612`; el rechazo de las 06:04 pertenecía al
token anterior. El stack `tangamandapio-live-20261013` reporta
`UPDATE_COMPLETE` (último cambio 00:27:59 UTC), el ALB está `active` y RDS
`available`, cifrada, privada, Single-AZ, con backup de un día. Sin embargo,
el ASG conserva mínimo/deseado 2 y máximo 5 pero no tiene instancias; el target
group tampoco tiene destinos. Los dos lanzamientos de las 06:07 terminaron con
`Client.InternalError` en AZ distintas. CloudTrail identificó dos denegaciones
explícitas de `kms:Decrypt` por la SCP de AWS Academy al procesar el volumen
raíz cifrado con `alias/aws/ebs`; por eso falló el aprovisionamiento y el portal
devolvió `/health` 503. Se preparó un parámetro `EncryptRootVolume` con valor
seguro predeterminado `true` y override explícito solo para el laboratorio,
pero no se creó change set ni se modificó AWS mientras se decide la excepción.
La puerta local posterior al cambio aprobó 218 pruebas unitarias, 14 Node,
40 transacciones aisladas, build, auditorías, CloudFormation y Terraform, sin
escrituras cloud.
Evidencia: [estado 06:22 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0622UTC.md) y [diagnóstico KMS 06:28 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0628UTC.md).

Azure no se revalidó en esta ventana. Su último health HTTP 200 fue a las 06:10
y el último E2E local→Azure pasó a las 06:09 con inventario/ledger sintético;
no usó EC2/RDS. El plan Terraform remoto Azure de las 05:57 fue `No changes`,
sin `apply`.

## 4.5 Revalidación vigente — 16/10/2026, 06:39–07:03 UTC

El token temporal AWS autenticó en la cuenta `841113066612`. Sin cambiar la
plantilla ni el stack, el ASG logró lanzar instancias con el Launch Template v18
y volúmenes raíz EBS cifrados. Una detección fresca de drift terminó
`IN_SYNC` a las 06:53:38 UTC; CloudFormation sigue `UPDATE_COMPLETE` y el ALB
`active`. A las 06:53 había dos instancias `InService`/`Healthy` y dos destinos
`healthy`; dos instancias previas estaban saliendo del grupo. El FQDN
`https://tangamandapio.kendellnm.me/health` respondió 200 a las 06:53:42 UTC.

CloudTrail registra que el rol de laboratorio `vocareum/resource` detuvo dos
instancias anteriores a las 06:45:43–06:45:44 UTC; no se atribuye esa acción a
un cambio de plantilla ni a una acción de esta revisión. El primer comando SSM
`admin-modules` quedó sin empezar en una de esas instancias detenidas; se
canceló tras confirmar `ExecutionStartDateTime=null`. Repetido una sola vez
contra la instancia sana `i-04b97f0ae7a9eddb5`, el smoke pasó: gasto sintético
de 0.05 liquidado y persistido, correo interno `portal_only` enviado/leído y
conteo aproximado de poison queue Azure igual a 0 sin exponer payloads. El E2E
AWS→Azure completo anterior también pasó en esta misma ventana: venta y compra
demo compensadas, ledger sintético 10→10, dos eventos entregados, matriz de
roles API y 24/24 lecturas concurrentes 200 (seis concurrentes, p95 346.89 ms).

Azure CLI muestra la suscripción `Enabled` y Function `tangama-wms-261008`
`Running`/HTTPS-only; `https://tangama-wms-261008.azurewebsites.net/api/health`
respondió 200. La integración WMS continúa siendo un ledger sintético. No se
habilitó VPN/red privada entre nubes, no se alteró el estado del stack, y no se
revalidaron en este corte ni la experiencia visual completa en Chrome, WebRTC
entre dos navegadores ni carga representativa. Evidencia:
[revalidación de nube 06:54 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0654UTC.md).

La puerta integral local se repitió a las 07:02 UTC y terminó aprobada: 218
pruebas unitarias, 14 pruebas Node, 40 transacciones aisladas, build y auditoría
de dependencias, validación CloudFormation y Terraform `fmt`/`validate`/tests;
no ejecutó operaciones de nube. Evidencia:
[QA local 07:02 UTC](../evidence/current/QA-LOCAL-2026-10-16-0702UTC.md).

Reconsulta a las 07:03 UTC: el ASG ya quedó exactamente con dos instancias
`InService`/`Healthy`, dos targets `healthy`, y ambos health endpoints (AWS y
Azure) devolvieron 200.

## 5. Estado verificado al corte — 04/10/2026 (histórico; superado por la sección 4.3)

| Área | Estado | Límite de la afirmación |
|---|---|---|
| AWS | Ciclo temporal cerrado. CloudFormation no muestra pilas de Tangamandapio y EC2 no muestra instancias en `us-east-1`. | Las pruebas del 01-02/10 son evidencia histórica válida del ciclo; no se declara disponibilidad actual. |
| Azure | Ciclo temporal cerrado. El grupo `rg-tangamandapio-261001r2-wus` fue eliminado y la consulta autenticada devolvió que no existe. | Las pruebas Health/Fulfillment anteriores prueban el ciclo pasado; no se declara Function activa. |
| Aplicación | Portal B2B, API, roles y contrato WMS existen en el repositorio. | La publicación live fue efímera. Falta repetir login/roles y la integración AWS→Azure en un mismo ciclo si se desea una demo actual. |

## 6. Definición de terminado

El proyecto queda listo para sustentar cuando demuestre: aplicaciones con responsabilidades separadas, persistencia e integración reales, segmentación de red, control de seguridad, balanceo/HA, observabilidad, IaC reproducible y costos/cierre. El plan funcional y sus límites están en [12_arquitectura_empresarial_portal_erp_correo.md](12_arquitectura_empresarial_portal_erp_correo.md); la hoja de ruta cloud sigue en [07_plan_reanudacion_y_mejoras.md](07_plan_reanudacion_y_mejoras.md) y [09_propuesta_cloud_aws_azure.md](09_propuesta_cloud_aws_azure.md). Las tres distinguen hechos verificados, candidatos y objetivos.

## 7. Actualización de ejecución — 01/10/2026

AWS validó la plantilla CloudFormation y creó el stack temporal. Antes de que AWS Academy cancelara la credencial local, se verificaron dos targets ALB `healthy`, RDS PostgreSQL privada/cifrada, S3 con bloqueo público, dashboard y alarmas, además de `GET /health` 200, `POST /api/orders` 201 y `GET /api/orders` 200. La evidencia está en [evidence/current/aws](../evidence/current/aws/CUR-AWS-03_despliegue_y_prueba_2026-10-01.md). La cancelación ocurrió después de las pruebas: no se afirma inventario cero hasta renovar la sesión y ejecutar el cierre.

En Azure, Terraform validó y aplicó el vertical temporal en West US. Tras corregir el empaquetado remoto Linux y el TTL de Queue, `HttpHealth` devolvió 200, `HttpFulfillment` aceptó el evento con 202, el reenvío devolvió 200 por idempotencia y se verificaron el objeto Blob y el mensaje Queue. Los registros están en [evidence/current/azure](../evidence/current/azure/README.md). Posteriormente se eliminaron los dos Resource Groups de Tangamandapio y la consulta final por prefijo no devolvió recursos.

## 8. Publicación B2B en AWS — 02/10/2026

Se publicó el artefacto versionado del portal B2B en el bucket privado del stack y se actualizó el Launch Template para descargarlo en cada nodo del ASG. El primer change set revirtió de forma automática porque el secreto de sesión declaraba una clave generada sin el objeto JSON base exigido por Secrets Manager. No se sustituyeron VPC, ALB ni RDS; el rollback eliminó únicamente los secretos nuevos incompletos y mantuvo la infraestructura previa.

Corregida la plantilla con `SecretStringTemplate: '{}'`, CloudFormation la validó y el segundo change set terminó `UPDATE_COMPLETE` a las **11:56 a. m. (America/Chicago)**. Durante el recambio gradual, `GET /health` respondió HTTP 200 e indicó `database=ok`. El registro técnico completo está en [CUR-AWS-10](../evidence/current/aws/CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md).

Después de reiniciar el laboratorio, la consola de CloudFormation muestra **Pilas (0)** al filtrar Tangamandapio y el nombre DNS del ALB de esa ejecución ya no resuelve. Por ello esta publicación se conserva como evidencia técnica histórica del ciclo, no como infraestructura actualmente activa. La siguiente ejecución debe reprovisionar el stack con una credencial AWS Academy vigente y entonces repetir, con capturas reales, login/roles, rutas protegidas y los dos targets saludables.

## 9. Actualización de ciclo y revisión visual — 08/10/2026

La observación de cierre del punto 8 aplica al ciclo `tangamandapio-live-20261001`, no a ciclos posteriores. La revisión actualizada y la fuente de verdad del inventario están en [MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md); sustituyen la observación visual anterior que no pudo cargar CloudFormation.

La primera ejecución de la puerta local aprobó 58 pruebas (22 API base, 14 Azure Functions y 22 del release AWS); una ejecución posterior aprobó 59/59. El [registro de pruebas](../evidence/current/PRUEBAS_LOCALES_2026-10-08.md) conserva ambos cortes. El build de la web y las validaciones locales de Terraform/CloudFormation también pasaron. Esto no equivale a una llamada WebRTC real ni a un WMS/ERP conectado. La restauración PITR temporal sí se probó, pero falta medir formalmente RTO/RPO. Las capturas nuevas de Chrome no pudieron archivarse desde la sesión; el índice señala qué PNG falta y qué imágenes existentes son tarjetas resumidas, no capturas crudas.

## 10. Reconstrucción Azure y prueba viva — 12/10/2026

La suscripción activa figura como **Azure for Students / Enabled**; ese estado no informa el saldo disponible. Se reconstruyó el vertical Azure con 14 recursos administrados por Terraform (cero destrucciones). La Function `tangama-wms-261008` quedó `Running`, HTTPS-only, con autenticación básica de publicación FTP/SCM deshabilitada; el Blob es privado, TLS 1.2 y LRS.

La prueba viva devolvió `/api/health` 200; llamada sin clave 401; productor desconocido 400; evento permitido 202 `queued`; repetición del mismo ID 202 `queued_duplicate`; consulta final `demo_fulfillment_completed`. El ledger ficticio descontó una unidad de SKU-ARROZ-001 (25→24) y declaró `is_real_erp=false`. El 14/10/2026 se configuraron dos receptores en el Action Group Azure mediante Terraform; el plan posterior terminó `No changes`. Las reglas están habilitadas, pero no se disparó una alerta ni se comprobó la entrega.

El entorno Azure queda activo y puede incurrir cargos. No se comprobó consumo/credito disponible ni se probó una solicitud originada en AWS en este ciclo. La Function/Blob/Queue son un WMS de laboratorio, no un WMS empresarial; VNet/VPN multicloud, inventario real, DNS/HTTPS propio, llamada WebRTC A/V real y captura directa de consola siguen pendientes.
