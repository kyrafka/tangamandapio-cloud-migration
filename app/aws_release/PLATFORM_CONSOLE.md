# Centro de nube, seguridad y usuarios

El [mapa de estado actual](../../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md)
es la fuente para saber qué quedó activo en AWS. Esta guía describe el módulo y
su preparación; no equivale a una validación autenticada de navegador.

El módulo local está en `/platform`. Lo pueden abrir Administración y
Operaciones TI. El backend vuelve a comprobar el rol; ocultar el acceso del
menú no es la barrera de seguridad.

Incluye:

- solicitudes, latencia p95, errores 5xx y destinos saludables del ALB;
- CPU y conexiones de RDS;
- bloqueos WAF y capacidad del Auto Scaling Group cuando esos recursos publican
  métricas configuradas;
- estado de controles del portal y contadores del proceso web actual;
- trazabilidad de la cola transaccional: consulta bajo demanda del estado final
  de cada evento en Azure y reintento auditado para Operaciones/Administración;
- edición de rol, empresa y estado de cuentas; restablecimiento de contraseña
  con revelado único. El API invalida las sesiones y audita los cambios.

El estado de Azure se consulta por evento y no modifica inventario desde esta
pantalla. Si el endpoint de cumplimiento está en modo `demo-only`, se marca
visiblemente como demostración. Los reintentos requieren confirmación y solo
Operaciones TI o Administración pueden ejecutarlos.

## Qué enseña sobre la nube y qué queda por activar

- **Balanceo y escalabilidad:** el ALB recibe tráfico y distribuye solicitudes
  entre sus destinos sanos. La consola presenta solicitudes, latencia p95,
  errores y salud del target group. Para demostrar elasticidad automática hace
  falta verificar o asociar un Auto Scaling Group real; no se afirma que exista
  solo porque el ALB tenga más de una instancia.
- **Base de datos:** PostgreSQL/RDS conserva los pedidos; la consola presenta
  CPU y conexiones cuando se configura su identificador. Multi-AZ y backups
  son propiedades de RDS, no una métrica inferida del panel.
- **Seguridad:** WAF protege el borde; la aplicación valida sesión, rol y CSRF;
  las credenciales de servicios deben venir del rol de instancia o de un
  almacén de secretos, nunca del navegador. La consola muestra controles de la
  aplicación y contadores WAF si están habilitados.
- **Integración multicloud:** AWS mantiene pedido y outbox durable; Azure recibe
  el evento por Function/Queue y guarda evidencia. El consumidor actual es una
  simulación didáctica, no un WMS con inventario real.

Para analizar experiencia dentro del navegador, el siguiente complemento es
CloudWatch RUM y Synthetics (mediciones reales y recorridos automatizados). Para
investigar solicitudes concretas, se pueden habilitar access logs del ALB a S3
y consultar agregados con Athena. Ninguno está habilitado por esta página. Para
ampliar la demostración de seguridad, CloudTrail registra actividad de cuenta;
GuardDuty y AWS Config son complementos sujetos a costo/cuota del laboratorio.

## Activar métricas reales de CloudWatch

La página no inventa valores: si no encuentra identificadores o permisos,
explica qué falta. El backend consulta exclusivamente `GetMetricData`, mediante
el rol de instancia de AWS, sin claves persistentes. La política mínima de
lectura está en `iac/modules/cloudwatch-platform-console-policy.json`.

Configura en el entorno del servicio los recursos que existan realmente:

```text
CLOUDWATCH_REGION_NAME=us-east-1
CLOUDWATCH_LOAD_BALANCER_FULL_NAME=app/<nombre>/<id>
CLOUDWATCH_TARGET_GROUP_FULL_NAME=targetgroup/<nombre>/<id>
CLOUDWATCH_RDS_INSTANCE_ID=<identificador-rds>
CLOUDWATCH_AUTO_SCALING_GROUP=<nombre-asg-si-existe>
CLOUDWATCH_WAF_WEB_ACL_NAME=<nombre-acl-si-publica-metricas>
CLOUDWATCH_WAF_REGION=us-east-1
```

El ALB y Target Group deben configurarse juntos. RDS, ASG y WAF son
independientes. `CLOUDWATCH_AUTO_SCALING_GROUP` es opcional a propósito: el
portal no declara que haya autoescalado hasta comprobar que existe y reporta
capacidad. El rol de instancia solo necesita `cloudwatch:GetMetricData`; no se
habilitan operaciones de creación, borrado ni modificación de infraestructura.

## Límite del despliegue

La política de solo lectura está preparada en código, pero no se debe afirmar
que el panel recibe métricas reales hasta comprobar permisos y configuración en
el servicio desplegado. La plantilla CloudFormation actual coincide con la del
stack según el [mapa vigente](../../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md);
antes de cualquier cambio, generar y revisar el change set. No aplicar Terraform
Azure: su state local apunta a un grupo anterior.

La serie de ALB representa tráfico agregado de la aplicación. Los contadores
de Flask son propios del proceso que atendió la vista, no una suma confiable de
todos los workers. Para monitoreo web agregado se usa ALB/CloudWatch; para
solicitudes individuales se conservan logs estructurados con ID de solicitud.
