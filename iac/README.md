# Infraestructura como código — estado verificado 27/10/2026

## Corte más reciente — 27/10/2026, 17:05 America/Chicago

Este corte reemplaza los estados contradictorios de las notas históricas que
siguen debajo. AWS STS funciona; CloudFormation está `UPDATE_COMPLETE`, el
dominio HTTPS responde 200, el ALB tiene 2/2 destinos sanos, WAF está asociado
y RDS está disponible, cifrada, Multi-AZ y con 7 días de retención. El ASG está
en 2 instancias (mínimo 2, máximo 5), por lo que todavía no hay evidencia de
escalado automático 2→3.

En Azure ya está desplegada la Function Flex `tangama-wms-flex-261013` con
acceso público deshabilitado y Private Endpoint `10.20.1.4`; su zona DNS privada
está enlazada a la VNet. La Function reportó siete funciones y procesó eventos
sintéticos con idempotencia antes de cerrar el acceso público. La Function Y1
anterior continúa respondiendo health 200. AWS todavía no tiene ruta privada a
la nueva Function, así que no hay cutover ni prueba AWS→Flex. No se encontró
una cola SQS del proyecto ni una Lambda de Tangamandapio.

Pendiente de despliegue/verificación: conexión privada AWS–Azure (la SCP de
AWS Academy deniega `ec2:CreateCustomerGateway`), SQS+Lambda+DLQ con un rol de
mínimo privilegio autorizado, SSO/MFA con Entra ID, copia y restauración entre
nubes, medición reproducible del escalado 2→3 después de corregir el cuello de
botella RDS, y prueba extremo a extremo desde AWS hacia el WMS privado. No se
ha demostrado capacidad para 3,000 usuarios concurrentes. Véase la
[evidencia del corte 27/10](../evidence/current/CLOUD-STATUS-2026-10-27.md).

Revalidación adicional, 27/10/2026: dominio y WMS health HTTPS respondieron
200; el token AWS Academy autenticó por STS. El P2S fallback ahora pasa
`fmt`/`validate` y 2 pruebas mock, y un plan de solo lectura encontró la VNet y
`GatewaySubnet` (3 recursos propuestos; no aplicados). Ambas EC2 están online
por SSM y tienen egreso HTTPS; no se encontró OpenVPN instalado. P2S sigue sin
desplegarse y no equivale a Site-to-Site; los requisitos de DNS privado y
certificados siguen pendientes. Véase la [evidencia del preflight P2S](../evidence/current/azure/AZURE-P2S-PREFLIGHT-2026-10-27.md).

Revalidación 27/10, 20:08–20:14 UTC: token temporal aceptado por STS; CloudFormation `UPDATE_COMPLETE`, drift nuevo `IN_SYNC`/0, ASG y targets 2/2, dominio HTTPS por Cloudflare y Azure Function health 200. RDS disponible, privada/cifrada, Multi-AZ y retención de 7 días; WAF asociado al ALB y canario XSS bloqueado (403). PT-PERF-01 de solo lectura pasó 500/500 GET al `/health`, concurrencia 20, p95 547.78 ms, sin errores; CloudWatch reportó ASG a 4.05% CPU y RDS a 7.66%/4 conexiones. ASG siguió en 2 y no se demostró escala 2→3 ni capacidad para 3,000 usuarios. IAM deniega `CreateRole`/`PassRole`; VPN/red privada, SQS/Lambda/DLQ, SSO/MFA y backup cruzado siguen sin desplegar. La VNet privada existe, pero no tiene gateway, private endpoint ni integración con la Function, que continúa en Y1 pública. [Evidencia 27/10](../evidence/current/aws/AWS-LIVE-VALIDATION-2026-10-27-rds-pool-v26.md).

La tabla inferior conserva el inventario de 16/10 como antecedente histórico. Para el estado actual, prevalece la revalidación anterior y su evidencia enlazada.

