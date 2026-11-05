# Túnel overlay AWS–Azure con Tailscale (propuesta controlada)

## Prueba desde el ERP — 05/11/2026

### Conmutación automática AWS verificada

Cada router AWS ejecuta un monitor systemd cada 30 s con el perfil existente `LabRole`. El router de espera puede tomar la ruta tras tres fallos confirmados del activo si su propia conexión al WMS está sana. El principal recupera la ruta tras diez comprobaciones saludables. Una observación inconclusa de SSM no se trata como fallo confirmado y no se cambian rutas desconocidas.

En una caída controlada de Tailscale en el router principal, el controlador registró tres fallos y `switched_to_backup=true`. El ERP perdió la consulta de salud privada a las 08:41:59 UTC y volvió a obtener 200 a las 08:43:14 UTC: unos 75 segundos entre las muestras observadas. Se recuperó el principal y se restableció manualmente la ruta. Evidencia: `evidence/current/aws/AWS-TAILSCALE-AUTO-FAILOVER-2026-11-05.json`.

El 05/11 se probaron además el retorno automático y la caída del respaldo mientras llevaba tráfico: el principal retomó la ruta y las dos instancias ERP consultaron el WMS privado con HTTP 200. Evidencia: `evidence/current/aws/AWS-TAILSCALE-BIDIRECTIONAL-2026-11-05.json`. Se detuvo el proceso Tailscale, no una zona o instancia completa. Esto no elimina dependencias del servicio Tailscale, Azure, la tabla de rutas ni todos los puntos únicos de fallo; AWS no ofrece comparación atómica al reemplazar esta ruta. `LabRole` tiene permisos amplios y no demuestra mínimo privilegio.

Para reinstalar únicamente el monitor en un router AWS de respaldo ya enrolado, con AWS CLI, Tailscale, ruta principal, forwarding y NAT previamente verificados, copiar `iac/scripts/tailscale_failover.py` e `iac/scripts/install_tailscale_failover.sh` a un mismo directorio del router y ejecutar como root:

```bash
EXPECTED_AWS_ACCOUNT_ID=<cuenta> AWS_REGION=<region> ROUTE_TABLE_ID=<tabla> \
WMS_PRIVATE_IP=<ip-privada> WMS_HOSTNAME=<nombre-flex.azurewebsites.net> \
PRIMARY_INSTANCE_ID=<instancia-principal> PRIMARY_ENI=<eni-principal> \
BACKUP_ENI=<eni-de-este-router> bash install_tailscale_failover.sh --apply
```

En el principal se usa `PREFER_SELF=true` y se intercambian los identificadores: `PRIMARY_INSTANCE_ID` y `PRIMARY_ENI` identifican al otro router, mientras `BACKUP_ENI` es la interfaz local. El instalador verifica cuenta, propiedad de interfaz, ruta y salud de ambos routers; se reinstaló en ambos con `ready=true`. Con `INSTALL_SCOPED_NAT=true` y `WMS_SOURCE_CIDR=10.10.10.0/23`, verifica además las etiquetas de la instancia e instala el servicio NAT limitado y la configuración persistente de reenvío, sin sobrescribir archivos distintos. Se ejecutó en ambos routers existentes con SSM `70fd4653-eb15-4368-989e-8c411ed18f9a` y `fc1992e2-68b4-4ba5-9212-89269f8a5c6b` y resultado `ready=true`. No crea routers, credenciales, rutas ni grupos de seguridad.

La política Tailscale incluye las etiquetas `tag:tangama-aws-router` y `tag:tangama-azure-router`, autoaprobación de `10.20.1.0/24` para la etiqueta Azure y HTTPS hacia `10.20.1.4/32` desde la etiqueta AWS. Se conservaron las cinco reglas anteriores y SSH. Ambas EC2 del ERP resolvieron la dirección privada y recibieron HTTP 200 tras guardar la política (SSM `182610c2-8550-4aba-bd8d-cea077e40c47`). La política no cambia de identidad los routers anteriores y la autoaprobación no aprueba retroactivamente rutas pendientes. `iac/scripts/enrol_tailscale_router.py` permite registrar un router nuevo con una clave temporal ya entregada en un archivo privado de `/run`; no genera ni entrega la clave. No se han creado credenciales OAuth ni integrado su ciclo a ambos proveedores. **No existe todavía una reconstrucción completa con un solo comando**.

