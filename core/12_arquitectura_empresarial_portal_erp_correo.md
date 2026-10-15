# Arquitectura empresarial objetivo — datacenter, portal, ERP y servicios corporativos

**Corte documental:** 14/10/2026, 10:37 America/Chicago
**Tipo:** organización de alcance y plan de evolución; no es inventario de servicios desplegados.

## 1. Aclaración de alcance

El proyecto hermano sirve como **referencia del problema del datacenter corporativo centralizado**: aplicaciones internas concentradas, varias sedes, crecimiento, disponibilidad, segmentación, protección de datos y continuidad. Sus cifras de personal pertenecen a ese caso y no se trasladan a Tangamandapio.

Tangamandapio es el caso propio: distribuidora mayorista, retail omnicanal y logística. El registro maestro fija 450 colaboradores, 220 cuentas internas, centros en Lima, Arequipa y Trujillo y hasta 3,000 usuarios externos concurrentes en campañas. La expansión a distribuidores internacionales es una **meta de diseño**, no una sede ni una carga ya medida.

El portal B2B, el ERP, el WMS y el correo corporativo son capacidades diferentes. Para el prototipo actual, portal, ERP ligero y mensajería interna viven en la misma web y comparten la autenticación, pero se separan por módulos, permisos, tablas y APIs. Azure sigue siendo autoridad de inventario WMS; el ERP consulta existencias y publica eventos. Si la carga o la complejidad financiera crecen, el ERP puede extraerse a un servicio independiente sin convertir al portal en dueño del stock.

## 2. Sistemas y límites de responsabilidad

| Sistema | Usuarios y responsabilidad | Fuente de verdad | Situación comprobada en este repositorio |
|---|---|---|---|
| Portal B2B | Distribuidores/clientes: catálogo publicado, creación y seguimiento de pedidos | Identidad externa, carrito/solicitud y estado visible del pedido | Release v9 desplegado en AWS detrás del ALB; API y persistencia PostgreSQL/RDS activas. El ALB aún usa HTTP público; dominio/HTTPS quedan para el cierre. |
| ERP corporativo | Personal autorizado: ventas internas, compras, finanzas operativas, clientes, productos y procesos administrativos | Maestros y transacciones ERP; en este prototipo, el ledger sintético de inventario vive en Azure | Módulo propio desplegado dentro del portal; ventas, compras, documentos CxC/CxP y datos maestros se probaron E2E. No usa Odoo ni es contabilidad legal/tributaria. |
| WMS de demostración | Procesamiento de eventos de fulfillment y reposición con SKU/cantidad | Ledger Blob de inventario sintético para la demostración académica | La Function Azure y Queue están activas; tres ventas y una recepción QA desde el portal AWS llegaron a `completed_demo`/`received_demo`. El stock es ficticio por diseño, no un criterio pendiente ni inventario comercial. |
| Correo y colaboración | Colaboradores: mensajes internos en el portal; entrega opcional mediante relay SMTP | El portal conserva el mensaje; SMTP solo transporta una copia y reporta aceptación/rechazo | Buzón interno persistente integrado al portal. Adaptador SMTP opcional probado contra servidor de prueba local; AWS no tiene relay productivo configurado. No hay IMAP, buzones corporativos ni entrega pública verificada. |
| Identidad corporativa | Personal: inicio de sesión, MFA, grupos y acceso a ERP/administración | Directorio corporativo | Se debe definir tenant y SSO corporativos. Las cuentas demo del portal no equivalen a un directorio empresarial. |
| Integración | Conecta portal, ERP, ledger WMS de demo y notificaciones sin acoplar bases | Contratos versionados, `order_id`, `event_id` e idempotencia | Recorrido autenticado AWS/PostgreSQL→outbox→HTTPS público Azure/Queue/Function probado; 7/7 eventos outbox entregados en la verificación. VPN privada AWS–Azure no está desplegada. |

### Decisión funcional pendiente: ERP y WMS

