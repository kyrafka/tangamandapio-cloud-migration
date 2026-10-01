# Mapa AWS predespliegue — Tangamandapio S.A.C.

**Fecha de corte:** 30/09/2026  
**Región objetivo:** `us-east-1`  
**Stack previsto:** `tangamandapio-live-20260930`  
**Fuente IaC:** `iac/cloudformation/aws-lab.yaml`

## 1. Estado real antes de ejecutar

| Elemento | Estado comprobado en CloudShell | Impacto de costo |
|---|---|---|
| Plantilla `aws-lab.yaml` | Cargada y `validate-template` aprobada por CloudFormation | Ninguno |
| Change set `tangamandapio-preflight-20260930` | Creado con la revisión anterior; stack en `REVIEW_IN_PROGRESS` | Ningún recurso de infraestructura creado |
| `andemarket-lab` | Registros históricos en `DELETE_COMPLETE` | Ninguno |
| Recursos con etiqueta `Project=andemarket` | Consulta de Tagging API: `0` | Ninguno |
| Recursos Tangamandapio | Ninguno desplegado aún | Ninguno |

El change set es el límite de seguridad: **hasta ejecutar `execute-change-set` no se crean EC2, RDS, ALB, NAT, S3 ni otros componentes facturables**. Después de este preflight se añadió la recolección de memoria, disco y Gunicorn a la plantilla local; por ello el change set abierto debe descartarse y recrearse antes de desplegar. No se ejecutará la revisión anterior.

## 2. Arquitectura que se creará al ejecutar el change set

```text
Internet
   │ HTTP:80 (demostración)
   ▼
ALB público en dos subredes públicas
   │ health check /health
   ▼
ASG: 2–4 EC2 privadas (Flask/Gunicorn + portal B2B)
   │ TCP:5432 solo desde AppSecurityGroup
   ▼
RDS PostgreSQL privada y cifrada

EC2 ──► Secrets Manager (credencial RDS)
EC2 ──► CloudWatch Logs / Dashboard / Alarmas
EC2 ──► S3 privado, cifrado y versionado
```

### 2.1 Servicios y configuración

| Dominio | Servicios AWS | Configuración preparada | Resultado a demostrar |
|---|---|---|---|
| Red | VPC, IGW, NAT Gateway, EIP, route tables, 6 subredes | CIDR `10.10.0.0/16`; 2 subredes públicas, 2 de aplicación y 2 de base de datos en dos AZ | Segmentación y rutas correctas |
| Entrada | ALB, target group, listener | ALB público, HTTP `80`; health check `GET /health` al puerto `8080` | 2 destinos `healthy`, respuesta del portal |
| Aplicación | Launch Template, Auto Scaling, EC2 | Amazon Linux 2023; mínimo/deseado `2`, máximo `4`; target tracking CPU 60% | Reparto de tráfico y recuperación de un target |
| Base de datos | RDS PostgreSQL, DB subnet group | `db.t3.micro`, 20 GiB gp3, cifrada, sin IP pública, `MultiAZ=false`, backup de 1 día | Alta y consulta de pedido reales; aislamiento de red |
| Objetos | S3 | Cifrado AES-256, versionado, acceso público bloqueado | Carga/lectura/recuperación de objeto de prueba |
| Secretos | Secrets Manager | Usuario RDS y contraseña generada; la aplicación la consulta en tiempo de ejecución | Sin contraseña escrita en código |
| Seguridad | Security Groups, IMDSv2, EBS cifrado | ALB→App `8080`; App→RDS `5432`; IMDSv2 obligatorio; volumen `gp3` cifrado | Puertos y origen restringidos |
| Operación | CloudWatch Logs, Dashboard, Alarmas | Logs de acceso/error; retención 1 día; dashboard y 4 alarmas | Evidencia de métricas, logs y una alarma |

## 3. Observabilidad y análisis

### Implementado en la plantilla