El borrado general de AWS ahora se detiene si encuentra los stacks Tailscale o cualquier zona privada asociada a la VPC, o si no puede consultar esas dependencias. No elimina esas dependencias automáticamente y no se ha probado un ciclo real de destrucción y reconstrucción.

La clave de Flex y la almacenada en AWS coincidieron después de la actualización realizada por el usuario. Desde ambas instancias de aplicación se efectuó una consulta autenticada al estado de un evento por la VPN: HTTP 200 y estado `pending` (SSM `f7349e4f-1e2c-4d2c-89e0-35544300de82`); esa consulta no crea un pedido. Una instancia nueva con destino Flex consultó el inventario a través del ERP: HTTP 200, ledger sintético y 14 productos (SSM `114c8aab-ef0c-40ca-abdb-c1f13ebca21e`).

Desde esa misma instancia nueva, mediante el ERP autenticado y el WMS privado, se creó el SKU sintético `SKU-QAVPN-1105-8CA8C1`, una venta y una compra de reposición: venta `completed_demo` con evento `evt-219d9a2c00ad47fc97d113c0a1441d0d`, compra `received_demo` con evento `evt-41eb76249e7240f6a0516155b5825fd8`, y stock final 3 igual al inicial. La evidencia está en `evidence/current/aws/AWS-AZURE-PRIVATE-ERP-SALE-2026-11-05.json`. Esta prueba se dirigió directamente a la nueva instancia mientras la actualización gradual de CloudFormation estaba en curso; no demuestra conmutación automática del router AWS.

CloudFormation terminó con `UPDATE_COMPLETE`, configuró Flex como destino y las dos instancias finales del ERP consultaron su inventario con HTTP 200 y 15 productos (SSM `e65c178c-017d-4ec0-b544-3dbfb87c0e49`). La conectividad se verificó sin forzar el DNS. El balanceador marcó sanas ambas instancias finales.

Se habilitó `net.ipv4.ip_forward=1` de forma persistente en ambos routers AWS. La tabla compartida de aplicación `rtb-0efe0ce4702b92b70` tiene una ruta para el endpoint privado `10.20.1.4/32` hacia el router principal. `lifecycle.sh vpn-route` invoca `iac/scripts/ensure_private_wms_route.py` para verificar cuenta, VPC, tabla del stack, router e interfaz; crea la ruta solamente si falta y no reemplaza un destino diferente. Se ejecutó en la infraestructura existente y devolvió `unchanged`, sin modificar la ruta. Es preciso indicar `ROUTE_TABLE_ID`, `ROUTER_ENI` y `WMS_PRIVATE_IP`. La validación de la ruta no sustituye la prueba de conectividad ni automatiza la creación de los routers.

Se añadieron reglas NAT acotadas a TCP 443 desde `10.10.10.0/23` hacia ese endpoint en ambos routers. El servicio systemd `tangamandapio-wms-nat.service` quedó habilitado en ambos y reinstala la regla; se verificó su reinicio y la conectividad posterior, pero no se reinició cada EC2 para probar arranque completo. `iac/scripts/tailscale_nat.py` reproduce el servicio acotado y rechaza redes ajenas o más amplias; el instalador del monitor puede utilizarlo como se indica arriba.

Las dos EC2 del ERP consultaron `/api/health` de la Function privada usando TLS y resolución explícita a `10.20.1.4`; ambas recibieron HTTP 200. También se cambió manualmente la ruta al router AWS de respaldo y ambas recibieron 200; después se restituyó la ruta al principal. Esto demuestra conectividad de aplicación a Function privada y conmutación **manual**, no conmutación automática ni el envío de un pedido autenticado.

