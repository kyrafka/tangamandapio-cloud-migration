# Verificación operativa de Tangamandapio

19 de noviembre de 2026, Lima. Cuenta AWS `481056890449` en Ohio y suscripción Azure for Students en West US.

## Portal y permisos

El administrador pudo iniciar y cerrar sesión por el dominio público. El CNAME de Cloudflare apuntaba a un balanceador anterior. Se actualizó el registro de Tangamandapio con el ALB actual y se verificaron TLS y sesión de administrador. La contraseña activa se guarda en `tangamandapio/portal/admin` en Secrets Manager.

| Evidencia | Resultado |
| --- | --- |
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

## Costos y restricciones

| Medición | Resultado |
| --- | --- |
| Crédito AWS Free Plan | USD 150,59 restantes. |
| AWS Budgets | USD 10,469 de gasto registrado en el presupuesto de USD 200. Las mediciones de crédito y presupuesto tienen cortes distintos. |
| Azure Cost Management | USD 8,7973 acumulados en el mes. Presupuesto mensual de USD 25. |
| Cambios de capacidad | Dos routers AWS `t3.micro` con crédito de CPU estándar. Se reutilizaron las VM, el Private Endpoint y el almacenamiento de Azure. El respaldo usa las EC2 de aplicación existentes. |

RDS está disponible en una sola zona y conserva su respaldo administrado de un día. El plan gratuito admite el despliegue Single-AZ. Una segunda región de recuperación, el escalado sostenido por debajo del umbral de errores y el audio entre redes restrictivas quedan por validar. La sustitución de una EC2 completa en cinco segundos no forma parte del resultado medido por el cambio entre routers.

La defensa requiere adjuntar fotografías autorizadas y aprobación escrita del docente para presentar AWS–Azure cuando la rúbrica pide AWS–OCI.
