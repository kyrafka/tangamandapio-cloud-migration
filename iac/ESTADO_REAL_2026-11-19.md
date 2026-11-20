# Verificación operativa de Tangamandapio

19 de noviembre de 2026, Lima. Cuenta AWS `481056890449` en Ohio y suscripción Azure for Students en West US.

Consulta el [estado del 20/11](ESTADO_REAL_2026-11-20.md) para la reconciliación de
RDS, el correo por rol y la última restauración del ERP.

## RDS Multi-AZ en Ohio

RDS completó la conversión de `tangamandapio-postgres` y quedó en estado
`available` con `MultiAZ=true`. El portal devolvió HTTP 200 a `/ready`
durante y después de la conversión. Se conservó la base PostgreSQL cifrada,
con 20 GiB gp3 y un día de respaldos. La conmutación de la base aún requiere
un ensayo controlado. El costo adicional estimado para 21 días de operación
continua es USD 10,66 antes de créditos.
[Evidencia de la conversión](../evidence/current/aws/AWS-RDS-MULTIAZ-2026-11-19.json)
· [Cálculo de costos](../evidence/current/COSTOS-2026-11-19.md).

El parámetro `DatabaseMultiAZ` del stack aún figura en `false`. El conjunto
de cambios que reconoció `SyncWithActual` para RDS también propuso reemplazar
recursos de red y quitar una suscripción SNS existente. Se retiraron las dos
propuestas sin ejecutarlas. Para el siguiente despliegue del stack, revisar el
conjunto de cambios preparado con `DATABASE_MULTI_AZ=true`.
[Parámetros de despliegue](cloudformation/README.md).

## Recuperación fuera de AWS

RDS devolvió una denegación explícita de la política de la organización en
las 16 regiones AWS habilitadas fuera de Ohio. Azure Blob en West US ya
conserva la copia externa. Se restauró en PostgreSQL local temporal con
Azure Blob y Key Vault, sin usar las API ni el cómputo de AWS. Se verificaron
las huellas del cifrado y del archivo, 20 tablas, un pedido y un evento
outbox en 14,568 s. El clúster temporal se eliminó. La prueba demuestra
la recuperación de la base fuera de AWS. Sigue pendiente levantar y
redirigir un ERP completo en otra región.
[Evidencia de restauración independiente](../evidence/current/azure/AZURE-POSTGRES-RESTORE-WITHOUT-AWS-2026-11-19.json).

La cuenta de almacenamiento de Azure está en `Standard_LRS`. Mantiene
la copia en una sola región de Azure. La programación diaria y la clave
de recuperación siguen siendo dependencias de este procedimiento.

## Segunda ronda de pruebas del 19/11

- **WAF.** CloudFormation creó `tangamandapio-waf-logging`. El grupo de
  CloudWatch conserva siete días. Una petición HTTPS real a `/ready` dejó
  un registro `ALLOW` con la cookie y la cadena de consulta ocultas.
  [Evidencia del WAF](../evidence/current/aws/AWS-WAF-LOGGING-2026-11-19.json).
- **Disponibilidad.** El cambio al respaldo se observó a los 1,43 s. Las
  aplicaciones completaron HTTPS privado en 2,64 s y 2,60 s tras el corte,
  con dos solicitudes fallidas en cada una y retorno al principal. El objetivo
  se cumplió en esa ejecución.
  [Evidencia de conmutación](../evidence/current/aws/AWS-WMS-FAILOVER-RUBRIC-2026-11-19.json).
- **Carga.** Una repetición acotada con 10.000 peticiones HTTPS directas al
  ALB y 50 concurrentes obtuvo 9.999 HTTP 200 y un 502. p95 de 487,14 ms.
  El registro del 502 muestra la acción `waf,forward` y carece de código
  HTTP del destino. Los logs archivados no conservan la ventana del 16/11,
  así que los 4.399 fallos históricos de transporte siguen sin causa demostrada.
  [Resultado de carga](../evidence/current/aws/AWS-ALB-LOAD-RECHECK-2026-11-19.json)
  · [Correlación ALB](../evidence/current/aws/AWS-ALB-502-CORRELATION-2026-11-19.json).
