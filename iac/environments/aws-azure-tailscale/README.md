# Túnel overlay AWS–Azure con Tailscale (propuesta controlada)

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