Para el alcance académico actual, el WMS Azure es explícitamente un simulador con inventario sintético; eso no es una falta de stock real. La Function valida el contrato cloud y la secuencia de ventas/recepciones. Si una futura operación real requiere radiofrecuencia, olas de picking, múltiples ubicaciones, lotes/series o existencias comerciales, se debe elegir e integrar un WMS empresarial con API y propiedad de datos explícita, fuera de este prototipo.

No se seleccionó Odoo ni otro ERP empaquetado: la primera iteración es un módulo propio dentro del portal porque permite probar los flujos académicos en el mismo acceso y mantener Azure como autoridad WMS. Si el alcance financiero supera el registro operativo actual, se evaluará un ERP dedicado con localización peruana, licencias, facturación electrónica, soporte, seguridad, costo y actualización antes de migrar datos. No se debe afirmar cumplimiento tributario por tener cuentas por cobrar/pagar.

## 3. Arquitectura lógica objetivo

```text
Distribuidores nacionales e internacionales
                  │ HTTPS
                  ▼
          AWS: WAF → ALB → Portal B2B / API
                              │ pedidos y consulta de estado
                              ▼
                 Datos propios del portal + outbox
                              │ API/evento autenticado, idempotente
                              ▼
                 Capa de integración / adaptadores
                      ┌───────┴────────┐
                      ▼                ▼
             ERP corporativo      WMS elegido (si separado)
             y datos maestros     ejecución física de almacén
                      └───────┬────────┘
                              │ resultado de cumplimiento
                              ▼
                    Estado publicado al portal

Personal ── identidad corporativa/MFA ── ERP y consola interna
Personal ── Microsoft 365/Exchange + SharePoint/OneDrive (opción SaaS)
Sedes ── conectividad privada/SD-WAN/VPN solo para apps privadas necesarias
AWS/Azure ── integración de servicio por HTTPS y credenciales de servicio;
             VPN entre nubes solo si un requisito de red privada lo exige.
Observabilidad, auditoría, copias y recuperación atraviesan todos los dominios.
```

El portal no consulta tablas del ERP directamente. Publica una orden con identificadores, líneas SKU/cantidad, empresa y versión de contrato. El ERP valida catálogo/precio/cliente y confirma o rechaza; el WMS ejecuta la preparación si corresponde. Los estados vuelven al portal por API/evento. Reintentos, DLQ, correlación y conciliación evitan perder operaciones sin simular una transacción distribuida.

## 4. Mapeo de capacidades y servicios candidatos

La siguiente tabla es una **propuesta por necesidad**. Solo el estado explícito de cada servicio en el mapa de inventario cuenta como desplegado.

