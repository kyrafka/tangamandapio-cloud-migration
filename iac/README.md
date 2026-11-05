# Infraestructura como código

## Estado de recuperación — 05/11/2026

Las secciones anteriores al 05/11 son históricas. El piloto actual usa routers Tailscale propios en AWS y Azure; se verificaron un pedido privado y una conmutación del router AWS, sin afirmar BGP ni VPN Site-to-Site administrada. Se guardó una copia manual cifrada de PostgreSQL en Blob y se restauró en una base aislada con 20 tablas verificadas. El respaldo periódico y la recuperación multirregión siguen pendientes.

CloudFormation y Terraform tienen validaciones de plantilla y pruebas automatizadas, pero no se ha completado un ciclo integral de destruir y reconstruir ambas nubes. No ejecutes el borrado general como prueba. El contenedor de copias de Azure requiere importación al estado Terraform y el Key Vault debe conservarse para descifrarlas; la política ya fue importada. Consulta los requisitos de [CloudFormation](cloudformation/README.md) y [Azure](environments/azure-rebuild/README.md).

## Nueva comprobación — 04/11/2026

**Actualización posterior:** HTTPS se habilitó mediante un change set sobre la plantilla desplegada. CloudFormation terminó `UPDATE_COMPLETE`, con dos destinos saludables; el portal y `/health` respondieron 200. Una venta y reposición sintéticas recorrieron AWS→Azure y devolvieron el stock de 10 a 10; la evidencia identifica ambos eventos. El acceso admin y la lectura WMS también respondieron 200 con cabeceras de navegador. Se creó la raíz `azure-private-network` y seis recursos de VNet/subredes; el plan posterior mostró `No changes` antes de añadir localmente el plan pendiente del Key Vault VPN. La Function Flex, gateway P2S, clientes OpenVPN y failover siguen sin desplegarse. La conectividad AWS–Azure comprobada usa el endpoint público existente. Las dos suscripciones SNS solicitadas figuran confirmadas; no se probó una alerta nueva.

Se reconstruyó temporalmente la pila `tangamandapio-live-20261103` en la cuenta Academy `654654388734`. Se observó RDS PostgreSQL `available`, Multi-AZ y retención de siete días; el balanceador tenía listeners HTTP y HTTPS y el WAF estaba asociado. Tras finalizar la sesión Academy y volver a iniciarla, la primera captura mostró ASG sin instancias y errores `Client.InternalError`; no se identificó una causa específica. Después se recuperaron dos instancias saludables. No se completaron pruebas cloud autenticadas de todos los roles ni restauración PostgreSQL desde Azure Blob.

La Function `tangama-wms-261030` respondió 200 en `/api/health` y después se detuvo de forma reversible. No había gateways de red Azure en el inventario consultado; el storage, las claves y la telemetría preexistentes se conservaron. El helper opcional `scripts/postgres_dr_pilot.py` cuenta con pruebas simuladas: no automatiza por sí solo el cifrado ni la transferencia a Blob, y no constituye evidencia de recuperación real.

El medidor de Academy mostró US$18,60 antes y US$18,80 después de una interrupción de varias horas. Dado su retraso de 8–12 horas no se atribuye esa diferencia con precisión a esta ejecución. Al revisar el SNS recreado se encontraron cero suscripciones confirmadas y cero pendientes.

En una etapa anterior del 04/11 el desmontaje finalizó con `PROJECT_STACKS_AND_RETAINED_DATA_PURGED`: se observó solo la pila base, se purgaron las copias de RDS y se conservaron cinco secretos; Academy figuró `Terminated`. **Después hubo una nueva reconstrucción temporal**, descrita en la fila superior y en la evidencia de puntos únicos de fallo. Por eso, ese registro de borrado no representa el último estado de AWS y no debe usarse como prueba de que los recursos siguen apagados.

Tras la recuperación se enviaron 10.000 solicitudes a `/health` con 40 procesos; todas devolvieron 200 en unos 46 segundos, pero el ASG siguió en 2/2/5 y no escaló. Ese endpoint ejecuta `SELECT 1` en PostgreSQL, así que la prueba también cargó RDS; se detuvo la carga adicional hasta revisar métricas de base de datos. El escalado 2→3 sí ocurrió en el ensayo estático independiente del 03/11, documentado abajo.

## Revalidación de servicios — 03/11/2026

La reconstrucción temporal en AWS Academy, cuenta `654654388734`, levantó RDS privado y cifrado con Multi-AZ en `us-east-1a`/`us-east-1b` y siete días de retención. WAF respondió 200 al tráfico normal y 403 a las pruebas XSS y SQLi. El ASG escaló automáticamente de 2 a 3 y los tres destinos quedaron saludables; la carga sobre un archivo estático obtuvo 28.187 respuestas 200 y p95 de 189,55 ms. Esta prueba no establece la capacidad transaccional para 3.000 usuarios. [Resultado de escalado](../evidence/current/aws-scale-revalidation-20261103.json).

