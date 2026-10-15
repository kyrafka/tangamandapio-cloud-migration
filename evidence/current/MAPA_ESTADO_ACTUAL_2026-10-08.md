# Mapa del estado actual — 08/10/2026

**Corte:** 08/10/2026, después del apagado. **Objetivo:** detener costos de la demostración y conservar IaC suficiente para una reconstrucción vacía. No se conservaron snapshots.

## Estado de nube

### AWS — `us-east-1`

- Se eliminaron los stacks `tangamandapio-live-20261005` y `tangamandapio-voice-recordings`, además de los tres buckets del proyecto y sus versiones.
- Verificación posterior: cero stacks/buckets del proyecto; cero instancias EC2 activas; VPC, balanceador y RDS ausentes; NAT Gateway en estado `deleted`; sin volúmenes, EIP asociados ni snapshots manuales o automáticos.
- Se eliminó también la clave Azure externa de Secrets Manager y el parámetro seguro SSM `/tangamandapio/azure/function-key`.
- El inventario por tags conserva entradas históricas de recursos terminados/eliminados; las consultas de estado confirman que no son instancias o volúmenes activos. La pila base administrada por AWS Academy no se modificó.
- Se borraron los pedidos, cuentas demo, base PostgreSQL, documentos, grabaciones (no había audios bajo `voice-recordings/`) y el historial de versiones del artefacto. No hay recuperación desde la nube.

### Azure — `westus`

- El Resource Group `rg-tangamandapio-261005-wus` y sus 10 recursos se eliminaron. `az group exists` devuelve `false`.
- El Key Vault anterior aparece en la lista de vaults con soft-delete; no es un recurso activo ni forma parte de un Resource Group vivo. La reconstrucción usa un nombre nuevo para evitar colisión con ese período de recuperación.
- Se eliminaron la Function App, su plan, Storage/Queue/Blob, Application Insights, Log Analytics, alertas y Action Groups del entorno anterior.
- La clave de Function almacenada fuera del grupo se eliminó de AWS. No quedan conexiones operativas entre Azure y AWS.

## Infraestructura como código y reconstrucción

| Área | Fuente actual | Validación/estado |
|---|---|---|
| AWS portal | `iac/cloudformation/aws-lab.yaml`, `deploy.sh`, `package_portal_artifact.sh`, `rebuild.sh` | Plantilla validada. El rebuild crea en dos fases, inicia EC2 en cero y luego habilita dos instancias. Perfil por defecto: sin Multi-AZ, WAF ni AWS Backup, un día de retención RDS. |
| AWS grabaciones | `iac/cloudformation/voice-recordings.yaml` | El rebuild la crea tras restaurar el rol del portal. `destroy.sh` vacía versiones y elimina explícitamente el bucket que el template retiene. |
| Terraform AWS `environments/demo` | `iac/modules/aws_network` | Código separado, sin state del proyecto; no aplicarlo como actualización del portal. |
| Azure anterior | `iac/environments/azure-demo` | State histórico, no reconciliado con el grupo eliminado. No usar para recrear ni destruir el nuevo entorno. |
| Azure rebuild | `iac/environments/azure-rebuild` | `terraform validate` pasó; plan aislado: 15 por crear, 0 cambios, 0 destrucciones. No se aplicó. Requiere revisar nombres globales y generar el ZIP local de la Function. |

Para reconstruir: aplicar primero el entorno nuevo `azure-rebuild`, obtener endpoint y clave nueva de Function, guardarla en AWS Secrets Manager sin pasarla por Git/chat/historial de shell y ejecutar después `iac/cloudformation/rebuild.sh`. El rebuild de AWS necesita credenciales vigentes de AWS Academy; los recursos del proyecto están apagados hasta entonces.

En Windows/WSL, los scripts Bash aceptan `AWS_CLI='/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe'` si la CLI no está instalada en WSL.

## Alcance funcional y pendientes

- Azure/WMS sigue siendo una simulación académica de Blob/Queue e inventario ficticio, no un WMS enlazado a existencias comerciales.
- La reconstrucción no se probó levantando un segundo stack; solo se validaron plantillas, Terraform, paquetes y pruebas locales. No afirmar que la nube quedó desplegada.
- El paquete Azure desplegado anteriormente no se pudo comparar binariamente con el ZIP local; el entorno nuevo debe construirse desde el ZIP versionado local.
- A/V WebRTC entre dos navegadores reales, grabación/reproducción, dominio y HTTPS confiable siguen pendientes.
- El portal local antes disponible en `127.0.0.1:8080` estaba en otra copia de trabajo; esta carpeta contiene las fuentes de IaC y la aplicación desplegada en AWS.

## Verificaciones realizadas en este corte

- AWS: stack y buckets ausentes, RDS/EC2 ausentes, backups consultados sin resultados, sin NAT activo ni EIP asociada.
- Azure: Resource Group ausente; el vault antiguo está en recuperación por soft-delete y no activo.
- Local: `aws-lab.yaml` valida; `bash -n` pasó en los scripts CloudFormation; `terraform fmt -check -recursive iac` y `terraform validate` de `azure-rebuild` pasaron. Las 14 pruebas unitarias del WMS local pasaron antes del apagado.
