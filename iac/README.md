# Infraestructura como código

## Estado de servicios — corte 29/10/2026

Este es el estado que se pudo observar; no equivale a una aprobación para desplegar.

| Plataforma | Recursos/funciones del proyecto | Estado y límite de verificación |
|---|---|---|
| AWS | CloudFormation del portal; ALB/HTTPS, WAF, Auto Scaling/EC2, RDS PostgreSQL, S3, Secrets Manager, CloudWatch y SNS figuran en el último inventario documentado. | El inventario del 27/10 es histórico. El 29/10 STS autenticó, pero las consultas de solo lectura fueron denegadas explícitamente por el laboratorio. El portal volvió a HTTP 200 en `/` y `/health`; no prueba por sí solo la salud de RDS ni el estado de los recursos. |
| Azure | Function Y1 y Function Flex privada; Storage, Key Vault, Application Insights, Log Analytics, alertas, VNet, Private Endpoint, DNS privado y VPN Gateway P2S. | El 29/10 Y1 health respondió 200, el inventario sintético y poison queue se consultaron y una recepción real de Queue/Function se procesó e identificó en App Insights. Flex da 403 desde Internet, esperado; Private Endpoint `Approved`. El gateway está `Succeeded`, pero la métrica P2S no tuvo puntos recientes. |
| Interconexión | Azure OpenVPN Point-to-Site más router EC2 como alternativa de acceso al WMS Private Endpoint. | La métrica registró máximo 1 cliente P2S entre 17:50–18:10 UTC, no ahora; route table vacío y AWS no revalidable por permisos. No es AWS Site-to-Site administrada ni BGP; no hay recorrido extremo a extremo vigente demostrado. |
| Recuperación | Storage de operaciones Azure con cifrado Blob y soft delete de 7 días; existe evidencia histórica de fixture S3 → Blob. | No se exportó PostgreSQL a Blob ni se restauró desde esa copia. El storage no tiene versionado de blobs y permite acceso de red pública; hace falta backup de DB, cifrado, retención aprobada y restore aislado. |

El portal público respondió 200 en esta revisión. En el reintento del 29/10 a las 21:24 UTC, STS apuntó a una cuenta distinta del inventario histórico y AWS volvió a denegar CloudFormation, EC2, Auto Scaling, ALB y RDS por `voc-cancel-cred`; no se deben presentar los estados históricos de AWS como vigentes. Evidencia: [`AWS-LIVE-ACCESS-CHECK`](../evidence/current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json).

## Mapa de IaC

### AWS — CloudFormation

- [`cloudformation/aws-lab.yaml`](cloudformation/aws-lab.yaml): stack principal del portal, red, aplicación, ALB, Auto Scaling, RDS, seguridad, observabilidad y salidas operativas.
- [`cloudformation/deploy.sh`](cloudformation/deploy.sh): prepara y revisa un change set; aplicar requiere confirmaciones explícitas.
- [`cloudformation/rebuild.sh`](cloudformation/rebuild.sh): reconstrucción con nombre de stack explícito y modo bootstrap para no arrancar EC2 antes de publicar el artefacto.
- [`cloudformation/destroy.sh`](cloudformation/destroy.sh): eliminación protegida; exige confirmaciones y conserva snapshots/secretos según las políticas configuradas.
- [`cloudformation/voice-recordings.yaml`](cloudformation/voice-recordings.yaml): recursos separados para grabaciones consentidas.
- `aws-azure-vpn.yaml`: diseño de Site-to-Site administrada. AWS Academy denegó `ec2:CreateCustomerGateway`; la plantilla no demuestra un túnel desplegado.
- `aws-azure-p2s-router.yaml`: router EC2 para la alternativa P2S. La creación de la instancia no configura por sí sola las credenciales OpenVPN ni demuestra el túnel; el material privado se mantiene fuera de Git.

### Azure y Terraform

Cada directorio de `environments/` es una raíz Terraform independiente. No se deben combinar estados ni ejecutar `apply` desde un directorio sin identificar su propósito.

| Raíz | Propósito |
|---|---|
| `azure-rebuild/` | Reconstrucción del backend WMS y sus servicios de soporte. |
| `azure-flex-private/` | Plan Flex, Private Endpoint y resolución DNS privada. |
| `azure-p2s-vpn/` | VPN Gateway P2S y configuración de acceso para el piloto privado. |
| `azure-tfstate/` | Almacenamiento remoto del estado Terraform. |
| `aws-azure-vpn/` | Diseño de VPN administrada entre nubes, sujeto a permisos de la cuenta. |
| `azure-demo/`, `demo/` | Entornos demostrativos separados; no aplicar sobre los recursos del portal. |

Los prototipos locales de IPsec/WireGuard no están validados de extremo a extremo y no forman parte de la IaC publicada.

Los módulos compartidos están en `modules/`; `modules/oci_network/` es material de comparación y no significa que OCI esté desplegado.

## ¿Se puede reconstruir tras reiniciar la cuenta?

La infraestructura está descrita parcialmente en CloudFormation y Terraform, pero **no se ha probado una reconstrucción integral desde una cuenta vacía**. Para recuperarla hacen falta, además del código:

1. Un inventario vivo, la cuenta/región correctas y permisos suficientes para leer y crear recursos.
2. El backup/snapshot de PostgreSQL que se decida conservar, credenciales nuevas y configuración segura de Secrets Manager/Key Vault.
3. Un release del portal publicado en S3 y los paquetes de Functions requeridos.
4. Certificados privados nuevos para la conexión P2S y material de configuración instalado por un canal seguro; nunca se versionan.
5. DNS y certificado HTTPS revalidados para el nombre disponible.
6. Planes revisados y una restauración de datos probada antes de habilitar el tráfico.

Un `.tfstate` no reemplaza el código ni un backup. El estado Terraform activo está en almacenamiento remoto; los estados, planes y secretos no se suben a GitHub.

## Reglas antes de cualquier cambio

- Comprueba identidad y suscripción con los mecanismos oficiales; una sesión STS válida no garantiza permiso para inventariar o desplegar.
- Lee el change set/plan completo. No ejecutes `apply`, `deploy` o `destroy` con nombre de stack supuesto.
- Conserva datos y secretos; comprueba `DeletionPolicy`, `UpdateReplacePolicy` y la retención real antes de cambios destructivos.
- WAF, RDS Multi-AZ, gateways VPN, EC2 y almacenamiento generan consumo. En AWS Academy pueden existir denegaciones SCP/IAM explícitas; no las eludas.
- No guardes credenciales de AWS/Azure, llaves VPN, PFX, state ni planes en Git o en argumentos de consola.

Guía operativa AWS: [`cloudformation/README.md`](cloudformation/README.md). Los scripts de costo y conectividad están en `scripts/`.
