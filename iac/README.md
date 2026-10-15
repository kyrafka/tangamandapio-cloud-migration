# Infraestructura como código — corte 14/10/2026

Última actualización: 14/10/2026. Se publicó el artefacto candidato v11 en el bucket de releases y se ejecutó un change set de CloudFormation. El stack entró en `UPDATE_IN_PROGRESS`, el primer destino nuevo no pasó el health check y el ALB empezó a devolver 503. Una denegación explícita `voc-cancel-cred` impide consultar el estado del stack o verificar su recuperación; no se afirma que el despliegue terminara ni que v10 haya sido restaurado. El último corte sano confirmado antes de v11 fue v10, `UPDATE_COMPLETE`, `IN_SYNC`, 2/2 destinos sanos. En la reconsulta, AWS Academy mostró `Lab status: stopping` aunque la sesión STS aún autenticaba; no se hizo ninguna acción de inicio/cambio desde esa página. En Azure no se aplicaron cambios en esta operación. Véase la [evidencia detallada del intento v11](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md) y la [revalidación anterior](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md).

Puerta local más reciente (`tests/run_local_quality.ps1 -ValidateTerraform`):
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

La plantilla local se reforzó después del intento fallido: usa
`AutoScalingInstanceRefresh` con 100% de salud mínima, 125% de capacidad máxima,
una instancia extra de margen, warmup de 420 s y bake de 180 s. No se aplicó porque el estado del stack está
bloqueado/no confirmado. `python_runtime_guard_test.sh` y `cfn-lint` aprobaron;
la validación remota `cloudformation validate-template` fue denegada por la
política del laboratorio. Este cambio local todavía no forma parte del change
set v11 ejecutado.

La puerta también prueba fail-closed en `deploy.sh`, `rebuild.sh`, `destroy.sh`,
PT-STO-01 y PT-MON-01 ante nombres de stack ausentes/genéricos, verifica con
mock que PT-MON-01 devuelve la alarma al estado original si ocurre un error y
cubre el diagnóstico AWS de solo lectura con tres escenarios mock:
sano, degradado y acceso denegado.

| Dominio | Fuente de verdad actual | Estado de despliegue |
|---|---|---|
| AWS portal | CloudFormation: `cloudformation/aws-lab.yaml` y `cloudformation/rebuild.sh` | El paquete legado v11 (SHA `2a834...`) se subió y el change set comenzó después de validar drift `IN_SYNC`; el ALB dio 503 y AWS bloqueó consultas de estado/recuperación. Resultado final desconocido. La plantilla local apunta ahora al paquete portable v11 (SHA `ef3ffe...`), aún no subido a S3, e incorpora Instance Refresh con margen para una instancia adicional. No iniciar otro despliegue ni afirmar v11 vivo hasta recuperar lectura, resolver el stack y subir/verificar el artefacto local. El último corte sano previo fue v10. Véase [intento v11](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md). |
| AWS grabaciones | CloudFormation: `cloudformation/voice-recordings.yaml`, creado por `cloudformation/rebuild.sh` | Último registro 09/10: `CREATE_COMPLETE`, drift `IN_SYNC`; sin objetos grabados. Estado actual no revalidado. |
| Red AWS de ejemplo | Terraform: `environments/demo` → `modules/aws_network` | Formato y validación correctos; no tiene state y no administra el stack vivo. Un `apply` crearía una VPC adicional. |
| WMS Azure anterior | Terraform histórico: `environments/azure-demo` → `modules/azure_operations` | Su state sigue apuntando al grupo anterior; no usarlo. El Resource Group anterior fue eliminado. |
| Reconstrucción Azure | Terraform: `environments/azure-rebuild` → `modules/azure_operations` | Último Terraform plan registrado a las 12:40: `No changes`, sin `apply`; Function health 200 a las 13:03 y smoke 12:30 confirmó Function `Running`/HTTPS-only, guards y venta/recepción compensada desde productor local. No se probó entrega de alertas. No hay VNet integration, así que la Function no es destino privado de VPN. ZIP se publicó por Azure CLI/Entra; FTP/SCM básico deshabilitado. Evidencia: `evidence/current/azure/AZURE-ERP-E2E-2026-10-14.md` y `evidence/current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md`. El state local está ignorado y puede contener datos sensibles; no versionarlo ni copiarlo a otra máquina. |
| Interconexión privada AWS–Azure | Azure VPN Gateway/BGP: `environments/aws-azure-vpn`; lado AWS separado en `cloudformation/aws-azure-vpn.yaml` | IaC declara VNet `10.20.0.0/16`, subnet Flex `10.20.2.0/27` delegada a `Microsoft.App/environments` y gateway BGP activo-activo; validación y 2 pruebas Terraform pasan. El preflight fail-closed cubre 13 escenarios mock, dos conexiones AWS, cuatro túneles BGP y rutas solo a la tabla app. No desplegado: AWS denegó lecturas; no se afirma estado presente. [Diseño y límites](environments/aws-azure-vpn/README.md). |
| Alternativa overlay AWS–Azure | Propuesta Tailscale: `environments/aws-azure-tailscale/README.md`; preflight de solo lectura `scripts/check_tailscale_prerequisites.py` | AWS STS y VPC `10.10.0.0/16` verificados; no hay VNet Azure. Cliente Tailscale local offline (`NoState`) y no se detectó clave efímera. No hay routers, rutas ni túnel desplegados. Este diseño no se cuenta como AWS Site-to-Site VPN ni como evidencia multinube hasta probar tráfico extremo a extremo. |
| Function Flex privada | Terraform: `environments/azure-flex-private` | Root blue-green validado con AzureRM 4.79.0 y pruebas mock 3/3; costo y bootstrap público con doble compuerta, identidad administrada, package blob endpoint, Private Endpoint y DNS Azure. No aplicado: falta la VNet/subnets, el grupo `rg-tangama-private-network` no existe en Azure, y AWS no permite leer la VPC/stack. |
| DNS privado AWS→Azure | CloudFormation opcional: `cloudformation/aws-azure-vpn.yaml`; orquestación en `scripts/deploy_aws_vpn.ps1` | Hosted zone privada Route 53 + registro A solo se habilitan pasando juntos el FQDN exacto de la Function y su IP PE validada en `10.20.2.4–30`. Desactivado por defecto; no desplegado. No configura dominio público ni HTTPS para usuarios. El gate local cubre 13 escenarios mock. |
| Recuperación RDS | Script `tests/aws/pt-dr-01-rds-restore.sh` + sonda SQL temporal vía SSM | PT-DR-01 pasó en AWS el 13/10 08:57: RTO 289 s, marcador y conteos de 14 tablas verificados, limpieza confirmada. `rds:DescribeDBInstances` fue denegado en la revalidación de las 11:52, así que la disponibilidad actual no está confirmada. La prueba demuestra recuperación en aquel corte, no estado presente. |

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
