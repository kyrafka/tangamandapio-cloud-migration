# Registro de nube y portal — cortes del 09/10/2026

## Nota de precedencia: estado final

El apagado posterior está documentado en
[`APAGADO_NUBE_2026-10-09.md`](APAGADO_NUBE_2026-10-09.md). Ese archivo es la
fuente vigente: los recursos AWS y Azure descritos abajo fueron eliminados; se
conserva solo un snapshot RDS cifrado de 20 GB. Este documento queda como
registro histórico del despliegue y las pruebas realizadas antes del apagado.

Este corte reemplaza como referencia actual al mapa del 08/10. No almacena
claves ni contraseñas.

## Consumo consultado

- **AWS Academy:** el panel marcó **US$21.40 usados de US$50** y **03:39** de
  laboratorio disponible tras reconstruir. Es el medidor del entorno académico,
  no una factura ni una proyección completa de los recursos recién creados.
- **AWS Cost Explorer:** el corte mensual devolvió un neto cercano a cero y
  negativo por créditos; no representa el costo bruto fiable del stack. Los
  cargos de infraestructura nueva pueden tardar en aparecer.
- **Azure:** el grupo activo `rg-tangamandapio-rebuild-wus` tiene 10 recursos.
  `az consumption usage list` no devolvió filas para ese grupo, así que el
  importe exacto **no está disponible**; no significa costo cero.

## Azure desplegado y verificado

- Suscripción habilitada; el único grupo activo del proyecto es
  `rg-tangamandapio-rebuild-wus` en West US.
- Function App `tangama-wms-261008`: `Running`, HTTPS-only; health respondió
  HTTP 200 (`status=ok`, `service=tangamandapio-wms`).
- Se verificó una recepción y venta sintéticas, con duplicados idempotentes
  (`queued_duplicate`). El worker informó `demo_restock_completed` y
  `demo_fulfillment_completed`; `SKU-ARROZ-001` terminó igual que al inicio
  (25 unidades). Un evento de un origen no autorizado se rechazó con HTTP 400.
  El modo `demo-inventory-ledger` es ficticio, no un ERP ni un WMS empresarial
  conectado.

## AWS reconstruido y verificado

- CloudFormation `tangamandapio-live-20261005`: `UPDATE_COMPLETE`, 45 recursos,
  cero recursos fallidos. El change set de la revisión ERP no reemplazó recursos
  ni modificó RDS; la detección posterior quedó `IN_SYNC`, cero recursos con
  drift.
- Stack separado `tangamandapio-voice-recordings`: `CREATE_COMPLETE`.
- Portal: [http://tangamandapio-alb-820217334.us-east-1.elb.amazonaws.com](http://tangamandapio-alb-820217334.us-east-1.elb.amazonaws.com)
  (`/health` HTTP 200, base de datos `ok`). ALB activo en dos zonas, 2/2
  destinos saludables después del rolling update; Auto Scaling 2 de 4.
- RDS PostgreSQL `available`, cifrada y privada. Multi-AZ apagado y backup de
  1 día para reducir gasto. Hay cuatro alarmas CloudWatch y dashboard
  `tangamandapio-operations`.
- Login admin verificado; la sesión ve 1 usuario inicial. Sin sesión, los
  endpoints de usuarios y pedidos responden 401.
- Un pedido sintético salió del portal y Azure lo aceptó. Estado final:
  `awaiting_items` (`simulated=true`), porque el release AWS no envía SKU ni
  cantidades; Azure no cambió el stock. Esta prueba confirma conectividad, no
  cumplimiento de inventario real.
- Se desplegó `20261009-erp-internal-mail`. Login admin y lectura de
  `/api/erp/access`, `/api/erp/overview`, `/api/erp/products` y
  `/api/erp/mail/users` respondieron correctamente; `/erp` y sus CSS/JS dieron
  HTTP 200. La integración a Azure mostró `connected`, `demo-inventory-ledger`
  y tres productos. La base reconstruida solo tiene un usuario interno (admin);
  las pruebas locales cubren permisos separados, no existen cuentas demo
  adicionales en producción.
- En el release AWS verificado, el correo era mensajería interna almacenada en
  PostgreSQL, sin SMTP configurado ni entrega externa. Finanzas cubre cuentas
  operativas y gastos básicos; no es contabilidad legal ni facturación tributaria.
- La URL de AWS es HTTP. Dominio/HTTPS confiable y prueba de audio/video entre
  dos navegadores siguen pendientes.

## Pruebas locales

- `tests/run_local_quality.ps1`: **68 passed** (API/app: 28; Azure Function: 17;
  AWS release: 23).
- Pruebas del artefacto AWS: login admin, ventas, compras/recepción, finanzas,
  outbox, permisos de rol y mensajería interna.
- Terraform Azure: el único cambio aplicado fue el setting de empaquetado de
  la Function; se documentó que Zip Deploy administra su URL SAS temporal para
  no permitir que un apply posterior reactive la versión anterior.
- Build frontend y `pnpm audit --prod`: aprobados; no se encontraron
  vulnerabilidades conocidas.
- `pip-audit` contra el lock de CI: aprobado; no se encontraron
  vulnerabilidades conocidas.
- Sintaxis Bash de `rebuild.sh` y `deploy.sh`: aprobada.
- `aws cloudformation validate-template`: aprobado.
- `git diff --check`: sin errores; Git solo advierte normalización LF/CRLF.

## Siguiente trabajo

1. Publicar y verificar en AWS los cambios locales posteriores solo después de
   revisar el inventario y tener sesión válida; probar roles con cuentas controladas.
2. Volver a consultar costos cuando la telemetría de facturación se actualice.
   Mantener el stack solo durante la ventana académica necesaria.
3. Configurar dominio/HTTPS y probar audio/video entre dos navegadores reales.

El state de Terraform Azure sigue local e ignorado por Git; antes de operar
desde otra máquina hay que configurar un backend privado o migrarlo con un
procedimiento seguro.

## Ampliación local de mensajería SMTP — 9 de octubre de 2026

Después del corte cloud se agregó al código local un adaptador SMTP configurable.
El mensaje se persiste primero en el buzón ERP; el resultado del relay se guarda
por separado, de modo que una caída SMTP no pierde el mensaje interno. El
destinatario se deriva de la cuenta y se restringe a un dominio interno
configurado; el usuario no puede escribir una dirección externa en el envío.
También se añadieron estado del transporte y prueba SMTP solo para administración.

La API se probó con un servidor SMTP local de prueba: handshake, remitente,
destinatario, contenido, estado `accepted_by_smtp`, prueba administrativa y
persistencia del mensaje cuando el relay rechaza la conexión. Las pruebas del
paquete AWS pasan por el mismo flujo SMTP. Docker Desktop no estaba activo, por
lo que Mailpit (configurado en Compose con SMTP `127.0.0.1:1025` y UI
`127.0.0.1:8025`) no se pudo levantar en esta sesión. El adaptador no está
configurado en AWS y no se envió correo a Internet: sigue haciendo falta un
relay real, dominio verificado, direcciones de buzón y autenticación
SPF/DKIM/DMARC.
