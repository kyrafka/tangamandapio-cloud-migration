# Plan maestro de pruebas AWS–Azure

**Corte vigente:** 16/10/2026, 04:24 UTC. Los antecedentes conservan su fecha;
una prueba histórica no sustituye una revalidación cuando hubo cambios.

## Estado actual

- AWS Academy autenticó en `default` (cuenta `841113066612`). El stack está
  `UPDATE_COMPLETE`; una detección fresca terminó `IN_SYNC` a las 04:23 UTC.
- ACM figura `ISSUED` hasta 30/04/2027 y el listener HTTP redirige a HTTPS.
  El ALB está activo; ASG
  deseado/mínimo 2, máximo 5, con 2/2 instancias `InService/Healthy` y 2/2
  targets `healthy`.
- Dominio HTTPS `/health` devolvió `200`, HTTP redirigió `301` a HTTPS y Azure
  WMS `/api/health` devolvió `200`. El smoke autenticado por TLS directo al
  origen ALB pasó roles y concilió 49/49 eventos; SNS tiene 2/2 suscripciones
  confirmadas.
- RDS está disponible, cifrada y privada; es Single-AZ y conserva un día de
  backup. PT-DR-01 ya documentó restore aislado (RTO 260 s, RPO observado ≤8 s),
  pero falta un failover.
- En esta revalidación, las cinco alarmas consultadas están `OK`. La alarma de
  5xx no recibió datapoints y los faltantes cuentan como `NonBreaching`, así que
  su estado no demuestra que haya observado tráfico. El ciclo sintético de SNS
  y recepción/recuperación ya pasó el 14/10.
- Pruebas sintéticas históricas demostraron scale-out e in 2↔3; falta carga
  transaccional medida a través del ALB. No se afirma capacidad para 3,000
  usuarios.
- La prueba Admin de solo lectura acaba de ejecutar 24 GET autenticados al
  origen ALB con concurrencia 6: 24/24 HTTP 200, p95 191.51 ms. Es un smoke
  pequeño, no un benchmark de capacidad ni una prueba de 3,000 usuarios.
- En una sonda reciente, Python `urllib` recibió 403 de Cloudflare (3/3; la
  corrida anterior fue 25/25), mientras `curl` e `Invoke-WebRequest` al mismo
  health recibieron 200. No se cambió ni se sorteó la regla del proxy. La
  métrica de latencia de esas respuestas 403 no representa rendimiento del
  origen.
- WAF regional no está desplegado. No existe ruta privada AWS–Azure: AWS
  Academy denegó Customer Gateway por SCP y no hay VNet Azure del proyecto.
- El template local CloudFormation usa defaults v18 y los parámetros efectivos
  del stack también son v18; el template guardado en AWS conserva tres defaults
  de artefacto v16. La comparación no encontró diferencias de recursos; no se
  forzó una actualización vacía. Terraform está validado localmente, sin `apply`.
- El control de Chrome se detuvo porque no pudo identificar con confianza la
  URL de la ventana. No hay recorrido visual nuevo de módulos/CSV en este corte.
  WebRTC entre dos navegadores tampoco está probado recientemente.
- La revisión de rúbrica sigue ambigua: la hoja del proyecto suma 18.5 aunque
  declara 20; el PDF general es otro instrumento con máximos que suman 90. No
  se combinan las escalas ni se inventa una nota.
- La compuerta local recién repetida pasó 215 pruebas unitarias, 14 Node,
  frontend/build, auditorías, CloudFormation, Terraform y cinco pruebas mock;
  no aplicó cambios cloud. GitHub Actions para `d060a2c` también pasó sus tres
  trabajos.

## Matriz de pruebas