Se creó manualmente la zona privada Route 53 `tangama-flex-261104.azurewebsites.net` (`Z0681242DQ7R4ZFD2BX5`) asociada a la VPC del proyecto, con A `10.20.1.4` y TTL 60. Tras propagarse, ambas EC2 resolvieron esa dirección y obtuvieron HTTP 200 con TLS sin forzar DNS (SSM `410064fa-0379-4e32-8b7a-93526275d959`). Esta zona afecta únicamente ese nombre dentro de la VPC y genera cargos; no modifica DNS público. La plantilla `iac/cloudformation/aws-private-wms-dns.yaml` y el auxiliar `iac/cloudformation/rebuild-private-wms-dns.sh` permiten crear una zona nueva. Su modo `--ensure` verifica la zona y el registro exactos sin duplicarlos ni adoptar la zona existente. `lifecycle.sh up` puede incorporar esta etapa con `ENABLE_PRIVATE_WMS_DNS=true`; `lifecycle.sh dns` permite reanudarla. Tras reiniciar el laboratorio y renovar las credenciales, `lifecycle.sh dns` verificó correctamente la zona existente sin cambiarla; las dos EC2 renovadas resolvieron 10.20.1.4 y respondieron HTTP 200 a la salud privada (SSM `5f02c0c4-7adc-4a59-9d5c-73f0bd13d1c7`). La zona actual no está administrada por CloudFormation; el ciclo principal aún no automatiza ruta, NAT ni enrolamiento.

Para crear una zona nueva durante una reconstrucción, después de desplegar la VPC y el Private Endpoint y verificar su IP:

```bash
EXPECTED_AWS_ACCOUNT_ID=<cuenta> AWS_REGION=<region> VPC_ID=<vpc> \
WMS_HOSTNAME=<nombre-flex.azurewebsites.net> WMS_PRIVATE_IP=<ip-privada> \
bash iac/cloudformation/rebuild-private-wms-dns.sh --apply
```

En Git Bash de Windows puede definirse `TANGAMA_PYTHON` con la ruta de Python y `AWS_CLI` con la del ejecutable AWS. Con `--ensure`, el auxiliar reutiliza una zona existente solo si el registro coincide exactamente; si no existe, intenta crear la plantilla. No adopta la zona activa. **No usar todavía el borrado general como limpieza completa:** no incluye las dos pilas Tailscale actuales ni la zona privada creada manualmente. Revisar esos recursos y el estado compartido antes de eliminar la VPC o Azure.

## Prueba de respaldo — 05/11/2026

Hay dos routers piloto AWS en zonas `us-east-1a` y `us-east-1b` y dos routers Azure en West US. Ambos routers AWS consultaron por HTTPS el endpoint privado de salud de Flex y recibieron HTTP 200. Los routers Azure anuncian la misma ruta privada `10.20.1.0/24`, aprobada en Tailscale.

Se detuvo temporalmente Tailscale en el router Azure principal, con recuperación programada: el respaldo pasó a ser el router primario de esa ruta y la consulta privada volvió a responder 200. En la serie observada hubo seis consultas fallidas entre 05:50:55 y 05:51:07 UTC; la primera respuesta correcta posterior fue a las 05:51:10 UTC. Es una prueba de conmutación del lado Azure, no de continuidad sin interrupciones ni de recuperación regional.

En la prueba de respaldo inicial el ERP aún no usaba esta ruta para pedidos. La conmutación automática del lado AWS para el tráfico de las instancias de aplicación no se ha implementado ni probado. Las reglas TCP 443 y la clave en AWS fueron actualizadas posteriormente por el usuario; una revisión automática había rechazado previamente mis intentos de añadirlas o transferir la clave.

La Function Flex había heredado una cadena `AzureWebJobsStorage` obsoleta que tenía prioridad sobre su identidad administrada y causaba errores de autenticación del almacenamiento. Se retiró esa configuración en la Function privada; la consulta de su clave de host volvió a funcionar. Esto no demuestra por sí solo el procesamiento de un pedido.

