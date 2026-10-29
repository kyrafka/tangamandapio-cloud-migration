# Infraestructura como código

## Estado de servicios — corte 29/10/2026

Este es el estado que se pudo observar; no equivale a una aprobación para desplegar.

| Plataforma | Recursos/funciones del proyecto | Estado y límite de verificación |
|---|---|---|
| AWS | CloudFormation del portal; ALB/HTTPS, WAF, Auto Scaling/EC2, RDS PostgreSQL, S3, Secrets Manager, CloudWatch y SNS figuran en el último inventario documentado. | El registro del 27/10 indica ASG con 2 instancias deseadas, máximo 5, RDS Multi-AZ cifrado con 7 días y WAF asociado. El 29/10 STS autenticó, pero una política explícita denegó `List`/`Describe`; no se pudo confirmar el inventario actual. El dominio respondió 503. |
| Azure | Function Y1 y Function Flex privada; Storage, Key Vault, Application Insights, Log Analytics, alertas, VNet, Private Endpoint, DNS privado y VPN Gateway P2S. | Azure CLI inventarió esos recursos. La Function Y1 respondió 200 por su endpoint público; la Flex privada respondió 403 desde Internet, esperado con acceso público deshabilitado. El gateway figura `Succeeded`; el estado del recurso no demuestra por sí solo una sesión VPN activa. |
| Interconexión | Azure OpenVPN Point-to-Site más un router EC2 como siguiente salto hacia el WMS Private Endpoint. | El reporte del 29/10 describe HTTPS 200 desde las instancias AWS al endpoint privado. Es una ruta limitada al WMS, con un router y un gateway como puntos únicos de falla; no es AWS Site-to-Site administrada ni BGP. No se pudo revalidar AWS el 29/10. |
| Recuperación | Copia de fixture sintético S3 → Azure Blob y restauración con SHA-256 coincidente. | Verifica un objeto de prueba, no backup/restore de PostgreSQL, RPO/RTO de base de datos ni recuperación de toda la aplicación. |

La ruta pública actual mostró HTTP 503 durante esta revisión. Hasta recuperar y comprobar el servicio no se deben presentar estados históricos de salud como estado vigente.

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