| ID | Prueba | Estado verificado | Qué falta |
|---|---|---|---|
| PT-HTTPS-01 | Dominio, TLS y redirect | HTTPS/ACM vigentes; health 200; HTTP→HTTPS | Prueba desde Chrome una vez que el controlador identifique la URL. |
| PT-AWS-01 | Salud y disponibilidad | Stack `UPDATE_COMPLETE`/`IN_SYNC`; ALB activo; ASG/targets 2/2 sanos | Captura actual de consola e inventario. |
| PT-AWS-02 | Login y roles | API Admin, Comercial y Operaciones pasó 200/403 por TLS | Recorrido visual autenticado completo. |
| PT-WMS-01 | ERP→AWS→Azure→ledger sintético | E2E público y estados demo con reconciliación ya demostrados | Repetición de una operación sintética de punta a punta en la interfaz. |
| PT-OUTBOX-01 | Historial paginado | 49/49 eventos entregados leídos sin omisiones | Ninguna brecha conocida en este flujo; comprobar en recorrido visual. |
| PT-RETRY-01 | Reintento y poison | Guards y metadata poison probados en Azure; outbox durable | Falla controlada y recuperación observada en el portal desplegado, sin borrar evidencia. |
| PT-DR-01 | Backup/restore/failover | Restore aislado: RTO 260 s, RPO observado ≤8 s | Failover Multi-AZ no probado; decidir costo antes de habilitarlo. |
| PT-NET-01 | Red privada AWS–Azure | E2E usa HTTPS público | VNet/ruta privada ausente; SCP bloquea Customer Gateway en AWS Academy. |
| PT-PERF-01 | Carga y escalado | Escalado sintético 2↔3 histórico; 24 GET al origen ALB, concurrencia 6, 24/24 HTTP 200, p95 191.51 ms | Carga sostenida y representativa, medir escalado/capacidad; no se afirma soportar 3,000 usuarios. |
| PT-SEC-01 | Seguridad y navegador | TLS, controles de rol por API; SNS y auditoría existentes | WAF ausente; validar vistas/CSV visualmente; no atribuir el 403 a la app sin origen confirmado. |
| PT-AZ-MON-01 | Invocaciones y alertas | Azure health 200; monitor y alerta sintética previos verificados | Captura actual de invocación/monitor y correlación de señal métrica real. |
| PT-IAC-01 | CloudFormation/Terraform | Validación local; detección fresca de drift `IN_SYNC` a las 04:23 UTC | Reconciliar defaults de artefacto v16/v18 en el siguiente cambio efectivo; no desplegar un cambio vacío. |
| PT-APP-01 | CSV, correo y finanzas | Módulos con datos sintéticos y mensajería interna portal-only | CSV e interacción ERP en navegador; SMTP externo no forma parte del correo portal-only. |
| PT-RTC-01 | WebRTC | Controles mute/cámara implementados | Prueba de audio/video bidireccional entre dos navegadores. |
| PT-COST-01 | Costos | AWS con créditos Academy que compensan el consumo medido | Importe Azure fiable y atribución por proyecto. |
| PT-DOC-01 | Evidencia/entrega | 215 pruebas unitarias, 14 Node y CI `d060a2c` aprobado en tres trabajos | Capturas recientes del inventario AWS y monitor Azure; defensa oral. |

## Secuencia de cierre

1. Si la sonda Python a través de Cloudflare sigue siendo necesaria, revisar la
   regla del proxy con su administrador; el test al origen ALB ya separa el
   rendimiento de la app del 403 del proxy. No desactivar controles a ciegas.
2. Completar recorrido Chrome de roles, módulos ERP y carga CSV cuando el control
   de ventana pueda identificar la URL activa.
3. Definir objetivo de capacidad y correr carga sostenida de bajo impacto por
   ALB con datos sintéticos, límites aprobados, reconciliación y limpieza
   documentada; observar el escalado gradualmente.
4. Reconciliar template local/deployed en la próxima actualización CloudFormation
   efectiva y generar change set; revisar cada reemplazo antes de ejecutarlo.
5. Revisar costo/permiso antes de Multi-AZ, WAF o VPN; no crear rutas privadas si
   la SCP/ausencia de VNet sigue bloqueando el diseño.
6. Capturar evidencia AWS/Azure, terminar prueba WebRTC si sigue en el alcance y
   pedir al docente aclaración de rúbrica/ponderación.

La revalidación más reciente se registra en
[`CLOUD-REVALIDATION-2026-10-16-0400UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0400UTC.md).
El smoke autenticado y la sonda de lectura del 16/10 se registran en
[`AWS-READONLY-LOAD-2026-10-16-0424UTC.md`](../evidence/current/aws/AWS-READONLY-LOAD-2026-10-16-0424UTC.md).
