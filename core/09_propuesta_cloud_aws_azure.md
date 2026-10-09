# Propuesta de evolución cloud — AWS + Azure

**Proyecto:** Tangamandapio S.A.C.

**Elaborada:** 08/10/2026

**Alcance:** propuesta técnica para el portal B2B y el flujo logístico ficticio.
**Importante:** describe diseño y próximos pasos; no afirma que los recursos estén activos ni los despliega.

## Resumen ejecutivo

La propuesta es mantener una arquitectura deliberadamente sencilla y mostrar
prácticas cloud reales, no añadir servicios solo para llenar el diagrama:

```text
Clientes
  │ HTTPS
  ▼
AWS WAF → ALB → Auto Scaling Group (portal/API en EC2)
                         ├── RDS PostgreSQL privada
                         ├── S3 privado (documentos / grabaciones)
                         └── Outbox durable ── HTTPS + event_id ──► Azure Function
                                                                    ├── Storage Queue
                                                                    ├── Blob privado
                                                                    └── Azure Monitor / App Insights
```

CloudWatch y Azure Monitor son la observabilidad administrada. La web local
`/platform` ayuda a exponer métricas de ALB/RDS/WAF, usuarios y conciliación,
pero requiere configuración real de recursos y permisos antes de mostrar datos
cloud. Los estados de despliegue deben contrastarse con el inventario del día;
una captura o plantilla no demuestra que algo siga encendido.

**Control documental antes de desplegar:** el registro maestro y el plan de
reanudación tienen corte 04/10/2026 y describen los recursos como eliminados;
el [README](../README.md) y el [estado web del 08/10](../app/WEB_STATUS_AND_GAPS_2026-10-08.md)
registran una ejecución posterior como desplegada. Esta propuesta no intenta
resolver esa diferencia sin una lectura de inventario AWS/Azure fechada. Antes
de cualquier `apply`, actualizar un solo registro rector con evidencia del
mismo ciclo.

## Herramientas adecuadas para este caso

| Necesidad | AWS | Azure | Cómo se demuestra |
|---|---|---|---|
| Entrada web | WAF + Application Load Balancer | No hace falta duplicar el balanceador en Azure | WAF bloquea una petición de prueba y el ALB reparte tráfico a dos destinos sanos. |
| Escala horizontal | EC2 Auto Scaling Group + CloudWatch | Functions con plan/trigger de cola apropiado | Carga sintética controlada; una métrica supera el objetivo, aumenta capacidad y luego reduce sin perder servicio. |
| Datos de negocio | RDS PostgreSQL privada, copias/PITR | Storage para evidencia del WMS | Crear un pedido, persistirlo, reiniciar una instancia web y consultar el mismo pedido. Restaurar una copia en entorno temporal y leer un registro. |
| Archivos | S3 privado con bloqueo público, cifrado y ciclo de vida | Blob privado con RBAC | Subir/leer con rol autorizado; petición anónima denegada; validar expiración/versionado según política. |
| Integración | Outbox durable y reintento del portal | Function + Queue + Blob | El mismo `event_id` aparece en ambos lados; evento repetido no genera un segundo efecto. |
| Métricas de infraestructura | CloudWatch (ALB, EC2/ASG, RDS, WAF) | Azure Monitor | Dashboard, umbral, alerta y evidencia de recuperación. |
| Diagnóstico de experiencia | CloudWatch RUM, Synthetics, ALB logs + Athena | Application Insights con OpenTelemetry | Detectar error del navegador y seguir una operación hasta el worker Azure. |
| Identidad de servicios | IAM instance profile; SSM Session Manager; Secrets Manager/Parameter Store | Managed Identity, RBAC, Key Vault | No hay claves permanentes en código, AMI, browser ni repositorio. |
| Auditoría/detección | CloudTrail; GuardDuty/Config si cuota y costo lo permiten | Activity Log, Defender for Cloud si está disponible | Mostrar quién cambió recursos y una alerta/detección controlada. |
| Infraestructura repetible | CloudFormation para el stack AWS | Terraform para el vertical Azure actual | Validar, revisar el cambio, aplicar y destruir solo el entorno etiquetado. |

La implementación debe conservar un único dueño de cada recurso: no administrar
el mismo ALB o Function simultáneamente desde dos plantillas distintas. El
registro maestro del proyecto y la plantilla activa tienen precedencia sobre
una plantilla antigua o un nombre DNS guardado.

