# Cierre técnico de nube y portal — 08/10/2026

Este archivo conserva los cambios y pruebas del corte de las 21:26 UTC. El
estado posterior de inventario, IaC y pendientes está centralizado en
[MAPA_ESTADO_ACTUAL_2026-10-08.md](MAPA_ESTADO_ACTUAL_2026-10-08.md); úsalo como
referencia actual. No se guardan claves, tokens, contraseñas ni contenido de audio.

## Resultado operativo del corte — 08/10/2026, 21:26 UTC (histórico; el mapa actual lo supera)

- **IaC y publicación:** recuperé el template exacto del stack existente, reconcilié `iac/cloudformation/aws-lab.yaml` antes de aplicarlo y validé la plantilla. El change set conservó los valores actuales de todos los parámetros; solo cambió la configuración de despacho automático y sus referencias de versión de Launch Template. CloudFormation terminó `UPDATE_COMPLETE`; el detector de drift quedó `IN_SYNC` (0 recursos). El ASG terminó con 2 instancias `InService/Healthy` y sus 2 destinos saludables. No se tocaron red, WAF, RDS ni backups.
- **Despacho/outbox:** `AUTO_DISPATCH_EVENTS=true` quedó confirmado por SSM en ambas instancias; `OUTBOX_RETRY_INTERVAL=60` y el servicio de aplicación está activo. Se añadió una prueba unitaria que comprueba el intento automático después de confirmar la orden y el registro durable en outbox. No se creó otro pedido vivo en esta comprobación, así que la entrega cloud-to-cloud con esta nueva bandera queda pendiente de una prueba autenticada.
- **Recuperación RDS:** se restauró una copia PITR temporal privada (`db.t3.micro`, sin Multi-AZ), se conectó desde una EC2 privada y la consulta de solo lectura encontró 10 tablas públicas. La copia temporal fue eliminada; la instancia original sigue `available`, privada, cifrada, Multi-AZ, con retención de 7 días. No se midió RTO/RPO formal ni se modificó la original.
- **Cola poison Azure:** se conservó intacto el mensaje observado, de `evt-c7508545eb85461dabc9c4d96621ec13`. El SHA-256 calculado del evento Blob coincide con su metadato, pero no con el hash del envelope de Queue; el Blob de resultado existe y el outbox AWS registra `delivered`, 1 intento. Esto indica una copia poison inconsistente de un evento ya entregado, no corrupción del Blob. No se borró ni reencoló. El health actual de la Function respondió `200`.
- **Roles/calidad:** la puerta local pasó 59 pruebas (22 base, 14 Azure, 23 release AWS) y el build frontend. Los tests ejercitan roles y permisos (admin/operaciones autorizados; ventas recibe 403 en consola/rutas restringidas) y el despacho automático. En el portal live el login admin respondió, pero la cookie `Secure` no viaja por HTTP loopback; no se desactivó esa protección y HTTPS confiable está diferido. La comprobación de roles live/autenticada queda pendiente.
- **Alcance intencionalmente excluido:** audio/video WebRTC entre navegadores y dominio/HTTPS confiable quedan pendientes para después, como pidió el usuario. No se probaron ni se cambiaron.
- **Pendiente próximo:** probar un pedido sintético nuevo desde sesión autenticada cuando haya HTTPS confiable; realizar revisión visual/manual de cada rol; acordar si archivar o retirar la copia poison ya diagnosticada (el evento ya fue entregado). El inventario de Azure continúa siendo demostrativo, no un WMS conectado a existencias empresariales.

## Resultado vivo del corte de 19:26 UTC (histórico, superado por la sección anterior)

Este bloque es la referencia vigente y **supera los resultados anteriores de este archivo**. El resto conserva la bitácora cronológica de los intentos/cortes previos.

