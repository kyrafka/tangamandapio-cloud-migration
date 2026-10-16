# Revalidación AWS–Azure, roles y fuentes de rúbrica — 16/10/2026, 03:41 UTC

## Estado vivo de nube

- AWS STS autenticó en la cuenta Academy esperada con el perfil `default`.
- CloudFormation `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; el estado
  reportado de drift es `IN_SYNC` (última detección 03:31:54 UTC). No se cambió
  infraestructura en esta revisión.
- ALB HTTPS 443 reenvía a la aplicación y el listener HTTP 80 redirige a HTTPS
  con 301. ACM está `ISSUED` para `tangamandapio.kendellnm.me`, con vencimiento
  el 30/04/2027. El dominio y `/health` del portal devolvieron 200; Azure
  `/api/health` también devolvió 200 con TLS validado por el cliente.
- ASG `tangamandapio-asg`: deseado/mínimo 2, máximo 5; 2/2 instancias
  `InService`/`Healthy`; el target group tiene 2/2 destinos `healthy`.
  Target tracking usa CPU promedio objetivo 60%.
- En el historial del ASG aparecen intentos de lanzamiento cancelados con
  `Client.InternalError` entre 00:51 y 01:20 UTC, seguidos por dos lanzamientos
  exitosos que elevaron la capacidad de 0 a 2 a las 01:52 UTC. La causa de los
  fallos iniciales no queda explicada; la capacidad actual sí está sana.
- La alarma target-tracking de CPU baja está `ALARM`: registró tres puntos
  1.158%, 1.352% y 1.175%, debajo de su umbral de 42%. Es coherente con escala
  hacia abajo; la política no puede bajar de la capacidad mínima de dos. Las
  alarmas de CPU alta, capacidad InService, RDS CPU, 5xx y destinos no sanos
  están `OK`, habilitadas y con una acción cada una. Esta observación no prueba
  escalado bajo carga ni una notificación de usuario.
- RDS PostgreSQL 18.3 está `available`, `db.t3.micro`, cifrada y no pública;
  permanece **Single-AZ** con retención de backup de **un día**.
- WAFv2 no lista Web ACL regional para esta cuenta/región.

## Smoke autenticado de solo lectura

El runner `run_public_portal_admin_readonly.ps1 -PortalTarget alb-origin-https`
terminó `LIVE_ADMIN_READONLY_SMOKE_PASSED`. Conservó el hostname del dominio y
la validación TLS al conectar directamente al ALB. La autenticación y el cierre
de sesión generan entradas normales de auditoría; no crean órdenes, compras,
gastos ni movimientos de stock.

- Admin: consola autenticada; el tablero concilia 1 pedido visible y 49/49
  eventos entregados, 0 pendientes. La consulta está completamente paginada.
- Suscripciones SNS: 2 confirmadas y 0 pendientes.
- Comercial: ventas `200`; WMS, outbox, administración y suscripciones `403`.
- Operaciones: WMS y outbox `200`; ventas, administración y suscripciones `403`.
- El smoke no disparó una alarma de prueba. La alarma de escala-baja descrita
  arriba ya estaba activa por CPU reducida.
- La autenticación automatizada a través del FQDN proxied recibió 403 de
  Cloudflare en una tentativa previa. No se identificó la regla exacta. No se
  cambió ni evitó la configuración de Cloudflare.
- El control de Chrome no pudo identificar con confianza la URL actual de la
  ventana; por política se detuvo. No hay verificación visual nueva de módulos.

## Validación automática y publicación

- El gate local vigente: 213 pruebas Python, 14 Node, build Vite, auditorías de
  dependencias, `cfn-lint`, Terraform `fmt`/`init`/`validate` y pruebas mock;
  todo pasó sin `terraform apply`.
- Commit `84b97bfb31d442181e618dba26f4043fd0dc82ed` quedó en la rama GitHub
  `codex/aws-v11-deploy-sync`. Sus tres jobs concluyeron `success`: validación
  AWS/Azure, backend/worker/flujo y build/auditoría frontend.
- La plantilla almacenada originalmente en CloudFormation todavía conserva
  defaults del artefacto v16; los parámetros efectivos desplegados usan v18 y
  coinciden con el origen local. AWS rechazó el change set que no producía
  cambios efectivos. No se forzó una actualización vacía.

## Cotejo de las rúbricas disponibles

- Las copias `rúbrica proyecto_qod3szrctm.xlsx` (incluidas las variantes
  `(1)`–`(3)` en Descargas) son idénticas, SHA-256
  `945DEC8DFEAE387B35A49CAE0CBA6CDE4C81BE24F741DB8989E52DAAC78D7BAE`. Los 14
  máximos visibles suman **18.5**, aunque la celda TOTAL dice **20**. No hay una
  fórmula o criterio oculto que explique los 1.5 puntos.
- El PDF general `rúbrica de evaluacion de proyecto de fin de
  ciclo_llss4pnf0z.pdf`, SHA-256
  `5F1BBB9284AB25E4FC960D162236C758B34091EE24B9FA2C048153C14CBF94C3`, contiene
  otros bloques: diseño de red, virtualización, servicios TI, cloud computing,
  documentación y defensa. Los máximos por bloque visibles son 20, 20, 20, 10,
  10 y 10 (suman 90); no corresponde a la hoja específica AWS–OCI/Azure ni
  explica la diferencia de esta última. No se normalizaron ni combinaron las
  dos escalas.
- Se requiere confirmar con el docente cuál instrumento aplica y cómo debe
  ponderarse al máximo anunciado antes de publicar una nota numérica.

## Brechas que siguen abiertas

- Conectividad privada AWS–Azure: AWS Academy denegó la creación de Customer
  Gateway por SCP y no hay VNet Azure; el E2E funcional usa HTTPS público.
- Resiliencia RDS: no es Multi-AZ, tiene un día de retención y no se midió un
  failover. La restauración PITR con RTO/RPO documentados es evidencia anterior,
  no repetida aquí.
- Capacidad: no se ejecutó carga representativa por ALB ni se demostró que el
  ASG escale. Las 24 lecturas previas fueron una sonda loopback pequeña.
- Protección/observabilidad: no hay WAF; falta disparar y recuperar una alarma
  sintética con evidencia de entrega. Las suscripciones SNS están confirmadas.
- Interfaz: falta recorrido manual visual por módulos y carga CSV en navegador;
  WebRTC bidireccional entre dos navegadores tampoco se probó en este corte.
- Costos: AWS mostró US$26.0033 de uso bruto y −US$26.0033 de créditos para toda
  la cuenta Academy del 1 al 15/10, sin atribución exclusiva al proyecto. Azure
  devolvió 255 filas con `pretaxCost=None`; falta un importe fiable.
- Evidencia visual reciente de inventario AWS e invocación/monitor Azure sigue
  pendiente.

El ledger WMS y los documentos ERP/Finanzas son operativos con datos sintéticos
en el alcance de demostración. No representan inventario físico ni
contabilidad legal; el buzón es interno al portal y no usa SMTP externo.
