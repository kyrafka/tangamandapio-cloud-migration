# Plan histórico de reanudación y mejoras

**Proyecto:** Tangamandapio S.A.C.
**Corte:** 04/10/2026
**Regla:** este plan diferencia hechos probados, pendientes y mejoras. No se despliega nada solo para editar documentos; cada levantamiento debe terminar con evidencias y cierre autorizado.

El estado de infraestructura descrito abajo es el corte del 04/10/2026 y ya no
es actual. Consulta [MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md)
antes de cualquier tarea o sustentación. Se conserva el resto como plan y
registro histórico, no como orden de despliegue vigente.

## 1. Estado de cierre verificado al corte — 04/10/2026

| Proveedor | Comprobación de cierre | Estado actual |
|---|---|---|
| AWS `us-east-1` | CloudFormation filtrado por Tangamandapio: 0 pilas. Consola EC2: sin instancias. El stack, ALB, ASG, RDS, VPC/NAT y bucket del ciclo fueron eliminados. | Sin recurso activo del proyecto. El Learner Lab puede estar iniciado sin reprovisionar infraestructura. |
| Azure West US | `az group exists --name rg-tangamandapio-261001r2-wus` devolvió `false`; el portal muestra el recurso como no encontrado. | Sin recurso activo del proyecto. |

No se infiere que un recurso esté activo por la existencia de código, artefactos, una URL vieja o una captura. Al corte de este plan, la infraestructura de Tangamandapio estaba **apagada/eliminada**; la verificación del siguiente ciclo debe hacerse nuevamente antes de desplegar.

## 2. Lo que sí fue probado en ciclos temporales

| Dominio | Prueba real completada | Límite de la prueba |
|---|---|---|
| AWS transaccional | CloudFormation alcanzó `UPDATE_COMPLETE`; ALB con dos targets saludables; `GET /health` devolvió 200 con PostgreSQL; `POST /api/orders` devolvió 201 y `GET /api/orders` devolvió 200. | Corresponde al ciclo temporal de octubre. No demuestra que hoy haya un ALB disponible. |
| AWS B2B | Se versionó el artefacto de portal y se corrigió el uso de booleanos PostgreSQL. Las pruebas unitarias y el build del portal pasaron. | Se debe repetir en infraestructura la autenticación, roles y rutas protegidas de la última versión. |
| Azure WMS | `HttpHealth` devolvió 200; `HttpFulfillment` aceptó evento con 202; la repetición idempotente devolvió 200; Blob y Queue fueron verificados. | Corresponde al ciclo temporal destruido. No demuestra una Function activa hoy. |
| Observabilidad | Se definieron CloudWatch/Alarmas y Azure Monitor/Application Insights en IaC; existen pruebas y registros del ciclo. | Faltan capturas correlacionadas de una misma ejecución para una demo actual. |

## 3. Pendiente obligatorio si se requiere una demostración actual

### Fase A — preparar sin costo

1. Actualizar la credencial temporal AWS Academy y comprobar identidad; iniciar sesión de Azure CLI.
2. Ejecutar `terraform fmt` y `terraform validate`; validar la plantilla CloudFormation.
3. Revisar el inventario inicial y confirmar que no hay recursos Tangamandapio antes de crear nada.
4. Preparar nombres únicos de Azure, las variables no secretas y un cambio versionado; no guardar claves ni tokens.

### Fase B — AWS primero

1. Crear el stack CloudFormation con el artefacto B2B versionado.
2. Verificar VPC/subredes, ALB, dos targets saludables, ASG, RDS privada, S3 con bloqueo público y alarmas CloudWatch.
3. Ejecutar y capturar: Health 200, creación de pedido 201 y consulta de pedido 200.
4. Probar login con cuentas de prueba y validar autorización en backend para cada rol, incluyendo un intento denegado. No usar credenciales personales en la evidencia.
5. Ejecutar una prueba corta de carga y una prueba de recuperación de una instancia/target; guardar el resultado y comprobar que el ALB se mantiene operativo.