- **Credenciales:** el perfil AWS CLI `default` se actualizó localmente con el token temporal compartido. STS autenticó correctamente contra la cuenta de laboratorio. No se copiarán credenciales ni claves a este archivo.
- **AWS:** el stack `tangamandapio-live-20261005` terminó `UPDATE_COMPLETE` (19:26 UTC). El ASG quedó con capacidad deseada 2; ambas EC2 están `InService/Healthy` y los dos targets del ALB están `healthy`. RDS `tangamandapio-postgres` está `available`, Multi-AZ, cifrado y retiene backups por 7 días; no se modificó ni restauró la base.
- **Rutas públicas:** ALB `/health` = `200`; `/platform` = `303` al login (ruta publicada y protegida); `/api/wms/inventory` sin autenticación = `401` (esperado). La sonda HTTPS omitió validar el certificado para poder observar el ALB; el certificado confiable para dominio propio sigue pendiente.
- **Azure:** `tangama-wms-fn` recibió el ZIP actualizado con build remoto. `/api/health` = `200`; hay cinco funciones publicadas, incluida `demo_inventory`. Se creó una clave de alcance de función para el endpoint de inventario y se sincronizó la clave activa desde Parameter Store hacia Secrets Manager. Se reiniciaron/revalidaron las dos EC2 gradualmente; ambas consultaron el inventario con autenticación y obtuvieron `200`.
- **Flujo integrado:** desde una EC2 se creó un pedido sintético con SKU `SKU-ARROZ-001`, cantidad 1. Quedó primero en el outbox duradero de AWS y se entregó mediante reintento manual a Azure. El worker registró `demo_fulfillment_completed`; el ledger ficticio bajó de 25 a 24. Reenviar el mismo evento no volvió a descontar (`idempotencia verificada`). No se usaron datos de clientes ni se tocó inventario real.
- **Modo de despacho:** `AUTO_DISPATCH_EVENTS=false`, por lo que por ahora el pedido requiere reintento manual en el portal. Se dejó así para no alterar silenciosamente el comportamiento de pedidos futuros.
- **Límite del WMS:** esto valida el flujo del proyecto con inventario de demostración en Azure Blob, no una conexión a un almacén/ERP empresarial ni una salida de stock comercial real.
- **Pendiente para cerrar:** reconciliar el template local CloudFormation contra el template/recursos vivos antes de otro `apply`; probar restore RDS aislado y medir RTO/RPO; inspeccionar y tratar con cuidado el mensaje poison histórico de Azure; probar la interfaz con login y matriz de roles; validar llamada A/V bidireccional en dos navegadores/redes; finalmente configurar dominio propio y HTTPS confiable.

## Revisión previa de solo lectura — 08/10/2026 (histórica)

El siguiente registro corresponde al estado anterior a renovar el token; se conserva para trazabilidad y no debe leerse como el estado actual.

- El ALB AWS respondió `/health` con HTTP 200 y `database=ok`, pero `/platform` devolvió 404; AWS STS rechazó la sesión CLI. Por eso solo se confirma la sonda de aplicación/DB, no el inventario de CloudFormation, la configuración viva de RDS, los destinos ni la revisión exacta del release. No se desplegó nada.
- Azure CLI indicó suscripción `Enabled`; la Function respondió HTTP 200 en `/api/health`, mientras `/api/wms/inventory` devolvió 404 sin clave. El ledger nuevo no está en la versión observada. No se publicó código Azure ni se hizo una operación de inventario.
- Las capturas/lecturas de inventario de 51 recursos y 2 destinos saludables descritas en la revisión Chrome son evidencia del momento registrado, no una afirmación de estado vigente permanente.
- Las pruebas locales se repitieron: 22 API base + 14 Azure + 22 release AWS = 58. `pnpm run build`, Terraform `fmt`/`validate` en ambos entornos y `cfn-lint` también pasaron. No se aplicó IaC ni se alteró el estado de las nubes.

## Intentos previos de desarrollo/despliegue (históricos; superados)