El acceso administrador y las consultas de usuarios, pedidos e inventario devolvieron 200 desde EC2. El evento AWS→Azure terminó como `demo_fulfillment_completed` y la reposición compensatoria como `demo_restock_completed`, con saldo sintético de 24→23→24. El recorrido usó HTTPS público de Azure; no se validó una ruta privada. No hay VPN/BGP activa y la SCP rechazó el dry-run de `CreateCustomerGateway`.

El desmontaje terminó con `PROJECT_STACKS_AND_RETAINED_DATA_PURGED`: en `us-east-1` solo quedó la pila base de Academy, sin EC2, ASG, ALB, RDS, NAT, EIP, WAF ni buckets del proyecto, ni snapshots manuales o backups automáticos observados. Se conservaron cinco secretos de Tangamandapio, con posibles cargos. Academy mostró **Lab terminated**, AWS **Terminated** y `00:00`.

El medidor de Academy permaneció en US$18,60/50 al inicio y al cierre; como Academy documenta un retraso de 8–12 horas, no determina el costo real ni un promedio horario de esta sesión. Azure Cost Management mostró US$0,0023796 acumulados en el mes en ambas consultas, también sujeto a retraso. Los recursos Azure preexistentes se conservaron; su ciclo integral de borrado y reconstrucción no se probó. El estado de antes de reconstruir se conserva a continuación como referencia histórica.

## Estado anterior — corte 30/10/2026

Este es el estado que se pudo observar; no equivale a una aprobación para desplegar.

| Plataforma | Recursos/funciones del proyecto | Estado y límite de verificación |
|---|---|---|
| AWS | Cuenta Academy `654654388734`, `us-east-1`. | El 30/10 confirmé en consola que solo queda la pila base del laboratorio; la pila principal y las pilas de grabaciones/router se eliminaron. RDS y el snapshot final se eliminaron; backups automáticos/retenidos de RDS: 0. EC2: no hay instancias activas, volúmenes, snapshots ni EIP. S3: 0 buckets; AWS Backup: 0 recovery points. Se conservan tres secretos del proyecto por decisión del usuario (aprox. US$1.20/mes más llamadas API). La próxima reconstrucción requiere base nueva: los datos transaccionales y grabaciones no se recuperan; el portal vuelve a sembrar maestros sintéticos. Azure no se modificó. |
| Azure | Function Y1 y Function Flex privada; Storage, Key Vault, Application Insights, Log Analytics, alertas, VNet, Private Endpoint, DNS privado y VPN Gateway P2S. | El 29/10 Y1 health respondió 200, el inventario sintético y poison queue se consultaron y una recepción real de Queue/Function se procesó e identificó en App Insights. Flex da 403 desde Internet, esperado; Private Endpoint `Approved`. El gateway está `Succeeded`, pero la métrica P2S no tuvo puntos recientes. |
| Interconexión | Azure OpenVPN Point-to-Site más router EC2 como alternativa de acceso al WMS Private Endpoint. | La métrica registró máximo 1 cliente P2S entre 17:50–18:10 UTC, no ahora; route table vacío y AWS no revalidable por permisos. No es AWS Site-to-Site administrada ni BGP; no hay recorrido extremo a extremo vigente demostrado. |
| Recuperación | Storage de operaciones Azure con cifrado Blob y soft delete de 7 días; existe evidencia histórica de fixture S3 → Blob. | No se exportó PostgreSQL a Blob ni se restauró desde esa copia. El storage no tiene versionado de blobs y permite acceso de red pública; hace falta backup de DB, cifrado, retención aprobada y restore aislado. |

El portal público respondió 200 en esta revisión. El usuario confirmó que la cuenta AWS Academy se cambió intencionalmente; el inventario del 27/10 pertenece a la cuenta anterior y no se debe reutilizar como estado de la cuenta nueva. En el reintento del 29/10 a las 21:27 UTC, STS autenticó y AWS denegó CloudFormation, EC2, Auto Scaling, ALB y RDS por `voc-cancel-cred`. Evidencia: [`AWS-LIVE-ACCESS-CHECK`](../evidence/current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json).

## Mapa de IaC

### AWS — CloudFormation

- [`cloudformation/aws-lab.yaml`](cloudformation/aws-lab.yaml): stack principal del portal, red, aplicación, ALB, Auto Scaling, RDS, seguridad, observabilidad y salidas operativas.
- [`cloudformation/deploy.sh`](cloudformation/deploy.sh): prepara y revisa un change set; aplicar requiere confirmaciones explícitas.
- [`cloudformation/rebuild.sh`](cloudformation/rebuild.sh): reconstrucción con nombre de stack explícito y modo bootstrap para no arrancar EC2 antes de publicar el artefacto.
- [`cloudformation/destroy.sh`](cloudformation/destroy.sh): eliminación protegida; purga snapshots/backups y conserva Secrets Manager/SSM por defecto; eliminar credenciales requiere una confirmación separada.
- [`cloudformation/lifecycle.sh`](cloudformation/lifecycle.sh): entrada guiada `up`/`down`; comprueba la cuenta AWS esperada y pide confirmación escrita. Su aviso declara que opera solo AWS en la región indicada; no despliega VPN, recuperación regional ni Azure, y tampoco finaliza AWS Academy.
- [`cloudformation/voice-recordings.yaml`](cloudformation/voice-recordings.yaml): recursos separados para grabaciones consentidas.
- `aws-azure-vpn.yaml`: diseño de Site-to-Site administrada. AWS Academy denegó `ec2:CreateCustomerGateway`; la plantilla no demuestra un túnel desplegado.
- `aws-azure-p2s-router.yaml`: router EC2 para la alternativa P2S. La creación de la instancia no configura por sí sola las credenciales OpenVPN ni demuestra el túnel; el material privado se mantiene fuera de Git.

