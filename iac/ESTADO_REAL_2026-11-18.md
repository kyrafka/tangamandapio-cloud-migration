# Verificación de Tangamandapio del 18 de noviembre de 2026

Fecha local de Lima. Las horas de comandos y métricas se conservan en UTC.
Cuenta AWS `481056890449` en `us-east-2` y suscripción `Azure for Students`.

## Red y portal

- El portal público respondió HTTPS 200 en `/health` y HTTP 301 hacia HTTPS.
  El ALB también respondió con certificado válido para el dominio desde el
  cliente de prueba. La contraseña de `tangamandapio/portal/admin` obtuvo 401.
- Desde cada router Azure (`10.20.0.4` y `10.20.0.5`) la Function privada
  respondió HTTP 200 en `10.20.1.4` con verificación TLS. Application Insights
  registró ambas peticiones con latencias de 202 y 150 ms.
- Tailscale muestra el permiso `tag:tangama-aws-router` → `10.20.1.4/32`
  TCP/443. Los nodos AWS históricos `20261109` aparecen conectados en el
  tailnet, pero no corresponden a las EC2 inventariadas en la VPC actual.
  La tabla de aplicación de Ohio carece de ruta al endpoint y los dos secretos
  de enrolamiento todavía no existen. Pedido privado y conmutación pendientes.
  La plantilla HA validada incorpora la zona DNS de un solo hostname y la
  ruta en la misma etapa. La verificación desde la aplicación exige HTTP 200
  e IP `10.20.1.4` con resolución normal.

## Recuperación de PostgreSQL

- Se exportó la RDS actual con `pg_dump` 18.6, conexión `verify-full` y CA RDS.
  El dump se cifró en memoria con AES-256-GCM y RSA-OAEP-256. La clave RSA
  privada permaneció en Key Vault. Azure devolvió HTTP 201 y confirmó el Blob
  `postgres/20261119T031447Z-79b6a664ff5d.json` (83.590 bytes cifrados).
- La restauración descargó el objeto, verificó las huellas cifrada y del dump,
  y abrió la clave de datos con la versión indicada del Key Vault. Se usó un
  clúster PostgreSQL 18.6 temporal en RAM, inaccesible por TCP y separado de RDS.
  Resultado **20 tablas, 1 usuario del portal, 0 pedidos y 0 eventos outbox**.
  Duración de extremo a extremo **29,794 s**. El tramo del host fue 3,396 s.
- El punto de copia fue 03:14:56 UTC y la restauración empezó a las 03:22:13
  UTC: la copia tenía unos **7 min 17 s**. Esa antigüedad sirve para describir
  el ejercicio manual. El RPO operacional requiere programación y una prueba
  de pérdida con transacciones marcadas. No se midió recuperación regional.
- Se eliminaron los parámetros temporales de SSM y se retiró el permiso de
  escritura del operador sobre el contenedor. RDS permanece en una zona y con
  un día de backups AWS. Falta el trabajo periódico con identidad propia.
- Se importó el contenedor privado `tangama-postgres-backups` al estado remoto
  de Terraform `azure-rebuild`. El módulo declara `prevent_destroy` para ese
  contenedor.
- [Evidencia de recuperación](../evidence/current/aws/AWS-AZURE-POSTGRES-RESTORE-2026-11-18.json).

## Observabilidad, seguridad y costos

- AWS SNS aceptó el aviso de prueba `TANGAMA-SNS-20261118`. Gmail figura
  confirmado y la suscripción UPeU reenviada figura `PendingConfirmation`.
  La recepción en bandeja requiere comprobación del destinatario.
- Las dos reglas de consulta de Azure para 5xx y latencia están habilitadas.
  La API de prueba del grupo de acciones rechazó el envío con `Free subscription
  not supported`. La alternativa controlada usó un HTTP 200 del endpoint
  privado. Azure Alerts Management registró `Fired` a las 03:36:27 UTC para
  la regla de prueba enlazada al grupo de acciones. El registro no confirma
  la recepción en las bandejas de correo.
- CloudFormation habilitó logs del ALB con retención de siete días en el prefijo
  privado `alb-access/`. S3 confirmó `ELBAccessLogTestFile` con SSE-S3 y registró
  las 600 respuestas HTTP 200 de la prueba, desde el ALB y desde el destino. La primera
  actualización se revirtió por una política S3 demasiado restrictiva. El
  segundo cambio dejó al rol EC2 acceso a cuatro secretos de aplicación y
  activó una renovación gradual. CloudFormation cerró `UPDATE_COMPLETE` con
  dos EC2 `InService` en zonas distintas y ambos destinos nuevos `healthy`.
  Los destinos salientes seguían drenando al comprobar `/ready` HTTP 200.
- La prueba anterior de 300.000 peticiones registró 4.399 fallos de transporte
  y 8 respuestas 502 del ALB. Faltan los registros de esa ventana: el ALB aún
  no los guardaba y la retención de logs de aplicación era de un día.
  La prueba actual directa al ALB tuvo 600/600 HTTP 200, con 15 concurrentes y
  p95 de 547,77 ms. El generador registra clases y códigos de error de red para
  la próxima prueba sostenida.
- AWS muestra **USD 151,71 de crédito restante**. Azure tiene el presupuesto
  `tangamandapio-demo-usd25` por **USD 25 al mes** con avisos a USD 12,50, 20 y 25.
  Tras un HTTP 429 inicial, la reconsulta de Cost Management confirmó
  **USD 8,414894** de costo acumulado en noviembre.

## Cierre de la rúbrica

1. Desplegar los routers AWS en la VPC actual, conectar DNS/ruta, enviar un
   pedido sintético y correlacionarlo en Function, Queue, Blob e Insights.
2. Desactivar el router principal de forma reversible y medir conmutación y
   retorno. Validar el objetivo de cinco segundos con el tiempo observado.
3. Programar la exportación y medir RPO con datos de prueba. Verificar recepción
   de avisos y repetir carga sostenida con logs y códigos de transporte.
4. Revisar recuperación de administrador, rotación de la clave de Function,
   opciones de RDS Multi-AZ y reconstrucción completa de AWS/Terraform Azure.
5. Adjuntar aprobación del docente para AWS–Azure, capturas y evidencia de la
   defensa. Integrante, docente y ciclo ya constan en el informe previo.

### Plan Terraform de Azure

El plan posterior a la importación marca el contenedor de respaldos `no-op`.
Propuso también actualizar Key Vault, la Function heredada, el grupo de
acciones y reglas heredadas, y reemplazar el paquete ZIP. Se alineó la opción
de alertas heredadas en código y se reservó la aplicación de los demás
cambios hasta reconciliar el paquete y el estado de los recursos.