- Implementé localmente el vertical de WMS demo: catálogo con SKU/cantidad y stock inicial ficticio persistido en Azure Blob; lease + ETag para serializar escrituras; idempotencia por `event_id`; rechazo atómico por saldo insuficiente; eventos históricos sin líneas quedan `awaiting_items`.
- El panel local `/platform` añade inventario y botón “Generar pedido demo”. El backend guarda las líneas en la orden y en el outbox de AWS, restringe el botón/API a Administración y Operaciones, valida el saldo de Azure y audita el movimiento. No es un WMS/ERP comercial.
- La migración `0007_order_items` conserva artículos en SQLite/PostgreSQL. Pasaron las tres suites completas: 22 base + 14 Azure + 22 release AWS = 58 pruebas; JavaScript pasó `node --check`.
- Intenté publicar el paquete mínimo en `tangama-wms-fn` mediante Zip Deploy. El endpoint SCM/Kudu no respondió desde este equipo; cancelé la espera. El health existente sigue `200`, pero `/api/wms/inventory` sigue `404`; no hay evidencia de que el código nuevo esté desplegado y se debe tratar como pendiente. No envié eventos a la cola ni modifiqué/eliminé/reencolé manualmente el mensaje histórico con checksum discordante.
- La suscripción se mostró `Enabled` y el Portal mantiene la Function `En ejecución`; sin embargo, la consulta ARM del Function App y el endpoint SCM no completaron desde esta sesión. Se requiere recuperar acceso al plano de despliegue para subir y probar el paquete.
- AWS tampoco se desplegó: STS rechazó el token Academy con `InvalidClientTokenId`. El ALB continúa sin `/platform` (404), así que el botón no está en la web pública. No hubo cambios de IaC ni RDS; reconciliación, backup/restore y dominio/HTTPS siguen pendientes.

## Estado observado antes de renovar el token (histórico)

### AWS y portal

- AWS Academy muestra el laboratorio como Ready, con 2 h 28 min de sesión y “No running instance”.
- El perfil AWS CLI local default fue actualizado con el bloque temporal compartido para esta sesión, pero aws sts get-caller-identity responde InvalidClientTokenId. Hasta que STS entregue una identidad válida, no es seguro ejecutar despliegues, restauraciones o cambios de configuración.
- En el ALB se obtuvieron /health 200, /ready 200 y /api/auth/session 200. /platform devuelve 404, así que la consola de administración/operaciones aún no está disponible en el sitio público desplegado.
- La revisión manual en Chrome llegó al login del portal, sin iniciar sesión ni enviar credenciales. La interfaz pública se sirve; esta comprobación no demuestra que los flujos autenticados funcionen en AWS.

### Azure y WMS

- Azure CLI muestra la suscripción Azure for Students habilitada y el grupo rg-tangamandapio-261005-wus con Function App, plan, Storage, Key Vault, Application Insights, Log Analytics y alertas.
- Azure Portal muestra tangama-wms-fn en ejecución y cuatro funciones habilitadas. En Application Insights, process_fulfillment_message procesó evt-20261008-liveprobe-01 con Succeeded, DequeueCount: 1 y simulated_fulfillment_completed.
- La prueba de extremo a extremo anterior con evento sintético devolvió HTTP 202 y luego HTTP 200 con simulated_completed, mode=demo-only. No se modificó inventario real.
- Hay errores históricos de ejecución, incluido un mensaje con checksum inconsistente que llegó a cinco entregas. No se borró ni alteró el mensaje; se debe confirmar su cola poison y su contenido antes de decidir si se corrige o reencola.
- En esta revisión no se desplegó código nuevo ni se mutaron recursos Azure.

### Pruebas locales y recorrido visual

- Backend base: 22 pruebas aprobadas.
- Function Azure: 14 pruebas aprobadas.
- Release backend AWS: 22 pruebas aprobadas.
- Puertos locales del portal y consola de administración respondieron en salud HTTP. Chrome mostró el login local y el login del ALB. No se automatizó el acceso ni se registraron llamadas durante este recorrido.
- El usuario ha confirmado previamente que la telefonía funciona; no se volvió a validar audio/video entre dos navegadores en esta sesión.

