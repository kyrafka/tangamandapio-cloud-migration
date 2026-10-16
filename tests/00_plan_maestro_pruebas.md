# Plan maestro de pruebas AWS–Azure

**Corte vigente:** 16/10/2026, 01:05 UTC. Los resultados históricos conservan
su fecha y no reemplazan una comprobación fallida posterior.

## Estado actual

- HTTPS del dominio completa TLS y HTTP redirige a HTTPS (`301`). A las 01:02
  UTC portada, `/health`, `/ready` y `/platform` devolvieron `503`.
- AWS STS autenticó en la cuenta Academy `841113066612`; CloudFormation
  `DescribeStacks` fue rechazado por el `explicit deny` `voc-cancel-cred`. No se
  confirmaron targets, drift, ASG ni RDS actuales; no se cambió infraestructura.
- Azure Function `tangama-wms-261008`: `Running`, `httpsOnly=true`; `/api/health`
  devolvió `200`.
- El E2E sintético local→Azure pasó guardas (401 sin clave, 400 productor no
  autorizado), venta `demo_fulfillment_completed`, recepción
  `demo_restock_completed`, stock demo restaurado exactamente y poison count 0
  antes/después. Los eventos válidos permanecen en auditoría Blob. Este flujo no
  salió de EC2/RDS.
- Gate local: 209 pruebas, frontend/build, CloudFormation, Terraform format y
  validate, mocks de red y auditoría de dependencias aprobados. No ejecutó
  `apply` ni verifica la salud del portal remoto.
- El restore RDS, permisos API por rol y E2E AWS→Azure disponibles en evidencia
  son cortes previos a v18. No asumir que validan esta revisión.

## Matriz de pruebas

| ID | Prueba | Criterio de aprobación | Último resultado y siguiente acción |
|---|---|---|---|
| PT-HTTPS-01 | Dominio, TLS y redirect | TLS válido, HTTP 301, HTTPS sirve páginas | TLS/301 sí; las cuatro rutas HTTPS dan 503. Recuperar el origen. |
| PT-AWS-01 | Salud y disponibilidad | `/health` y `/ready` 200; dos destinos sanos | Falla 503; IAM impide leer salud formal del target group. Recuperar permiso legítimo y diagnosticar antes de editar. |
| PT-AWS-02 | Login y operaciones v18 | Login, roles 200/403, venta/compra persistidas y reconciliadas | No repetido en v18. Hacer después de restaurar disponibilidad. |
| PT-WMS-01 | ERP→Queue→Function→ledger | Evento correlacionado, estado y stock demo reconciliado | Aprobado local→Azure. Repetir como AWS/EC2→Azure y preservar saldo inicial. |
| PT-OUTBOX-01 | Historial paginado | 45 eventos sin omisiones/duplicados: páginas 30+15 | Unitarias pasan; falta confirmar GET autenticado contra el despliegue v18. |
| PT-RETRY-01 | Reintento y poison | Pedido/outbox durables, retry observable, poison inspeccionado sin destruir evidencia | Pruebas unitarias; poison metadata Azure 0 en la prueba reciente. Falta inyectar falla controlada y observar recuperación en el portal desplegado. |
| PT-DR-01 | Backup y restauración | Restore aislado íntegro; medir RTO/RPO y limpiar solo temporales | Restore exitoso en evidencia previa; RDS Single-AZ/backup 1 día y sin failover probado. Revalidar cuando haya permisos si el corte actual lo requiere. |
| PT-NET-01 | Conectividad privada AWS–Azure | Túnel/rutas privadas y tráfico verificado entre redes | Pendiente; preflight de VPN denegado por AWS Academy. HTTPS público no satisface este criterio. |
| PT-PERF-01 | Carga y autoescalado | Perfil de carga aprobado, errores/p95 definidos, escalado observado | Gate histórico corto (24 lecturas, concurrencia 6); no acredita 3,000 usuarios ni autoescalado. |
| PT-SEC-01 | Roles, admin y navegador | Roles aislados, CSRF/sesión, vistas autenticadas y CSV correctos | API pasó en v17; visual y regresión v18 pendientes. WAF desactivado. |
| PT-AZ-MON-01 | Azure y alertas | Invocaciones correlacionadas, métricas, alarma/recuperación y evidencia | Function health 200 y E2E reciente; usuario confirmó alerta/recuperación previa. Guardar captura/telemetría actual. |
| PT-IAC-01 | CloudFormation/Terraform | fmt/validate/plan; drift y cambios revisados, sin reemplazos sorpresa | Gate local aprobado; CloudFormation v18 `UPDATE_COMPLETE`; drift AWS no consultable por IAM. No aplicar a ciegas. |
| PT-APP-01 | CSV, correo y finanzas | Importar catálogo, comprobar ledger, finanzas y entrega de correo conforme alcance | Finanzas/correo interno `portal_only` pasaron en v17; CSV visual y SMTP saliente no verificados/desplegados. |
| PT-RTC-01 | Telefonía WebRTC | Audio/video bidireccional, mute/cámara y grabación con consentimiento | No probado recientemente entre dos navegadores. Pendiente de producto, separado del 503. |
| PT-COST-01 | Costos y limpieza | Costo AWS/Azure observado; solo temporales retirados tras verificar | AWS tiene estimación; Azure y consumo real del lab sin conciliación actual. |
| PT-DOC-01 | Evidencia/entrega | Capturas, logs sanitizados, matriz y documentación sincronizados | Corte actual documentado; faltan capturas de consola/monitor y comprobar Actions tras sincronizar. |

## Secuencia de cierre

1. Recuperar acceso de lectura autorizado al plano de control AWS. No usar
   perfiles alternativos ni intentar sortear `voc-cancel-cred`.
2. Consultar ALB/target health, ASG, eventos/logs de las instancias y RDS; aislar
   causa del 503 antes de desplegar otra versión.
3. Cuando `/health` y `/ready` estén sanos, ejecutar el smoke autenticado v18,
   roles y paginación, seguido de venta/compra sintéticas AWS→Azure con
   reconciliación del saldo.
4. Revalidar drift IaC; probar restauración/failover según presupuesto y
   restricciones de Academy; crear la red privada solo con permisos, costo y
   plan revisados.
5. Ejecutar los casos de carga, navegador, monitoreo, CSV, correo y WebRTC que
   se mantengan dentro del alcance acordado; guardar evidencia fechada.

El detalle del corte está en
[`CLOUD-REVALIDATION-2026-10-16-0105UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0105UTC.md).
