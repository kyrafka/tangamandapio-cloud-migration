# Revalidación cloud y recorrido en navegador — 16/10/2026 07:10–07:22 UTC

## Resultado del corte

- AWS STS aceptó el perfil local `default`. CloudFormation está
  `UPDATE_COMPLETE`; una detección nueva terminó `IN_SYNC` con cero recursos
  desviados a las 07:15:52 UTC. Los dos targets del ALB están saludables.
- El ASG conserva 2 de 2 instancias (mínimo 2, máximo 5). Las dos instancias
  actuales tienen volúmenes raíz EBS cifrados con KMS. El historial reciente
  muestra dos reemplazos exitosos después de que el chequeo EC2 sacara instancias
  detenidas/no saludables; conviene seguir observando estabilidad. La alarma de
  escala-in de CPU está en `ALARM`; la capacidad se mantiene en el mínimo.
- RDS está `available`, cifrado, Single-AZ y con retención de backup de un día.
  La restauración aislada anterior pasó; no se probó failover Multi-AZ.
- `https://tangamandapio.kendellnm.me/health` devolvió 200 en una petición
  normal. Terraform 1.16 consultó el backend remoto de Azure en modo
  `-refresh-only` y terminó `No changes`; no se aplicó infraestructura.
- Azure Function `tangama-wms-261008` responde HTTP 200. Application Insights
  registró en la última hora dos `receive_fulfillment_event` HTTP 202 y dos
  ejecuciones `process_fulfillment_message` con `resultCode=0`; el endpoint
  protegido de estado de la cola poison respondió 200. Las alertas de métrica
  5xx y latencia están habilitadas.

## Recorrido autenticado en Chrome

Se recorrió la sesión Admin existente en el dominio HTTPS, sin crear ni cambiar
datos:

- Resumen: AWS disponible, WMS conectado, 53 eventos entregados y cero pendientes.
- Pedidos: un pedido visible; su panel de detalle muestra pedido, outbox
  entregado y línea de tiempo WMS/auditoría.
- Integración WMS: paginación verificada de 53 eventos (30 en página 1, 23 en
  página 2). La consulta de un evento a Azure devolvió
  `demo_restock_completed` y explicitó que solo modifica el ledger sintético.
- Centro de nube: 2 destinos saludables, 2/2 instancias, CPU RDS 6.6% y cuatro
  conexiones al momento de la lectura; WAF figura no desplegado. La vista cargó
  los 13 SKU ficticios.
- ERP: 6 socios, 13 productos, 27 ventas, 25 compras y 56 documentos financieros;
  vistas de resumen, maestros, ventas, compras, finanzas y permisos cargaron.
  El acceso ERP separado muestra 3 cuentas con permisos de mínimo privilegio.
- Buzón: se verificó una entrega sintética al buzón del portal. La UI avisa que
  solo se envía copia SMTP si un relay está configurado; esta prueba aparece como
  `Buzón del portal`, no prueba entrega SMTP externa.
- Administración: 3 cuentas activas, 1 empresa, 2 suscripciones SNS confirmadas
  y 100 eventos de auditoría visibles.
- Telefonía: 2 extensiones disponibles, 3 llamadas históricas y una grabación
  de audio listada. No incluye video ni prueba una llamada bidireccional nueva.

## Prueba de carga y límite del proxy

`tests/performance/load_test.py` envió 300 GET concurrentes (concurrencia 15)
al dominio HTTPS y recibió 300 respuestas Cloudflare `403`, error 1010. Una
petición con el User-Agent Python también recibió ese bloqueo; una petición
normal desde PowerShell y el navegador Chrome sí dieron 200. Por tanto, esta
prueba **no llegó a medir la aplicación** y no se considera una prueba de
rendimiento aprobada ni una caída del portal. No se modificó ni se eludió la
regla del proxy. El JSON crudo está en
[`AWS-READONLY-LOAD-2026-10-16-0710UTC.json`](aws/AWS-READONLY-LOAD-2026-10-16-0710UTC.json).

## Pendientes que siguen abiertos

- Carga sostenida y observación de escalado 2↔3 con un cliente autorizado por
  Cloudflare; el último intento externo fue bloqueado antes del ALB.
- Prueba WebRTC de audio/video bidireccional con dos navegadores reales.
- Integración de red privada AWS–Azure: hoy el E2E usa HTTPS público; AWS
  Academy limita `CreateCustomerGateway` por SCP.
- Failover Multi-AZ y retención/restore más robustos; el RDS actual es Single-AZ
  con un día de backups.
- WAF administrado no está desplegado. No se desactivaron protecciones de
  Cloudflare ni se habilitó un bypass.
- Recorrido visual con Comercial y Operaciones, validación de exportación CSV,
  captura/correlación de alerta Azure y atribución confiable de costos.
- Estado final de CI del commit que incorpore esta evidencia.

No hubo `apply`, reinicio de instancia, cambio de credenciales, alta de usuario,
envío de correo externo ni modificación del inventario sintético en este corte.