El respaldo AWS utiliza la misma plantilla de CloudFormation `aws-tailscale-pilot.yaml`, en una segunda pila. Azure tiene una raíz Terraform separada en `iac/environments/azure-tailscale-backup`, que reutiliza el módulo del piloto con nombres distintos. Las altas de dispositivos, reglas y aprobación de rutas todavía son manuales y deben repetirse al reconstruir; los comandos generales de levantamiento y borrado no comprenden este piloto automáticamente. Las máquinas y sus recursos de red pueden generar cargos mientras existan.

## Avance observado — 04/11/2026

La EC2 `tangamandapio-tailscale-pilot` y la VM Azure `vm-tangama-ts-pilot` se registraron en el tailnet y respondieron entre sí por DERP. Desde la EC2 se comprobó el endpoint privado `10.20.1.4` de `tangama-flex-261104`: `/api/health` devolvió 200 con TLS válido, el endpoint público devolvió 403 y un evento sin clave devolvió 401. El registro está en `evidence/current/aws/AWS-AZURE-TAILSCALE-2026-11-04.json`.

El ERP no cambió de destino, no se probó un evento autenticado por el túnel ni se demostró conmutación. La política del tailnet usa IP de los nodos piloto, que pueden cambiar al recrearlos; su enrolamiento y aprobación de rutas siguen siendo manuales. La Function Flex fue desplegada inicialmente con publicación pública temporal y después se cerró el acceso público. El comando de publicación terminó con error al consultar la clave del host, pese a que los endpoints de salud y autorización respondieron; investigar antes de afirmar que procesa eventos. Una revisión automática previa rechazó abrir TCP 443 desde las subredes de aplicación al router; no se activó dicha ruta.

El piloto AWS está definido por `iac/cloudformation/aws-tailscale-pilot.yaml`; el de Azure por `iac/environments/azure-tailscale-pilot`. Los comandos generales de ciclo de vida todavía **no** automatizan el enrolamiento, la política, las rutas, este piloto ni el WMS Flex privado. Las dos VMs, la IP pública de Azure y el Private Endpoint generan o pueden generar costos mientras existan. No borrar las redes compartidas ni los otros dispositivos del tailnet al limpiar el piloto.

## Estado comprobado — 13/10/2026, 14:53 America/Chicago

- AWS STS autentica el perfil local `default`; existe una VPC disponible con
  `10.10.0.0/16`.
- Azure CLI tiene una suscripción seleccionada, pero `az network vnet list`
  devuelve cero VNets. El grupo de red y los routers Azure todavía no existen.
- El servicio Tailscale de Windows está instalado y activo; el cliente reportó
  `BackendState=NoState` y el nodo local no estaba online durante la última
  comprobación. No se enroló ningún nodo cloud durante esta tarea; al estar
  offline, el cliente no permite afirmar el inventario actual del tailnet.
- Por tanto, **no hay túnel ni ruta privada AWS–Azure en este corte**. La
  Function WMS permanece pública; no se presenta como tráfico por Tailscale.

Ejecutar el preflight de solo lectura desde la raíz del proyecto:

```powershell
python .\iac\scripts\check_tailscale_prerequisites.py
```

El informe no imprime identidad de cuenta, clave ni errores crudos de los CLIs.
Exige sesión AWS/Azure, VPC y VNet esperadas, CIDR sin solapamiento, cliente
Tailscale online y `TAILSCALE_AUTH_KEY` presente como variable. Nunca muestra
el valor de la clave. Devuelve código 2 mientras falte cualquier requisito.

## Topología propuesta

1. Mantener la VPC de la aplicación AWS (`10.10.0.0/16`) y crear una EC2
   Linux dedicada a subnet-router, fuera del ASG de aplicación, con source/
   destination check desactivado. Preferir subnet pública para conexión directa
   si la política y el saldo lo permiten; Tailscale también puede usar DERP si
   la conexión directa no está disponible.
2. Crear una VNet Azure separada (`10.20.0.0/16`) y una VM Linux dedicada a
   subnet-router. La VNet también albergaría la subnet de la futura Function
   Flex y su Private Endpoint; no cambiar el WMS `Y1` durante el piloto.