| Componente | Cobertura |
|---|---|
| CloudWatch Agent | Instalado en cada EC2 y configurado para enviar `access.log` y `error.log` al log group de Tangamandapio |
| CloudWatch Dashboard | CPU del ASG, hosts healthy, p95/5xx del ALB, CPU y conexiones de RDS |
| Alarmas | CPU alta de aplicación, targets no saludables, 5xx del ALB y CPU alta de RDS |
| Logs Insights | Disponible para analizar el log group desplegado; todavía no existe una consulta guardada ni evidencia vigente |

### Zabbix: decisión explícita

**Zabbix no está preparado ni se levantará en esta ventana.** No hay archivos, contenedor, EC2, base de datos ni recurso Zabbix en IaC. Agregarlo exige administrar por lo menos un servidor Zabbix, base de datos y agentes, lo que aumenta costo, superficie de operación y tiempo de limpieza.

Para el laboratorio, **CloudWatch es el sistema de monitoreo oficial seleccionado**: ya recibe métricas nativas de ALB/EC2/RDS, centraliza logs y permite dashboard y alarmas. El agente de CloudWatch puede ampliar la recolección de métricas, logs y trazas desde EC2, pero la configuración actual solo publica logs de aplicación; métricas de memoria, disco y proceso aún no están configuradas. [AWS: CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

**Mejora opcional posterior, sin Zabbix:** agregar al agente una sección `metrics` con memoria, disco y `procstat` para Gunicorn; crear consulta Logs Insights/alarma de errores; instrumentar OpenTelemetry/X-Ray. No se declarará ninguna de estas mejoras como realizada hasta probarla.

## 4. Qué falta ejecutar y demostrar

| Orden | Acción pendiente | Evidencia requerida |
|---|---|---|
| 1 | Confirmar y ejecutar el change set | Stack `CREATE_IN_PROGRESS` y luego `CREATE_COMPLETE` |
| 2 | Esperar ALB, ASG y RDS | Inventario de servicios, 2 targets healthy |
| 3 | Probar portal, `/health`, `POST /api/orders` y `GET /api/orders` | Capturas/salidas HTTP reales contra ALB |
| 4 | Verificar RDS privada y acceso externo rechazado | Configuración y resultado de prueba `pt-sec-02-rds-deny.py` |
| 5 | Ejecutar S3, alarma y recuperación solo con autorizaciones específicas | Resultados de `pt-sto-01`, `pt-mon-01`, `pt-dr-01`; este último genera costo temporal |
| 6 | Mostrar dashboard, logs y alarmas | Capturas CUR-AWS-08 |
| 7 | Medir RTO/RPO y probar recuperación/caída de target | CUR-AWS-07 y CUR-AWS-09 |
| 8 | Eliminar stack, vaciar S3 si fuera necesario y verificar cero recursos del proyecto | CUR-AWS-10 y cierre del laboratorio |

## 5. Limitaciones honestas del laboratorio

- El ALB usa **HTTP**, no HTTPS: no hay dominio/ACM configurado. No se debe afirmar TLS ni WAF.
- NAT Gateway único y RDS `MultiAZ=false`: son decisiones de costo de laboratorio, no alta disponibilidad completa de producción.
- Retención de logs y backup RDS: 1 día; no cubren una política empresarial final.
- `LabInstanceProfile` es una dependencia provista por AWS Academy; no representa un rol propio de mínimo privilegio.
- La aplicación desplegada desde CloudFormation contiene un portal estático ligero. El build Vite de desarrollo y la integración real con Azure no se declaran desplegados en AWS.
- No se incluyen CloudTrail, VPC Flow Logs, GuardDuty, WAF, SNS, X-Ray, Zabbix ni una acción automática de notificación. Son mejoras de producción o de una fase posterior.

## 6. Servicios adicionales evaluados

| Servicio o control | Qué aporta | Viabilidad en el laboratorio | Decisión propuesta |
|---|---|---|---|
| Métricas ampliadas de CloudWatch Agent | Memoria, disco y proceso Gunicorn mediante `procstat` | Viable sin servidor adicional; las métricas personalizadas pueden generar cargos | **Prioridad alta**, habilitar solo durante la ventana de pruebas si se acepta el costo marginal |
| CloudWatch Logs Insights | Consultas de 5xx, latencia y errores del portal | Viable; el costo depende de datos analizados y el volumen de una demo es bajo | **Prioridad alta**, crear una consulta reproducible tras desplegar |
| CloudTrail de eventos de administración | Auditoría de creación/cambios de red, RDS, IAM y CloudFormation | Viable si no existe ya un trail equivalente; una primera copia regional de management events puede ser gratuita, pero data events generan cargo | **Prioridad media**, revisar primero trails existentes y no habilitar data events |
| VPC Flow Logs con tráfico `REJECT` | Evidencia de segmentación y denegaciones de red | Viable, pero requiere destino/IAM y genera ingesta de logs | **Prioridad media**, solo si el LabInstanceProfile permite el rol y se acepta el costo de logs |
| SNS para alarmas | Notificación por correo cuando una alarma entra en estado `ALARM` | Viable; requiere suscripción y confirmación del correo | **Prioridad media**, opcional para una demostración visible |
| CloudWatch Synthetics Canary | Prueba periódica externa de `/health` y flujo HTTP | Viable técnicamente; crea una función programada y consumo asociado | **Prioridad media**, mejor después de probar manualmente el ALB |
| AWS Systems Manager | Operación sin abrir SSH/RDP y evidencia de administración segura | Viable solo si `LabInstanceProfile` tiene permisos de SSM | **Prioridad media**, comprobar permisos tras desplegar |
| CloudTrail Lake / Insights | Análisis avanzado de auditoría y anomalías API | Genera costos de ingesta/consulta | **No para esta ventana** |
| AWS WAF | Reglas administradas y limitación de peticiones frente al ALB | Viable, pero cobra por Web ACL, reglas y solicitudes inspeccionadas | **Diseño de producción**, no laboratorio con presupuesto limitado |
| GuardDuty, Security Hub, Inspector, Config, Macie | Detección, postura y cumplimiento avanzados | Técnicamente viables, pero con costos, permisos y tiempo de ajuste | **Diseño de producción**, documentar pero no desplegar ahora |
| ACM + Route 53 + HTTPS | TLS real y redirección segura al ALB | Certificado ACM puede no costar, pero se necesita dominio/DNS controlado; Route 53 y dominio sí pueden costar | **Pendiente de dominio**, no afirmar HTTPS hasta implementarlo |
| RDS Multi-AZ, segundo NAT y AWS Backup | Continuidad real y mayor disponibilidad | Aumentan significativamente el consumo de laboratorio | **Producción**, documentar como mejora; la prueba de restore temporal se autoriza por separado |
| SQS/EventBridge con DLQ hacia Azure | Outbox/reintentos para el flujo de pedidos a WMS | Útil para la fase multicloud; no está incluido en la aplicación AWS actual | **Fase Azure**, implementar con contrato de eventos real |
| Zabbix | Monitorización OSS centralizada y plantillas de hosts | Exige operar servidor, base de datos y agentes adicionales | **Descartado para esta ventana**; CloudWatch cubre la evidencia solicitada con menor complejidad |

CloudWatch ya cubre el núcleo de observabilidad de esta solución. AWS también ofrece canaries para comprobar endpoints de manera programada; cada canary crea recursos Lambda y se debe incluir en el presupuesto de pruebas. [CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) Para auditoría, no se deben habilitar data events de CloudTrail en un laboratorio sin revisar costo: esos eventos sí generan cargos, mientras que la primera copia regional de management events puede ser gratuita. [AWS CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-trail-manage-costs.html)

## 7. Guardas de costo y seguridad

1. Nunca ejecutar recursos del change set sin una confirmación inmediata del responsable.
2. Mantener el stack en la ventana mínima necesaria y registrar cada prueba real.
3. No tocar recursos que no lleven el identificador o etiqueta del proyecto.
4. Tras las pruebas, eliminar exclusivamente `tangamandapio-live-20260930`, verificar RDS/EC2/ALB/NAT/S3 del proyecto y terminar el laboratorio.

