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
- A las 19:35 UTC, portal `/health` devolvió HTTP 200 (`status=ok`), `/ready`
  devolvió HTTP 200 (`status=ready`) y Azure Function `/api/health` devolvió
  HTTP 200 (`status=ok`).
- A las 19:39 UTC, `aws sts get-caller-identity` volvió a devolver
  `ExpiredToken`; no se validaron RDS, drift ni configuración vigente por API
  de AWS.
- La plantilla en CloudFormation muestra explícitamente el artefacto v12 y no
  contiene las variables de entorno que necesita la integración CloudWatch
  (`CLOUDWATCH_LOAD_BALANCER_FULL_NAME`, `CLOUDWATCH_RDS_INSTANCE_ID` y
  `CLOUDWATCH_REGION_NAME`). Esto coincide con el panel publicado que muestra
  las métricas como no configuradas.
- El candidato local v13 es reproducible por identidad: el artefacto
  `artifacts/portal-b2b-20261015-cloudwatch-wiring-v13-python312-d0e4f6b6ccadff7eb1edac2026211d081c2f1df941c6884e64ff0cab2e2c9c57.tar.gz`
  existe (18,191,553 bytes) y su SHA-256 coincide con el sufijo de su nombre.
  El listado visible del prefijo productivo S3 contiene 10 objetos, incluido
  v12, pero no v13. No se subió ni desplegó nada en esta pasada.
- Es un smoke visual del usuario administrador, no una prueba exhaustiva de
  todos los roles, flujos de escritura, entrega SMTP ni llamada WebRTC real.