### Azure y Terraform

Cada directorio de `environments/` es una raíz Terraform independiente. No se deben combinar estados ni ejecutar `apply` desde un directorio sin identificar su propósito.

| Raíz | Propósito |
|---|---|
| `azure-rebuild/` | Reconstrucción del backend WMS y sus servicios de soporte; [`lifecycle.ps1`](environments/azure-rebuild/lifecycle.ps1) guía `up`/`down` y conserva el backend remoto de Terraform. |
| `azure-private-network/` | VNet y subredes para OpenVPN P2S y Flex; el Key Vault VPN y su permiso acotado están planificados, pendientes de autorización tras el rechazo de revisión automática. Estado remoto independiente; no crea gateways. |
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

Los lanzadores de ciclo de vida validan la cuenta/suscripción y solicitan una confirmación literal; no sustituyen los permisos ni los respaldos. El lanzador de Azure solo administra la raíz `azure-rebuild`; las raíces de VPN/Flex y el backend de state se operan aparte. El lanzador AWS administra el stack principal y el stack de grabaciones, no recursos externos que no pertenezcan a esos stacks.

Un `.tfstate` no reemplaza el código ni un backup. El estado Terraform activo está en almacenamiento remoto; los estados, planes y secretos no se suben a GitHub.

## Reglas antes de cualquier cambio

- Comprueba identidad y suscripción con los mecanismos oficiales; una sesión STS válida no garantiza permiso para inventariar o desplegar.
- Lee el change set/plan completo. No ejecutes `apply`, `deploy` o `destroy` con nombre de stack supuesto.
- Conserva datos y secretos; comprueba `DeletionPolicy`, `UpdateReplacePolicy` y la retención real antes de cambios destructivos.
- WAF, RDS Multi-AZ, gateways VPN, EC2 y almacenamiento generan consumo. En AWS Academy pueden existir denegaciones SCP/IAM explícitas; no las eludas.
- No guardes credenciales de AWS/Azure, llaves VPN, PFX, state ni planes en Git o en argumentos de consola.

Guía operativa AWS: [`cloudformation/README.md`](cloudformation/README.md). Los scripts de costo y conectividad están en `scripts/`.

## Revalidación de puntos únicos de fallo — 2026-11-04

En la revisión histórica del 04/11 el inventario mostró WAF, RDS PostgreSQL Multi-AZ con 7 días de retención y ASG hasta 5; la captura inicial del ASG en cero fue seguida por una recuperación a dos instancias. La prueba posterior `/health` no escaló. En ese momento había un único NAT y no se observaba un túnel activo; el piloto Tailscale se probó posteriormente, como indica el corte del 05/11. RDS es `db.t3.micro`; `rebuild.sh` pasa 7 días por defecto, alineado con `aws-lab.yaml`; puede reducirse explícitamente con `DATABASE_BACKUP_RETENTION_DAYS`, pero eso cambia el margen de recuperación.

`us-west-2` no tiene una pila del proyecto: se observó únicamente la VPC predeterminada. La recuperación regional queda como backup-and-restore/pilot light no desplegado ni probado. La alternativa OpenVPN propia no está activa: el template router histórico no configura ni inicia un túnel y no aporta failover. No presentar una respuesta HTTPS pública como prueba de la ruta privada. Los lanzadores actuales operan raíces independientes y no reconstruyen VPN ni región secundaria; no existe todavía un ciclo integral verificado de “levantar todo / borrar todo”.

En una primera comprobación local, AWS CLI no encontró credenciales y Azure CLI no pudo leer su perfil por permisos. Una reconsulta posterior autenticó en AWS con el token temporal y en Azure con acceso autorizado; sus resultados están en el registro de puntos únicos de fallo. No se modificó la nube. El comando `down` no termina por sí solo el laboratorio AWS Academy.

Para el cierre de esta sesión se autorizó perder los datos del portal y conservar los secretos de Secrets Manager/SSM y la pila Academy. El `destroy.sh` ahora exige la cuenta esperada y ejecuta detección de deriva cuando CloudFormation aún muestra `NOT_CHECKED`; si la deriva no termina en `IN_SYNC` o el inventario no coincide, se detiene antes de vaciar datos. El contador Academy consultado el 04/11 era US$19.90/US$50; es acumulado, no un cargo horario ni un valor que baje al borrar.