### Fase C — Azure y flujo entre nubes

1. Crear el vertical WMS con Terraform: Function, Blob privado, Queue, Key Vault, Managed Identity/RBAC, Log Analytics y Application Insights.
2. Repetir Health 200, evento 202, Blob creado, Queue encolada y repetición idempotente 200.
3. Implementar y probar el emisor **real** del outbox AWS hacia `HttpFulfillment` de Azure. El mismo `event_id` debe poder verse en el pedido/outbox, Function, Blob, Queue y registros.
4. Implementar reintento controlado: ante una indisponibilidad temporal de Azure, el evento queda pendiente y se reintenta sin duplicar el despacho.

### Fase D — evidencias y cierre

1. Insertar solo capturas reales en el Entregable 1: fecha, región, recurso, configuración, resultado y pie de captura.
2. Marcar las capturas anteriores como históricas del ciclo temporal, no como estado actual.
3. Tras autorización expresa, destruir AWS y Azure y capturar el inventario final en cero.
4. Actualizar este archivo y el registro maestro con fecha, resultados y anomalías observadas.

## 4. Mejoras priorizadas para producción

| Prioridad | Mejora | Criterio de finalización |
|---|---|---|
| P0 | HTTPS, dominio y redirección HTTP→HTTPS | Certificado ACM, listener 443 y cookies `Secure`; no se exponen credenciales reales sobre HTTP temporal. |
| P0 | Integración AWS→Azure con autenticación y reintento | Evento trazable, idempotente y recuperable de punta a punta. |
| P0 | Autorización por roles en servidor | Cada endpoint sensible valida sesión y rol; una prueba negativa confirma que no basta ocultar elementos en la interfaz. |
| P1 | Backups y recuperación | Backups automáticos RDS, versionado/lifecycle S3, RPO/RTO declarados y una restauración probada. |
| P1 | Observabilidad operativa | Dashboard, alarmas y logs correlacionados; prueba de indisponibilidad y alerta verificable. |
| P1 | CI/CD e IaC reproducible | Pipeline de validación, empaquetado versionado, `plan`/change set revisable y destrucción controlada. |
| P2 | Alta disponibilidad de datos | Evaluar RDS Multi-AZ y recuperación regional según presupuesto/RPO/RTO. |
| P2 | Endurecimiento adicional | WAF, rotación de secretos, análisis de dependencias y pruebas de seguridad de API/sesión. |
| P2 | Portal desplegable único | Empaquetar el build React/Vite en el mismo artefacto que se publica en AWS para evitar deriva con la versión ligera de laboratorio. |

## 5. Decisiones ya tomadas

La propuesta técnica detallada de escalabilidad, seguridad, análisis web/tráfico,
telemetría y CI/CD está en [09_propuesta_cloud_aws_azure.md](09_propuesta_cloud_aws_azure.md).
Usar ese documento para priorizar herramientas; este plan conserva el orden de
levantamiento y cierre del laboratorio.

- **AWS y Azure** son el alcance operativo acordado. OCI está fuera del proyecto actual; la descripción/rúbrica escrita aún la menciona, así que documentar la instrucción del docente que reemplaza ese requisito (ver [evaluación](10_evaluacion_rubrica_entregable_final_2026-10-08.md)).
- **CloudWatch y Azure Monitor** son la observabilidad administrada de referencia. Prometheus, Grafana y Portainer son complementos locales; Zabbix no es requisito ni debe añadir costo al piloto.
- La telefonía IP se planifica como un dominio de comunicaciones separado; su guía, límites y evidencias están en [08_manual_evolucion_portal_y_telefonia_ip.md](08_manual_evolucion_portal_y_telefonia_ip.md). No se considera implementada hasta completar un piloto aislado.
- Los recursos se levantan solo durante la ventana de evidencia y se destruyen después. El objetivo es demostrar arquitectura y operación, no mantener un servicio público permanente.
- El repositorio oficial es [tangamandapio-cloud-migration](https://github.com/kyrafka/tangamandapio-cloud-migration).