| Capacidad | Ubicación/servicio candidato | Para qué sirve en el caso | Estado |
|---|---|---|---|
| Canal externo y protección perimetral | ALB y portal/API en ASG/EC2 según IaC actual; WAF es opcional | Aislar entrada pública, distribuir tráfico y sustituir nodos con fallos | El release v10 quedó aplicado y saludable a las 12:17; el ALB devolvió 503 a las 13:03. STS autentica, pero lecturas de ELB/EC2/ASG/RDS y anteriores de CloudFormation/SSM están denegadas. Sigue HTTP hasta el cierre de HTTPS. |
| Persistencia del canal | RDS PostgreSQL privada; S3 privado para objetos/respaldos | Pedidos/outbox del portal y archivos autorizados | Último inventario válido: RDS disponible, cifrada y privada; Single-AZ/1 día. No fue posible revalidarla después del 503 por denegación AWS. Restore aislado tiene evidencia histórica. |
| Automatización logística de demo | Azure Functions, Queue, Blob privado y Managed Identity | Recibir/encolar y observar eventos del contrato | Function `Running`; `/api/health=200`; Terraform `No changes`. El inventario procesado es sintético. |
| ERP | Módulo propio dentro del portal; futura extracción si lo exige el crecimiento | Ventas, compras, finanzas operativas y maestros; consulta el ledger sintético Azure | Desplegado y probado con cuentas/roles; no es contabilidad legal/tributaria ni ERP empresarial certificado. |
| WMS empresarial | Módulo de inventario/almacén del ERP o producto WMS conectado, solo si el caso de producción lo requiere | Operación física de centros con existencias comerciales | No seleccionado; fuera del alcance del ledger de demostración actual, no una falta de datos sintéticos. |
| Correo interno del prototipo | Bandeja del portal/ERP + transporte SMTP opcional; Mailpit local en Compose | Persistencia del mensaje, estado del relay y entrega de copia a buzones configurados | Buzón interno desplegado; pruebas SMTP locales aprobadas. SMTP productivo no está configurado en AWS. |
| Correo corporativo real | Relay corporativo o proveedor de salida SMTP + cuentas de usuario | Buzones, calendario, colaboración y archivos según solución elegida | Pendiente; requiere direcciones reales, dominio controlado/verificado, TLS, SPF/DKIM/DMARC y gestión segura de credenciales. SMTP no sustituye IMAP ni crea buzones. |
| Notificaciones de aplicación | Un proveedor transaccional, por ejemplo Amazon SES, con SPF/DKIM/DMARC del dominio | Avisos de pedido, alertas y correo automatizado; no buzones | Fase posterior; requiere dominio y consentimiento de destinatarios |
| Identidad y administración | Entra ID/SSO corporativo o proveedor definido; MFA, grupos, roles y cuenta break-glass | Acceso individual a aplicaciones internas | Diseño pendiente; no confundir con usuarios demo |
| Telemetría y auditoría | CloudWatch/CloudTrail en AWS; Azure Monitor/Application Insights en Azure | Salud, errores, latencia, cola, cambios y seguimiento de pedido | Alarmas AWS activas; Azure tiene reglas/receptores configurados, pero prueba oficial de entrega no disponible en suscripción Free. |
| Resiliencia y datos | Backups cifrados, retención, restauraciones aisladas y RTO/RPO | Recuperar pedidos y documentos ante borrado/falla | Restore aislado validado; la BD productiva mantiene Single-AZ/1 día, así que la HA de RDS no está alcanzada. |
| Red de sedes y multinube privada | VPC/VNet segmentadas; VPN/SD-WAN solo para consumo privado | Conectar sedes y servicios privados con control | Último inventario AWS confirmó VPC; VPN AWS–Azure no desplegada. El intercambio probado usa HTTPS público; no se pudo revalidar el plano AWS a las 13:03. |

Evitar agregar productos duplicados sin un requisito medible. Por ejemplo, no montar simultáneamente un WMS separado y stock ERP sin acordar cuál manda; tampoco desplegar VPN AWS–Azure solo porque se usan dos nubes para intercambiar eventos HTTPS.

## 5. Requisitos empresariales a convertir en pruebas

1. Un distribuidor solo consulta su empresa, catálogo autorizado y pedidos propios; un usuario interno recibe permisos por rol y función.
2. Un pedido incluye líneas SKU/cantidad y referencia de catálogo; un evento conserva el mismo identificador al reintentarse.
3. En la demostración, ERP publica ventas/recepciones y Azure actualiza el ledger sintético; una integración con WMS empresarial solo se requeriría si el alcance cambia a operación real.
4. Una falla de ERP/WMS no pierde el pedido: se conserva el evento, se reintenta con límites y se alerta en DLQ sin duplicar efectos.
5. Inventario, pedido y estados muestran propietario del dato, sello temporal y fuente; un ledger de laboratorio nunca aparece como stock real.
6. Personal interno usa MFA y cuentas individuales; los servicios usan identidades administradas/roles mínimos, no claves permanentes.
7. Se mide concurrencia objetivo de 3,000 usuarios externos con carga sintética y criterios de latencia/error acordados; no se infiere capacidad por la presencia de un ASG.
8. Backups se restauran en un entorno aislado y se registran duración, pérdida de datos observada, RTO y RPO.
9. Mensajes internos del portal, notificaciones SMTP y buzones de correo corporativo se tratan como servicios distintos; la autenticación de dominio se habilita cuando exista un dominio controlado por la empresa.
10. Cada fase cloud registra inventario inicial/final, presupuesto/alarma, pruebas, evidencia y apagado cuando corresponda.