3. Unir ambos Linux routers al mismo tailnet con dispositivos etiquetados,
   habilitar `net.ipv4.ip_forward=1` y `net.ipv6.conf.all.forwarding=1`, y
   configurar cada router con `--advertise-routes=<CIDR-local>`,
   `--snat-subnet-routes=false` y `--accept-routes`. Anunciar solo los prefijos
   necesarios; no anunciar ni propagar la subnet privada de RDS.
4. Aprobar ambas rutas en la consola tailnet y autorizar el flujo mínimo en la
   política ACL/grants. Añadir rutas de retorno en las tablas cloud:
   VPC → ENI del router AWS para `10.20.0.0/16`; subnets Azure → IP privada
   del router Azure para `10.10.0.0/16`. Restringir las reglas de red al tráfico
   requerido; no abrir SSH ni UDP entrante por defecto.
5. Probar un endpoint TCP/HTTP sintético de ambas direcciones y capturar
   `tailscale status`, rutas aprobadas, ACL efectiva, traceroute/ruta y logs
   del listener. Después probar una llamada desde AWS al Private Endpoint de
   Flex, solo cuando el DNS privado y la migración blue-green estén listos.
6. Destruir las VMs, IP públicas, NICs, NSG/SG, tablas/rutas y VNet temporal;
   confirmar también que no quedan dispositivos o rutas de prueba aprobadas.

La instalación de una máquina en Tailscale **no conecta por sí sola dos
subredes**. Para site-to-site Tailscale requiere routers Linux en ambos lados,
forwarding, anuncios y aprobación de rutas, ACL/grants en ambas direcciones, y
rutas de retorno en las nubes. Su guía prescribe desactivar SNAT para que los
routers puedan encadenar subredes. No usar la laptop como router permanente.
La guía Azure documenta UDP 41641 para facilitar conexiones directas, pero se
omitirá ingress amplio en el piloto; primero se probará con salida y relay, y
cualquier apertura se limitará tras revisar la topología.

## Aprobaciones y seguridad antes del piloto

- La última prueba con VPN administrada fue denegada por una SCP de AWS al
  crear `CustomerGateway`. Eso no demuestra que se permitan EC2, cambios de
  route table o IAM; confirmar cada operación con preflight/read-only y detener
  el plan ante `AccessDenied`.
- Usar una clave de enrolamiento Tailscale temporal, de un solo uso y etiquetada;
  no colocarla en Terraform, user-data persistente, Git, logs ni capturas. El
  valor debe inyectarse desde el entorno seguro de despliegue, y revocarse al
  terminar. La variable `TAILSCALE_AUTH_KEY` solo se inspecciona como booleano.
- Limitar ACL al puerto/protocolo y hosts del piloto. Deshabilitar forwarding
  del resto del tráfico, activar el firewall del host y no exportar la ruta de
  RDS ni `0.0.0.0/0`.
- Revisar cargos de EC2, VM Azure, discos e IPs públicas antes de crear; el
  plano de control SaaS de Tailscale también es una dependencia externa. No
  aplicar hasta tener plan guardado y aprobación del piloto temporal.

## Qué demostraría y qué no

Una prueba de tráfico privado enrutado acreditaría conectividad overlay cifrada
entre las subredes del piloto. No equivale a dos conexiones AWS Site-to-Site
VPN administradas, IPsec/BGP ni a redundancia de gateway. Si la rúbrica exige
explícitamente VPN nativa o BGP, reportar Tailscale como alternativa técnica,
no como sustitución silenciosa. El criterio solo puede reconsiderarse con la
conectividad y alcance que acepte el docente.

Referencias oficiales:

- [Arquitectura de referencia AWS](https://tailscale.com/kb/1296/aws-reference-architecture)
- [Site-to-site con Tailscale](https://tailscale.com/docs/reference/subnet-site-to-site)
- [Configuración actual site-to-site y forwarding](https://tailscale.com/docs/features/site-to-site)
- [VM Linux Azure con Tailscale](https://tailscale.com/docs/install/cloud/azure/linux)
- [Subnet routers y forwarding](https://tailscale.com/kb/1104/enable-ip-forwarding)
- [Aprobación de rutas y control de acceso](https://tailscale.com/docs/reference/route-injection)