## Bloqueo de inventario real

La implementación local ahora admite artículos SKU/cantidad, valida saldo en el catálogo de laboratorio y guarda líneas en el pedido/outbox. Sin embargo, el release vigente de AWS y la Function viva no se revalidaron ni publicaron en este corte; además, el ledger pertenece a la demostración Azure y no a un WMS empresarial. La manera de avanzar desde el ledger de demostración a un WMS real es:

1. Añadir artículos/SKU y cantidades al pedido en la API y el formulario.
2. Definir un catálogo y saldo inicial sintéticos, explícitamente identificados como inventario de laboratorio.
3. Aplicar reservas/salidas con idempotencia por evento, control de concurrencia y rechazo por stock insuficiente.
4. Mostrar en el portal la diferencia entre recibido, reservado, despachado y rechazado, y habilitar conciliación/reintentos auditados.
5. Conservar los mensajes poison y alertar; solo reencolar tras verificar que el evento y el Blob tengan el mismo hash.

Eso permitiría actualizar un inventario de demostración persistente en Azure, no el inventario de un ERP o almacén externo. Para afectar stock empresarial real hace falta integrar el WMS dueño de esos datos y su contrato aprobado.

## Reconciliación de IaC antes de publicar

El template local iac/cloudformation/aws-lab.yaml declara MultiAZ: false, BackupRetentionPeriod: 1 y DeletionProtection: false. El registro de la última verificación viva describía RDS privado, Multi-AZ, 7 días de backup y clase db.t3.micro. La lectura viva de hoy está bloqueada porque STS rechaza el token; por ello esto es una diferencia conocida, no una declaración de drift actual.

Cuando STS vuelva a autenticar:

1. Consultar describe-stacks, describe-stack-resources, get-template y describe-db-instances solo en modo lectura.
2. Comparar ID, estado, plantilla aplicada, parámetros, clase, Multi-AZ, almacenamiento/cifrado, retención, acceso público, subnet group y protección contra borrado.
3. Ajustar la IaC y revisar un change set sin ejecutarlo. No aplicar el template local antiguo sobre RDS ni recrear el stack a ciegas.
4. Publicar el panel administrativo como actualización de aplicación usando la plantilla y los recursos existentes, preferentemente con despliegue gradual y rollback verificado.

## Restauración, reintentos y recuperación

- RDS restore: pendiente. Crear solo una instancia de restauración temporal, privada, con nombre identificable de prueba y sin modificar la base original; verificar disponibilidad, conexión y recuperación de datos sintéticos. Eliminar únicamente esa copia de prueba tras guardar evidencia.
- Outbox AWS → Azure: las pruebas unitarias verifican duplicados/reintentos, pero falta una prueba viva en la que el WMS falle temporalmente, el pedido quede durable en outbox y un reintento entregue el mismo evento exactamente una vez a nivel de negocio.
- Azure Queue: inspeccionar la cola poison y conservar el mensaje con checksum discordante hasta identificar el evento. Después probar reencolado/reparación con un evento sintético válido y comprobar que no descuenta inventario dos veces.
- Recuperación web: publicar el panel solo después de que la validación de drift pase; comprobar el login, roles, consulta de estado y rollback sin tocar datos de clientes.
- Dominio y HTTPS confiable: se dejan para el final, como pidió el usuario.

## Criterio de cierre de sustentación

La parte de nube aún no se considera cerrada: la identidad ya autentica, el portal y el flujo WMS de demostración están publicados y comprobados; siguen pendientes la reconciliación IaC, restauración/recuperación evidenciada, tratamiento de poison queue, regresión autenticada de administración y dominio/HTTPS confiable. Las pruebas locales aprobadas no sustituyen estos pasos.