## 6. Plan de organización e implementación

| Fase | Resultado | Puerta antes de avanzar |
|---|---|---|
| A — Verdad y alcance | Documento, diagrama, matriz hecho/objetivo y brechas con cortes fechados | Mantener mapa cloud sincronizado y no tratar datos sintéticos como inventario comercial |
| B — Diseño funcional | Dueño de datos por objeto; decisión ERP vs WMS; procesos de ventas, compra, recepción, stock, despacho, devoluciones y usuarios externos | Validar con caso académico; identificar requisitos de localización y rúbrica |
| C — Plataforma base | AWS/Azure desplegados por IaC, redes, secretos, logs, presupuesto y respaldos | CloudFormation `UPDATE_COMPLETE`; Terraform activo `No changes`; HA RDS y HTTPS público siguen pendientes |
| D — Módulos con límites claros | Portal/ERP y mensajería interna en misma web con APIs/tablas/permisos separados; Azure procesa ledger sintético | Implementados y probados por rol en API; falta inspección visual de vistas autenticadas y relay SMTP productivo |
| E — Integración operativa | API/eventos versionados, idempotencia, reintentos, DLQ y conciliación con datos sintéticos | Tres ventas y recepción QA desde AWS a Azure aprobadas; repasar poison queue y registrar evidencia visual |
| F — No funcionales | Carga, escalado, permisos, alarmas, restauración, RTO/RPO y costos | Carga solo local; restore aislado probado; falta carga/HA cloud y alerta Azure real |
| G — Presentación | Informe, capturas limpias de consola, recorrido del portal y límites | Dominio/HTTPS y A/V WebRTC quedan para el cierre acordado; no declararlos probados aún |

### Trabajo inmediato recomendado en el repositorio

1. Mantener un único mapa de inventario cloud y actualizar `README.md`/registro maestro con el estado activo fechado.
2. Mantener `core/12` como referencia de límites de sistema y enlazarlo desde propuesta, registro y README.
3. Convertir los requisitos de la sección 5 en matriz requisito→API/IaC→prueba→evidencia.
4. No desplegar un WMS empresarial ni aplicar cambios de HA/costo sin revisar arquitectura, licencias, seguridad, costo y change set.

## 7. Verdad del despliegue

Al corte operativo más reciente del 14/10/2026 (13:03), no se puede afirmar disponibilidad del portal AWS: el ALB respondió 503, STS autenticó y las lecturas de ELB/EC2/Auto Scaling/RDS fueron denegadas; CloudFormation/SSM también estaban denegadas en lecturas previas. El último inventario anterior (12:17) observó v10 y dos destinos sanos. Azure Function health respondió 200 a las 13:03; el smoke compensado más reciente usó un productor local/SQLite, no AWS. El último plan Terraform Azure terminó `No changes` a las 12:40. El E2E portal AWS→Azure está probado en un corte anterior, pero debe repetirse una vez recuperado AWS. El ledger WMS es simulación académica por diseño, no stock comercial. SMTP productivo no está configurado en AWS, y el buzón interno del portal no equivale a correo corporativo SMTP/IMAP. No se debe inferir disponibilidad por el mero hecho de que exista IaC.

La diferencia entre objetivo y realidad es intencional: una arquitectura completa puede incluir sistemas aún no seleccionados, pero debe rotularlos como decisión/candidato, no como logro. Para la rúbrica, confirmar además por escrito el alcance AWS–Azure frente a la plantilla que todavía menciona AWS–OCI.