- **RPO.** La copia diaria de las 00:08:42 de Lima se cotejó con RDS en modo
  lectura a las 15:48:26. En una caída simulada en ese momento quedarían fuera
  un pedido sintético y un evento outbox. El punto tenía 15 h 39 min 44 s de
  antigüedad. Se verificó la integridad y el Azure Key Vault volvió a permitir
  el descifrado autorizado de la copia. El tiempo de 35,108 s viene de la
  restauración aislada previa de la misma copia.
  [Evidencia de RPO](../evidence/current/aws/AWS-POSTGRES-RPO-MARKERS-2026-11-19.json).
- **Seguridad y alcance.** AWS informó cero usuarios IAM y cero claves raíz
  en la cuenta del proyecto. La sesión operativa usa STS. El rol del router
  tiene `ReplaceRoute` acotado a la tabla de aplicación y el despacho de
  respaldo tiene alcance al documento SSM del proyecto y a las instancias
  con etiqueta del ASG. El ERP aún lee el secreto maestro de su RDS, por lo
  que queda pendiente un usuario SQL separado con permisos de ejecución.
  Siguen por verificar las credenciales que aparecieron en capturas de otras
  cuentas. [Revisión de IAM](../evidence/current/aws/AWS-IAM-SCOPE-2026-11-19.json).
- **Regiones y entrega.** RDS seguía en Single-AZ durante este corte. La SCP denegó el
  acceso a RDS en `us-west-2` y `us-east-1`; no se efectuó una restauración
  regional. El emulador creó y eliminó 17 recursos de red de Terraform.
  CloudFormation identificó 21 de 23 recursos de su subconjunto y el borrado
  devolvió `DependencyViolation`. La reconstrucción completa requiere probar
  las dos nubes desde cuentas vacías. Se presenta AWS–Azure según la
  confirmación del equipo.
  [Prueba de IaC](../evidence/current/aws/AWS-IAC-EMULATOR-2026-11-19.json)
  ·
  [Tabla de costos por servicio](../evidence/current/COSTOS-2026-11-19.md).

## Portal y permisos

La versión `20261119-technical-tests-and-recovery` quedó desplegada. La sección
**Administración → Pruebas técnicas** rechazó con HTTP 401 el acceso anónimo
y devolvió HTTP 200 con sesión administrativa. La consulta al WMS desde el
ERP respondió en 861,09 ms en esta prueba, con cero mensajes pendientes y cero
en la cola de errores. [Prueba del módulo en producción](../evidence/current/aws/AWS-ERP-TECHNICAL-TESTS-2026-11-19.json).

El administrador pudo iniciar y cerrar sesión por el dominio público. El CNAME de Cloudflare apuntaba a un balanceador anterior. Se actualizó el registro de Tangamandapio con el ALB actual y se verificaron TLS y sesión de administrador. La contraseña activa se guarda en `tangamandapio/portal/admin` en Secrets Manager.

| Evidencia | Resultado |
| --- | --- |
| [Sesiones por rol en navegador](../evidence/current/aws/AWS-PORTAL-ROLES-BROWSER-2026-11-19.json) | 256 comprobaciones aprobadas en diez sesiones de producción. Se abrieron los módulos según el rol, se verificaron las respuestas 403 esperadas y se confirmó la suspensión de la cuenta temporal. Administración consultó el WMS con cero mensajes pendientes y cero en la cola de errores. |
| [Portal público](../evidence/current/aws/AWS-PUBLIC-PORTAL-ADMIN-2026-11-18.json) | 32 lecturas HTTP 200. Incluyen administración, usuarios, empresas, alertas, auditoría, pedidos, outbox, ERP, inventario WMS y telefonía. |
| [Roles del portal](../evidence/current/aws/AWS-PORTAL-ROLES-2026-11-19.json) | Seis roles y 42 respuestas contrastadas con la matriz de permisos. Cinco cuentas temporales quedaron desactivadas. |
| [Roles y operaciones ERP](../evidence/current/aws/AWS-ERP-ADMIN-MODULES-2026-11-19.json) | Seis roles ERP y 48 comprobaciones. Se registró y liquidó un gasto sintético de 0,05 en el ERP. El panel concilió el pedido con su evento outbox. |
| [WebRTC y correo](../evidence/current/aws/AWS-PORTAL-WEBRTC-MEDIA-2026-11-19.json) | Una llamada entre administrador y ventas intercambió SDP por el portal y recibió audio sintético en ambos sentidos. Se comprobaron 12 tramas por extremo, cierre de llamada y correo interno recibido y marcado como leído. Dos clientes de prueba en el mismo equipo. TURN sigue sin configurar y falta verificar audio entre redes restrictivas. |
| [Grabación WebRTC](../evidence/current/aws/AWS-PORTAL-WEBRTC-RECORDING-2026-11-19.json) | El inicio antes del consentimiento devolvió 409. Con aprobación de ambos participantes, un archivo Ogg sintético se guardó, el destinatario lo recuperó por HTTPS y se verificaron su SHA-256 y 19.512 muestras decodificadas. |

