# Smoke visual admin del portal publicado — 15/10/2026, 19:30–19:34 UTC

Revisión manual en la pestaña de Chrome del portal publicado por HTTPS,
después de que el usuario iniciara sesión como administrador. Solo navegación,
lectura de tablas y filtros; no se crearon ni modificaron pedidos, usuarios,
inventario, pagos, compras, ventas, mensajes o configuración cloud.

## Resultado por módulo

- **Autenticación e inicio:** el portal reconoce `admin@tangamandapio.local` y
  carga los datos del resumen.
- **Pedidos:** se mostró el pedido sintético visible; buscar por referencia y
  limpiar el filtro funcionó sin cambiar registros.
- **Integración WMS:** la tabla mostró 39 eventos entregados, 0 pendientes y
  paginación funcional (10 por página, 3 páginas). Consultar el estado de un
  evento existente devolvió `demo_restock_completed` para el pedido #18. El
  mensaje de la UI confirma que corresponde al ledger ficticio de Azure, no a
  existencias de un ERP real. La consulta no creó otro movimiento.
- **Administración:** se cargaron 3 cuentas activas, 1 empresa y 2 destinatarios
  de alertas confirmados. La vista de auditoría presentó 100 registros y el
  login admin de esta sesión aparece en la lista. No se editaron permisos ni
  destinatarios.
- **Telefonía:** cargó el directorio con 2 cuentas disponibles; se veían 0
  llamadas y 0 grabaciones. No se inició llamada: no había un segundo navegador
  participante disponible para verificar audio/video de extremo a extremo.
- **Consola de plataforma:** muestra Azure WMS conectado, 14 productos de
  inventario sintético y 39 eventos entregados. Los paneles de métricas AWS
  indican que faltan identificadores de recursos CloudWatch; por ello no hay
  series útiles de ALB, RDS, WAF o Auto Scaling en esta vista publicada.
- **ERP — resumen:** cargó 20 ventas, 18 órdenes de compra, S/ 304.50 por cobrar
  y S/ 251.00 por pagar. El propio módulo identifica como ficticias las
  existencias y aclara que las finanzas son seguimiento operativo, no
  contabilidad legal.
- **ERP — maestros:** cargaron 6 socios y 13 productos; se mostraron cantidades
  consultadas al ledger Azure de demostración. Los controles de alta e importación
  se inspeccionaron, pero no se usaron.
- **ERP — ventas/compras:** cargaron 20 ventas y 18 compras con detalle SKU y
  estados `completed_demo` / `received_demo`. Aparecen múltiples documentos QA
  repetidos asociados al cliente/proveedor de prueba `QA LIVE AWS Azure v10`;
  esta pasada no añadió ninguno.
- **ERP — finanzas:** 38 documentos aparecen abiertos. Las acciones de registrar
  pagos, cobros o gastos no se ejecutaron.
- **ERP — accesos:** se muestra la tabla granular de permisos para las 3 cuentas;
  solo lectura. Esta revisión valida la vista con rol administrador, no demuestra
  el aislamiento efectivo de permisos para Comercial y Operaciones.
- **ERP — correo:** la entrada figura vacía y enviados contiene 1 mensaje. La UI
  aclara que el buzón es interno y que aceptar SMTP no prueba entrega externa;
  no se redactó ni envió correo.

## Navegador y límites de verificación

- La consulta de errores y advertencias de la consola Chrome devolvió una lista
  vacía durante la revisión.
- Con Python 3.12 y el lock de CI en un entorno temporal aislado pasaron 17
  pruebas API/flujo, 31 de Azure Function, 46 del release AWS y 23 de preflight
  cloud. También pasaron el chequeo del lock, la compilación Python y `cfn-lint`.
  En frontend pasaron 8 pruebas de navegación por rol, 6 de CSV y
  `pnpm run build:check`. El CI del commit `8a1fe81` también quedó verde en sus
  tres jobs (backend/Azure, frontend y validación de infraestructura).
- Revalidación a las 19:49 UTC: portal `/health` HTTP 200 (`status=ok`),
  `/ready` HTTP 200 (`status=ready`) y Azure Function `/api/health` HTTP 200
  (`status=ok`).
- A las 19:49 UTC, `aws sts get-caller-identity` volvió a devolver
  `ExpiredToken`; no se validaron RDS, drift ni configuración vigente por API
  de AWS.
- A las 19:47 UTC, AWS Academy mostraba el laboratorio `ready` y un uso de
  `$29.6 de $50`; esto no renueva automáticamente las credenciales del CLI
  local.
- La plantilla en CloudFormation muestra explícitamente el artefacto v12 y no
  contiene las variables de entorno que necesita la integración CloudWatch
  (`CLOUDWATCH_LOAD_BALANCER_FULL_NAME`, `CLOUDWATCH_RDS_INSTANCE_ID` y
  `CLOUDWATCH_REGION_NAME`). Esto coincide con el panel publicado que muestra
  las métricas como no configuradas.
- El artefacto local v13 existía (18,191,553 bytes) y su SHA-256 coincidía con
  el sufijo; una revisión posterior desde el checkout Linux detectó que la
  empaquetación no era reproducible entre Windows (CRLF) y Linux (LF). Por
  eso no se publicó v13. La corrección de normalización está incluida en v14
  abajo; se debe contrastar también desde CloudShell antes de subirlo.
- Es un smoke visual del usuario administrador, no una prueba exhaustiva de
  todos los roles, flujos de escritura, entrega SMTP ni llamada WebRTC real.

## Revisión interactiva adicional — 15/10/2026, 20:00 UTC

El administrador inició sesión y se recorrieron las vistas en Chrome. Se usó
solo lectura y navegación; no se crearon ventas/compras, no se registraron
cobros, no se editaron permisos y no se agregaron alarmas.

- **Pedidos:** la tabla cargó 1 pedido sintético. El detalle abrió y mostró la
  línea de tiempo del outbox y del WMS.
- **WMS:** directorio con 39 eventos entregados y 0 pendientes; las 3 páginas
  avanzaron correctamente. El centro de plataforma cargó 14 SKU con saldos
  sintéticos y aclaró que el ledger de Azure no es un inventario ERP real.
- **ERP:** resumen, maestros (6 socios y 13 SKU), ventas (20), compras (18),
  finanzas (38 documentos) y accesos (3 cuentas) cargaron. El buzón mostró el
  mensaje interno existente; no se probó envío ni entrega SMTP.
- **Administración:** 3 cuentas activas, 1 empresa y 2 destinatarios SNS
  confirmados. La auditoría mostró 100 eventos recientes. No se probaron
  cambios ni restablecimientos.
- **Telefonía:** admin y dos extensiones autorizadas aparecen disponibles; no
  se inició llamada porque no había otro navegador con sesión autenticada para
  contestar.
- **Hallazgo confirmado:** la portada de «Nube, seguridad y capacidad» muestra
  las 8 series CloudWatch como «No configurado» aunque las consultas
  administrativas de AWS CloudShell sí encontraron métricas del ALB, RDS y
  ASG. La plantilla local se está actualizando para pasar los identificadores
  reales de esos recursos al panel.