El intento v11 del 14/10 quedó registrado con el resultado observado en ese momento; sus notas de “estado desconocido” son históricas y quedaron superadas por la actualización completada el 15/10. Véase la [evidencia del intento v11](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

Puerta general anterior al release v12 (`tests/run_local_quality.ps1 -ValidateTerraform`; corte 14/10, histórico):
**165 pruebas Python**, 14 pruebas Node, PT-PERF-02 (40 transacciones aisladas),
auditoría de dependencias sin vulnerabilidades conocidas, build frontend,
CloudFormation `cfn-lint` y Terraform `fmt`/`validate`/tests aprobaron sin
`apply` ni escrituras cloud. La suite Tailscale aporta 8 pruebas mock y el
preflight real está bloqueado por prerrequisitos ausentes; no es evidencia de
túnel. v10 fue el último release sano confirmado antes del intento v11; el
artefacto v11 legado sí se subió y su update falló con 503, pero el estado final
del stack no se puede leer. El empaquetador ahora fija permisos de archivos y
directorios y produce el mismo hash portable en WSL y Git Bash; ese nuevo
artefacto todavía no está subido a S3. Después pasaron 17 pruebas del harness
Azure, 6 pruebas CSV, 5 pruebas de catálogo y 2 pruebas locales de autorización
para seis roles.

La plantilla aplicada usa `AutoScalingRollingUpdate`: mantiene dos instancias
en servicio, reemplaza una por lote y espera hasta siete minutos para la
estabilización del health check antes del lote siguiente. `python_runtime_guard_test.sh`
aprobó en la validación local del release. `cfn-lint` no estaba instalado en el
entorno de esta revisión; no se afirma una validación con esa herramienta.

La puerta también prueba fail-closed en `deploy.sh`, `rebuild.sh`, `destroy.sh`,
PT-STO-01 y PT-MON-01 ante nombres de stack ausentes/genéricos, verifica con
mock que PT-MON-01 devuelve la alarma al estado original si ocurre un error y
cubre el diagnóstico AWS de solo lectura con tres escenarios mock:
sano, degradado y acceso denegado.

La puerta local vigente pasó CloudFormation `cfn-lint`/`validate-template` y
Terraform `fmt`, `init`, `validate` en las seis raíces configuradas, más cinco
pruebas mock de costo/red. Además, `azure-rebuild` se planeó contra su backend
remoto y terminó `No changes` a las 05:57 UTC, sin `apply`. No se ejecutó un
plan AWS en vivo; estas validaciones no prueban que todos los estados Terraform
administren los recursos desplegados.

| Dominio | Fuente de verdad actual | Estado de despliegue |
|---|---|---|
| AWS portal | CloudFormation: `cloudformation/aws-lab.yaml` y `cloudformation/rebuild.sh` | Revalidado 27/10: stack `UPDATE_COMPLETE`, HTTPS del dominio 200, ALB targets 2/2 sanos, WAF asociado; RDS disponible, cifrada, Multi-AZ, retención 7 días. ASG 2/2 (min 2, max 5); el escalado 2→3 no se ha demostrado. [Evidencia del corte](../evidence/current/CLOUD-STATUS-2026-10-27.md). |

| AWS grabaciones | CloudFormation: `cloudformation/voice-recordings.yaml`, creado por `cloudformation/rebuild.sh` | Último registro 09/10: `CREATE_COMPLETE`, drift `IN_SYNC`; sin objetos grabados. Estado actual no revalidado. |
| Red AWS de ejemplo | Terraform: `environments/demo` → `modules/aws_network` | Formato y validación correctos; no tiene state y no administra el stack vivo. Un `apply` crearía una VPC adicional. |
| WMS Azure anterior | Terraform histórico: `environments/azure-demo` → `modules/azure_operations` | Su state sigue apuntando al grupo anterior; no usarlo. El Resource Group anterior fue eliminado. |
| Reconstrucción Azure | Terraform: `environments/azure-rebuild` → `modules/azure_operations` | 16/10 09:56: Function `Running`/HTTPS-only, health HTTPS/TLS 200 y dos eventos procesados con éxito según App Insights. Plan normal y `refresh-only` `No changes`, sin `apply`. No hay VNet Azure del proyecto. [Revalidación 09:56](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0950UTC.md). |
| Interconexión privada AWS–Azure | Azure VPN Gateway/BGP: `environments/aws-azure-vpn`; lado AWS separado en `cloudformation/aws-azure-vpn.yaml` | No hay túnel/rutas entre nubes. La VNet `10.20.0.0/16`, la Function privada y su Private Endpoint existen; AWS Academy denegó `ec2:CreateCustomerGateway`. No sortear la política ni reportar conectividad privada. [Diseño y límites](environments/aws-azure-vpn/README.md) y [evidencia del corte](../evidence/current/CLOUD-STATUS-2026-10-27.md). |
| Alternativa overlay AWS–Azure | Propuesta Tailscale: `environments/aws-azure-tailscale/README.md`; preflight de solo lectura `scripts/check_tailscale_prerequisites.py` | AWS STS y VPC `10.10.0.0/16` verificados; no hay VNet Azure. Cliente Tailscale local offline (`NoState`) y no se detectó clave efímera. No hay routers, rutas ni túnel desplegados. Este diseño no se cuenta como AWS Site-to-Site VPN ni como evidencia multinube hasta probar tráfico extremo a extremo. |
| Function Flex privada | Terraform: `environments/azure-flex-private` | Desplegada en `rg-tangamandapio-rebuild-wus`, estado Terraform remoto, plan final `No changes`, pruebas mock 3/3. Identidad administrada, colas/Blob, Private Endpoint `10.20.1.4` y DNS privado en VNet; `publicNetworkAccess=Disabled` (health público 403 esperado). No es accesible desde AWS hasta desplegar y probar rutas privadas. El WMS Y1 anterior sigue activo para continuidad. |
| DNS privado AWS→Azure | CloudFormation opcional: `cloudformation/aws-azure-vpn.yaml`; orquestación en `scripts/deploy_aws_vpn.ps1` | Hosted zone privada Route 53 + registro A solo se habilitan pasando juntos el FQDN exacto de la Function y su IP PE validada en `10.20.2.4–30`. Desactivado por defecto; no desplegado. No configura dominio público ni HTTPS para usuarios. El gate local cubre 13 escenarios mock. |
| Recuperación RDS | Script `tests/aws/pt-dr-01-rds-restore.sh` + sonda SQL temporal vía SSM | PT-DR-01 pasó 16/10: marcador y conteos verificados, RTO 258 s y RPO superior observado 8 s; copia y snapshot temporales eliminados y verificados. RDS principal sigue disponible, privada, cifrada, Single-AZ y backup 1 día. No demuestra failover Multi-AZ ni garantía de RPO. [Evidencia 09:26 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0926UTC.md). |

## Criterios de operación

- No administrar un mismo recurso con CloudFormation y Terraform.
- En AWS, indicar siempre el `STACK_NAME` exacto del inventario actual; los scripts de despliegue, reconstrucción y borrado rechazan nombres ausentes o inválidos y no tienen un default que pueda apuntar a una pila histórica. Revisar el change set y usar `APPLY_CHANGE_SET=true` más confirmación explícita para ejecutarlo. `deploy.sh` conserva todos los parámetros actuales, incluso los `NoEcho`.
- En Azure, `terraform validate` es una comprobación de sintaxis, no prueba de que el state represente los recursos actuales. El 14/10 07:18, un plan completo consultó ARM y no mostró cambios. El state local no se comparte y no debe versionarse.
- Para reconstruir desde cero, primero confirmar que el grupo activo ya no existe y revisar disponibilidad de nombres globales. El ZIP de la Function debe generarse desde `app/azure_function`; después publícalo con Azure CLI/Entra (`az functionapp deployment source config-zip`). Los nombres nuevos implican actualizar el endpoint y la clave Azure en AWS. Los scripts CloudFormation exigen siempre un nombre de stack verificado, sin default histórico.
- `cloudformation/rebuild.sh` requiere Azure activo y la clave vigente en AWS Secrets Manager. Arranca con cero EC2, publica el artefacto local de `app/aws_release/current` y después habilita capacidad. Por defecto desactiva Multi-AZ/WAF/AWS Backup y deja un día de backup RDS.
- La VPN AWS–Azure está separada de la plantilla del portal para no cambiar su VPC/RDS. Desplegar solo después de revisar la cuenta y costo recurrente; `validate` no implica despliegue ni conectividad. La Function `Y1` está verificada públicamente accesible, sin VNet integration. La red, Function Flex y Private Endpoint/DNS no están creados. Los roots locales `aws-azure-vpn` y `azure-flex-private` describen el destino; ambos requieren preflight de inventario, presupuesto, plan guardado y aprobación antes de aplicar. El DNS privado Route 53 es opcional, requiere el hostname/IP PE exactos y no es el dominio público/HTTPS final.
- Tailscale puede servir para un piloto overlay si el docente acepta esa tecnología, pero requiere un subnet router en cada nube, forwarding, rutas aprobadas en el tailnet, ACL mínima y rutas de retorno en ambas redes. No sustituye silenciosamente la VPN IPsec/BGP evaluada. Correr `python .\iac\scripts\check_tailscale_prerequisites.py` antes de diseñar el apply; es solo lectura y falla cerrado ante estado faltante.
- `tests/aws/pt-dr-01-rds-restore.sh` modifica temporalmente la base de laboratorio para probar que un marcador confirmado antes del snapshot exista tras el restore. Aun con limpieza automática, ejecutarlo solo en ventana de laboratorio; si el proceso se interrumpe, revisar los identificadores de test que reporte antes de reintentar.
- Antes de borrar el corte, guardar los artefactos desplegados y un snapshot final de RDS; vaciar buckets solo tras verificar que no contienen archivos de usuario/grabaciones. El stack/sesión Academy (administrado por AWS Academy) se cierra después de borrar los stacks del proyecto.
- No subir archivos `terraform.tfstate`, `terraform.tfvars`, claves ni salidas con secretos.
- El inventario Azure actual es una demostración de despacho/inventario ficticio, no integración con un WMS/ERP real.