## Ruta privada y conmutación

- Dos EC2 privadas `t3.micro` se enrolaron en Tailscale. Ambas EC2 de aplicación resolvieron y alcanzaron la Function por HTTPS 200 en `10.20.1.4` con TLS verificado. La ruta `/32` y el DNS privado están activos. [Prueba desde las dos aplicaciones](../evidence/current/aws/AWS-AZURE-PRIVATE-WMS-2026-11-18.json).
- El pedido ficticio `WMS-DEMO-20261119-AF9E52` salió del portal con HTTP 201. El evento `evt-a56553941e9747e6bbd1ff5637ff9f4c` pasó por Function y Queue. Application Insights registró la publicación y finalización del mismo evento, y Blob devolvió el evento original y su resultado cifrados. [Prueba de extremo a extremo](../evidence/current/azure/AZURE-WMS-PRIVATE-ORDER-2026-11-18.json).
- El controlador confirma un apagado explícito de Tailscale y comprueba en paralelo la ruta vigente y la salud HTTPS del destino antes de cambiar la ENI. En dos pruebas después del ajuste el respaldo tomó el tráfico y el principal recuperó la ruta. El cambio se observó a los **3,21 s** y **8,20 s**. El primer HTTP 200 completo desde las EC2 llegó a **4,59 s y 6,59 s** en la primera prueba, y a **9,88 s y 9,92 s** en la segunda. La meta de 3 s queda abierta. La medición anterior fue 4,68 s y 5,57 s para el primer HTTP 200. [Medición inicial](../evidence/current/aws/AWS-AZURE-WMS-FAILOVER-2026-11-19.json) · [Primera prueba ajustada](../evidence/current/aws/AWS-AZURE-WMS-FAILOVER-FAST-2026-11-19.json) · [Repetición](../evidence/current/aws/AWS-AZURE-WMS-FAILOVER-RETEST-2026-11-19.json).
- Gmail recibió los avisos de paso a respaldo y retorno al principal. También se observó la recepción de la prueba SNS, eventos de lanzamiento y terminación del ASG y un correo de Azure Monitor. La segunda suscripción SNS aún figura sin confirmar.
- El controlador de respaldo usa una sesión persistente de AWS. Cada router reutiliza su sondeo HTTPS de Azure durante 30 segundos en condiciones normales y conserva el estado anterior ante un fallo transitorio único. La detección del proceso Tailscale sigue siendo inmediata en cada consulta local. CloudFormation conserva la ruta operativa y el paquete de reconstrucción actualizado ya está en el bucket de activos. La actualización del servicio en los nodos existentes se hizo de forma escalonada mediante Systems Manager.

## Seguimiento por rol y colas WMS