## Escalabilidad que sí podemos demostrar

1. Mantener el portal detrás del ALB en al menos dos zonas de disponibilidad,
   con health checks y reemplazo automático de destinos dañados.
2. Asociar el Target Group al Auto Scaling Group. Para esta aplicación web,
   evaluar primero target tracking de `ALBRequestCountPerTarget`; CPU puede
   servir como señal secundaria. El objetivo se calibra con una carga de prueba,
   no se inventa antes de medir.
3. En una práctica de laboratorio, usar límites pequeños (por ejemplo, mínimo
   2 y máximo 4) y presupuesto/alerta; comprobar escala hacia arriba y hacia
   abajo y borrar el entorno al terminar.
4. Observar RDS por conexiones, CPU, almacenamiento y latencia. Escalar EC2 no
   arregla una base saturada; RDS Multi-AZ es alta disponibilidad, no escalado
   horizontal de escrituras. Réplicas de lectura solo se justificarían con
   lecturas dominantes demostradas.
5. Para Azure, medir profundidad/antigüedad de la cola, ejecuciones, errores y
   duración de Function. La escala depende del plan y del trigger configurado;
   no se debe deducir solo de que exista una Function.

Amazon EC2 Auto Scaling puede usar el promedio de solicitudes por destino del
ALB como métrica target tracking; el servicio gestiona las alarmas asociadas a
esa política ([documentación AWS](https://docs.aws.amazon.com/autoscaling/application/userguide/target-tracking-scaling-policy-overview.html)).
Azure Functions también puede escalar según eventos/colas, pero el máximo, la
velocidad y la granularidad dependen del plan y trigger elegidos
([escalado event-driven de Functions](https://learn.microsoft.com/en-us/azure/azure-functions/event-driven-scaling)).
Estas políticas no se activan aquí: antes hay que comprobar la plantilla y el
inventario del ciclo vigente.

## Observabilidad: distinguir infraestructura, aplicación y navegador

- **Infraestructura:** CloudWatch para solicitudes, latencia p95, 4xx/5xx,
  destinos no saludables, actividad ASG y métricas RDS. Azure Monitor para
  ejecuciones de Function, errores, cola y almacenamiento.
- **Aplicación y flujo de negocio:** propagar `request_id`, `order_id` y
  `event_id` sin datos personales en logs. Una vista debe poder contestar:
  “¿se guardó el pedido?”, “¿se entregó el evento?”, “¿qué respondió Azure?” y
  “¿cuánto lleva pendiente?”. OpenTelemetry/W3C trace context permite
  instrumentar servicios sin acoplar toda la observabilidad a una sola nube.
- **Experiencia web real:** CloudWatch RUM mide tiempos y fallos observados por
  navegadores reales; Synthetics puede recorrer login/pedido con cuentas
  sintéticas. Muestrear RUM, minimizar información identificable y fijar
  retención; no enviar contraseñas, formularios ni contenido de llamadas.
- **Detección de anomalías:** después de conseguir una serie histórica,
  evaluar CloudWatch Anomaly Detection para solicitudes/latencia y umbrales
  dinámicos de Azure Monitor para telemetría WMS. En el laboratorio corto y
  sin datos suficientes, usar umbrales explícitos y declarar el límite; los
  modelos no sustituyen una alarma de seguridad determinista.
- **Análisis forense de tráfico:** los access logs del ALB se pueden guardar en
  S3 y consultar con Athena para origen, URL, estado y latencia. Configurar
  retención, acceso y redacción porque un log puede contener datos sensibles.
- **Correlación multicloud:** enviar y registrar el mismo `event_id` en AWS y
  Azure; Application Insights ofrece mapa de dependencias para Functions y
  bindings si la instrumentación está activa.

CloudWatch RUM recoge rendimiento y errores de sesiones reales, mientras que
Athena puede consultar logs del ALB guardados en S3 ([RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html),
[Athena para ALB](https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html)).
Para Azure, Application Insights admite instrumentación OpenTelemetry y
seguimiento de dependencias ([Azure Monitor OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable)).
CloudWatch puede modelar bandas de comportamiento histórico, y Azure Monitor
puede calcular umbrales dinámicos cuando hay muestras suficientes
([AWS Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html),
[Azure Dynamic Thresholds](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-dynamic-thresholds)).
Estos analizadores son candidatos de siguiente fase, no recursos que deban
marcarse como activos sin habilitarlos y verificar su telemetría.

## Seguridad por diseño

- **Personas:** cuentas individuales, MFA para administradores, permisos por
  rol y revisión periódica. Evitar cuentas compartidas y privilegios globales.
- **Servicios:** EC2 usa un rol de instancia con permisos mínimos; acceso
  administrativo a instancias mediante Session Manager, sin SSH público.
  Azure Functions usa Managed Identity y RBAC acotado a su Queue/Blob.
- **Integración entre nubes:** para el laboratorio, mantener HTTPS y guardar
  la clave de Function únicamente en Parameter Store `SecureString`, con
  acceso limitado al rol emisor y procedimiento de rotación. Para producción,
  reemplazarla por un flujo OAuth 2.0 de identidad de servicio/Entra o un
  mecanismo aprobado equivalente; no copiar credenciales AWS Academy a Azure.
- **GitHub/CI:** federar con OIDC tanto para AWS IAM como para Azure Entra,
  limitado a este repositorio, ramas y entornos aprobados. Así el pipeline usa
  credenciales temporales y no claves de larga duración ([AWS OIDC](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html),
  [Azure OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)).
- **Red y datos:** ALB público como única entrada; EC2 y RDS en subred privada;
  RDS acepta PostgreSQL solo desde el grupo de aplicación; cifrado y backups;
  S3/Blob sin acceso público; TLS en tránsito. VPN Site-to-Site solo si se
  exige conectar redes privadas/sedes, no para una API AWS→Azure por HTTPS.
- **Borde y auditoría:** reglas administradas WAF con modo de observación y
  ajuste antes de bloquear; CloudTrail y logs diagnósticos; alertas de
  actividad, errores, accesos denegados y cambio de configuración.
- **Aplicación:** HTTPS confiable, cookies `Secure`/`HttpOnly`/`SameSite`, CSRF,
  protección ante abuso de login, validación de entradas, control de rol en
  backend y auditoría de acciones sensibles.

Esto sigue principios de mínimo privilegio, identidad auditable y secretos
fuera del código de los Well-Architected Framework de AWS y Azure
([AWS](https://docs.aws.amazon.com/wellarchitected/latest/userguide/waf.html),
[Azure](https://learn.microsoft.com/en-us/azure/well-architected/)).

## WMS: decidir Queue simple o broker avanzado

La Azure Storage Queue actual es razonable para un laboratorio económico y un
flujo sencillo. No conviene reemplazarla sin necesidad. Si la operación llegara
a requerir orden garantizado por pedido, duplicados detectados en broker,
pub/sub, sesiones o dead-letter administrada, evaluar Azure Service Bus; la
decisión se basa en esas garantías y no en usar el servicio “más grande”. Azure
documenta diferencias de orden, transacciones, deduplicación y DLQ entre ambos
[servicios de cola](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-azure-and-service-bus-queues-compared-contrasted).

En cualquier opción, el consumidor debe ser idempotente. Si el WMS sigue siendo
simulado, la interfaz y la presentación deben decirlo explícitamente. Una
integración real necesita contrato de SKU/cantidad/almacén, autenticación,
estados de aceptación/rechazo y pruebas con datos ficticios autorizados.

## Entrega segura: pipeline recomendado

1. **Pull request:** formato/lint, pruebas unitarias (AWS y Azure), análisis de
   dependencias y secretos, validación de CloudFormation/Terraform y revisión
   de permisos IAM/RBAC.
2. **Construcción reproducible:** crear artefacto versionado una sola vez,
   conservar checksum/SBOM y asociarlo al commit. No reconstruir artefactos
   diferentes entre prueba y despliegue.
3. **Autenticación federada:** GitHub Actions obtiene sesión temporal vía OIDC;
   ningún token de Learner Lab queda en GitHub. Restringir trust policy a
   repositorio/branch/environment concreto y requerir aprobación antes de
   publicar.
4. **Despliegue:** change set/plan visible, revisión de drift, despliegue
   gradual, health check y smoke test; si falla, detenerse y volver a la
   versión previa conocida.
5. **Cierre de laboratorio:** exportar capturas/evidencias sin secretos,
   confirmar qué recursos cuestan, destruir solo el stack autorizado y
   verificar el inventario final.

CloudFormation/Terraform no deben aplicarse hasta reconciliarse con los
recursos vivos. El propio proyecto ya registra diferencias históricas entre
plantilla local y stack; primero se importa/describe el estado real y se revisa
el cambio.

## Guion corto para enseñar el proyecto

1. **Antes de la carga:** mostrar que el pedido vive en PostgreSQL privada, el
   ALB conoce sus destinos y RDS no tiene entrada pública.
2. **Transacción:** crear un pedido ficticio; enseñar respuesta del portal,
   fila de pedido y evento outbox con un solo `event_id`.
3. **Escala:** generar una carga pequeña previamente acordada, observar
   `RequestCountPerTarget` y el cambio controlado del ASG; confirmar que el ALB
   mantiene destinos saludables y que la capacidad vuelve a su mínimo.
4. **Resiliencia multicloud:** pausar el worker/endpoint de prueba, observar el
   outbox pendiente y reintento; reactivar Azure y consultar el mismo evento.
   No usar pedidos ni clientes reales.
5. **Seguridad y telemetría:** mostrar un acceso denegado por rol, un bloqueo
   WAF no destructivo, el trace del `event_id` en ambos proveedores y una
   alerta que se recupera.
6. **Cierre:** guardar capturas redactadas, confirmar cargos y borrar el
   laboratorio temporal con una comprobación final de inventario.

La demostración se detiene si hay una alarma no prevista, se excede el límite
de carga acordado o el laboratorio muestra un costo/cuota inesperado.

## Orden de trabajo recomendado

| Fase | Trabajo | Criterio para pasar a la siguiente |
|---|---|---|
| 0. Preparación | Revisar estado actual, rubric, cuotas, presupuesto, IaC y datos sintéticos. | Plan aprobado y costos/limpieza entendidos. |
| 1. Núcleo AWS | ALB, dos targets, ASG, RDS privada, IAM, S3, WAF y HTTPS. | Pedido persiste; rol no autorizado recibe rechazo; health checks y backup visibles. |
| 2. Elasticidad | Carga de prueba breve, target tracking por target, alarma y recuperación de instancia. | Capacidad escala y vuelve; el portal responde; se registra tiempo y evidencia. |
| 3. WMS Azure | Function, Storage Queue/Blob privados, Managed Identity/RBAC, monitorización. | `event_id` end-to-end, idempotencia, reintento y fallo controlado. |
| 4. Seguridad/telemetría | OIDC CI, secretos protegidos, CloudTrail/Azure diagnostics, RUM/Synthetics si presupuesto. | Se prueba alerta y se evita guardar datos sensibles en logs. |
| 5. Continuidad | Backup restore, RPO/RTO, rollback y cierre del laboratorio. | Restauración consultable y teardown/inventario final documentados. |
| 6. Dominio final | DNS propio, certificado ACM, cookie Secure y prueba desde ambos proveedores. | TLS confiable en navegador y renovación documentada. |

## Decisiones para no sobrecargar el proyecto

- No añadir Kubernetes/EKS/AKS: el portal no necesita esa complejidad para
  demostrar balanceo, escalado y resiliencia.
- No duplicar el WAF, CDN, base de datos y observabilidad en ambos proveedores
  sin un requisito de negocio: multicloud aquí significa responsabilidades
  distintas y trazables, no dos copias de todo.
- No agregar VPN, Grafana/Prometheus administrados, API Management o broker
  avanzado hasta que una prueba o requisito lo justifique. CloudWatch y Azure
  Monitor bastan como base administrada del entregable.
- No habilitar RUM, logs detallados, Security Hub, GuardDuty, Defender o
  réplicas regionales a ciegas: revisar cuotas, retención y costos del lab;
  activar por ventana, capturar y cerrar.

## Referencias de diseño

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/userguide/waf.html)
- [Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/)
- [Auto Scaling target tracking con AWS](https://docs.aws.amazon.com/autoscaling/application/userguide/target-tracking-scaling-policy-overview.html)
- [CloudWatch RUM](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html)
- [Análisis de ALB con Athena](https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html)
- [Application Insights y OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable)
- [Comparación Storage Queue y Service Bus](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-azure-and-service-bus-queues-compared-contrasted)
- [Federación OIDC de GitHub con AWS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html)
- [Federación OIDC de GitHub con Azure](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)
- [Pruebas de restauración recomendadas por AWS](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_backing_up_data_periodic_recovery_testing_data.html)