- **Seguimiento de pedidos** reutiliza los seis roles existentes. Cliente B2B
  queda limitado a su empresa, Ventas registra pedidos, Almacén y Auditoría
  consultan las etapas, y Operaciones y Administración gestionan los reintentos.
  Se probaron estas vistas en navegador con base aislada y se verificó el
  aislamiento entre empresas. [Flujo y permisos](../app/aws_release/PLATFORM_CONSOLE.md#seguimiento-de-pedidos-por-rol).
- El pedido sintético `SEGUIMIENTO-DEMO-20261119-151352` se guardó en AWS con
  HTTP 201 en 61 ms y siguió las etapas **pendiente → en cola → procesado**.
  Azure conservó el evento y el resultado cifrados en Blob. Application Insights
  registró la publicación en Queue y la escritura del resultado. El saldo
  validado corresponde al inventario de demostración.
  [Evidencia del portal](../evidence/current/aws/AWS-PORTAL-ORDER-TRACKING-2026-11-19.json)
  · [Evidencia de Azure](../evidence/current/azure/AZURE-WMS-ORDER-TRACKING-2026-11-19.json).
- La consulta privada de colas devolvió HTTP 200 con autenticación y 401 sin
  clave. En la comprobación posterior al pedido, la cola de trabajo y la de
  fallidos tenían cero mensajes. [Evidencia de colas](../evidence/current/azure/AZURE-WMS-QUEUE-STATUS-2026-11-19.json).
- CloudFormation terminó en `UPDATE_COMPLETE` con dos destinos sanos. Por
  el dominio público, la sesión de Administración abrió Seguimiento y volvió
  a consultar el resultado procesado y el estado de las colas con HTTP 200.

## Respaldo y recuperación

- Systems Manager ejecuta el respaldo a las **03:00 de Lima**. Crea un objeto diario en Azure y guarda los hashes en S3. La autorización de Blob permite crear objetos en el contenedor privado y dura 24 días desde el 19/11. Para operar más allá de ese período, hay que reemplazar esa autorización a tiempo. Azure conserva las copias bajo `postgres/` por 30 días.
- `postgres/20261119-daily.json` fue exportado por la asociación y devuelto por Azure Blob con una coincidencia del hash. El segundo nodo fue rechazado al intentar reutilizar el mismo nombre. Se agregó el manifiesto diario en S3 y una reejecución de la asociación dio `Success` en ambos nodos, que reconocieron esa copia.
- La restauración actual validó las huellas, descifró la copia y levantó un PostgreSQL 18.6 temporal en RAM con socket local. Recuperó 20 tablas, un usuario, un pedido y un evento outbox en **35,108 s** de extremo a extremo. El respaldo diario define la frecuencia prevista. Medir el RPO requiere una prueba de pérdida de transacciones con marcas conocidas. [Prueba de exportación y restauración](../evidence/current/aws/AWS-AZURE-POSTGRES-SCHEDULE-2026-11-19.json).

## Administración y escalado

- En **Administración → Respaldos** se consultaron tres archivos de Azure Blob.
  La descarga de la copia diaria devolvió 84.654 bytes. **Ejecutar respaldo**
  guardó un pedido y su evento outbox en S3 con AES256. Se descargó esa copia
  desde el portal y su SHA-256 coincidió. Se usó el rol de aplicación de una
  EC2 con la revisión `20261119-admin-backup-and-scaling`. [Evidencia autenticada](../evidence/current/aws/AWS-PORTAL-ADMIN-BACKUP-2026-11-19.json).
- **Administración → Prueba de escalado** consulta capacidad deseada y sana.
  Admite 3, 4 y 5 instancias y programa el regreso antes de modificar el ASG.
  En Moto se verificaron las tres solicitudes y los valores de regreso a 2.
  Desde el portal público, la solicitud de tres instancias obtuvo HTTP 202.
  El ALB marcó tres destinos sanos y la acción de las 09:12 de Lima devolvió
  automáticamente la capacidad a dos. El balanceador volvió a dos destinos
  sanos. A las 09:17 terminaron el drenaje y la retirada de la tercera EC2.
  [Ciclo en AWS](../evidence/current/aws/AWS-PORTAL-SCALING-2026-11-19.json)
  · [Procedimiento del portal](../app/aws_release/PLATFORM_CONSOLE.md).
- Después de publicar la revisión, las tres EC2 activas durante la prueba de
  capacidad resolvieron `10.20.1.4` e hicieron HTTPS 200 contra el WMS. Sus
  consultas tardaron entre 270 y 322 ms, con la ruta de vuelta en el principal.
  [Comprobación desde las instancias actualizadas](../evidence/current/aws/AWS-PORTAL-RENEWAL-PRIVATE-WMS-2026-11-19.json).
- k6 sostuvo 25 usuarios virtuales durante 120 s después de la rampa. El ALB
  respondió correctamente a las 3.013 peticiones HTTPS a `/ready`, con p95 de
  **189,86 ms**. No se enviaron pedidos ni solicitudes al WMS. La prueba anterior
  envió 300.000 peticiones a `/` con 50 clientes concurrentes y registró 4.399
  fallos de transporte (4.276 `URLError`, 102 timeouts y 21 conexiones
  reiniciadas) más 8 respuestas 502. CloudWatch registró 7 respuestas 502
  agregadas en la ventana histórica revisada. Los datos no identifican el
  origen específico de cada fallo de transporte. La prueba acotada usa otra
  ruta, concurrencia y protocolo, por lo que el escenario histórico queda como
  antecedente abierto. [Nueva carga](../evidence/current/aws/AWS-ALB-SUSTAINED-2026-11-19.json)
  · [Métricas históricas](../evidence/current/aws/AWS-ALB-HISTORICAL-ERRORS-2026-11-16.json).
- La prueba transaccional aislada ejecutó 180 pedidos sintéticos con 20
  concurrentes. Recuperó los 180 pedidos y conservó los 180 eventos outbox
  pendientes, sin dependencias externas. El p95 local fue 1,91 s.
  [Prueba de pedidos y outbox](../evidence/current/aws/LOCAL-PORTAL-ORDER-LOAD-2026-11-19.json).

## Reconstrucción aislada

- **Terraform** creó y retiró 17 recursos usando el módulo de red existente.
  Se verificaron seis subredes en dos zonas, las seis asociaciones de ruta y
  la salida por Internet Gateway. Los entornos reales de VPN AWS y reconstrucción
  Azure pasaron `terraform validate`.
- **CloudFormation** levantó un subconjunto extraído de `aws-lab.yaml`. Moto
  identificó 21 recursos, entre ellos la red, la ruta pública y los dos
  buckets. La versión 5.2.5 no reprodujo todas las asociaciones de las subredes,
  las políticas de bucket ni el borrado ordenado de la VPC. La plantilla
  completa también pasó `ValidateTemplate` en AWS. El emulador no acredita
  NAT, WAF, ALB, RDS ni la VPN real. [Resultado reproducible](../evidence/current/aws/AWS-IAC-EMULATOR-2026-11-19.json)
  · [Comandos para repetir](local-emulator/README.md).

## Referencias para reconstruir

| Servicio | Revisión y artefacto |
| --- | --- |
| Portal AWS | `20261119-order-tracking-and-contingency`, objeto `releases/tangamandapio/portal-b2b-seguimiento-da9a3ea37b1b.tar.gz`, SHA-256 `da9a3ea37b1bd5e82da6e6a31a1dd473538f57551cd5ae235d5d8467b937a104`. |
| WMS Flex | OneDeploy `seguimiento-9295b4146422`, objeto `function-flex-deployments/source/seguimiento-9295b4146422/released-package.zip`, SHA-256 `9295b4146422973cf61ac7da1e55ba30dfd088a27d772e9382e1018facd2287a`. |

La receta de [OneDeploy](environments/azure-flex-private#publicar-en-la-function-privada)
mantiene cerrado el ingreso público. El ZIP llega por ARM con una autorización
temporal de lectura; el token queda fuera de Git y del estado Terraform.

## Costos y restricciones

| Medición | Resultado |
| --- | --- |
| Crédito AWS Free Plan | USD 150,59 restantes. |
| AWS Budgets | USD 10,469 de gasto registrado en el presupuesto de USD 200. Las mediciones de crédito y presupuesto tienen cortes distintos. |
| Azure Cost Management | USD 8,7973 acumulados en el mes. Presupuesto mensual de USD 25. |
| Cambios de capacidad | Dos routers AWS `t3.micro` con crédito de CPU estándar. Se reutilizaron las VM, el Private Endpoint y el almacenamiento de Azure. El respaldo usa las EC2 de aplicación existentes. |

RDS está disponible en Multi-AZ y conserva su respaldo administrado de un día. Una segunda región con el ERP completo, el escalado sostenido por debajo del umbral de errores y el audio entre redes restrictivas quedan por validar. La sustitución de una EC2 completa en cinco segundos queda fuera del ensayo de cambio entre routers.

La defensa requiere adjuntar fotografías autorizadas y aprobación escrita del docente para presentar AWS–Azure cuando la rúbrica pide AWS–OCI.
