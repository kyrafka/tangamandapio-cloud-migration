# Azure Point-to-Site para acceso privado al WMS

## Propósito y límites

Este root configura un VPN Gateway Azure Route-Based con OpenVPN y clientes de certificado. Para el piloto, una EC2 privada se conecta como cliente y enruta únicamente el tráfico HTTPS dirigido al Private Endpoint del WMS. Esto es una ruta privada limitada, no una VPN AWS Site-to-Site administrada, no configura BGP y no conecta toda la VPC.

El piloto del 29/10 reportó HTTPS `/api/health` 200 desde el router y las dos EC2 de aplicación, con validación TLS. Esta comprobación fue al endpoint de salud; no demuestra una venta/recepción creada por el ERP. El inventario de AWS no se pudo revalidar después de ese corte. Azure muestra el gateway provisionado, pero eso no prueba una sesión activa por sí mismo.

## Topología

```text
EC2 privadas de aplicación
  └─ ruta /32 al router EC2
       └─ OpenVPN P2S (cliente de certificado)
            └─ Azure VPN Gateway
                 └─ VNet → Private Endpoint → Azure Function Flex
```

El router aplica NAT para el camino de retorno y la resolución del hostname del WMS debe apuntar al Private Endpoint dentro de la VPC. Mantén el alcance limitado al endpoint requerido; no enrutes RDS ni toda la VNet por este piloto.

## Riesgos operativos

- El router y el gateway son puntos únicos de falla; reemplazo y reconexión deben probarse antes de depender de ellos.
- El VPN Gateway genera costo horario mientras exista. Apágalo/destrúyelo cuando el laboratorio no lo necesite.
- Los certificados del piloto tienen fecha de expiración y deben rotarse antes de usarlos de nuevo. Las claves raíz, PFX, perfiles OpenVPN y archivos con credenciales permanecen fuera del repositorio.
- La ruta privada requiere revisar DNS, rutas y reglas de red en ambos lados; el estado `Succeeded` del gateway no acredita el trayecto extremo a extremo.

## Reconstrucción segura

Este root usa el estado remoto Terraform del proyecto y referencia una VNet existente. Antes de plan/apply:

1. Confirma suscripción, grupo de recursos, VNet, `GatewaySubnet` y estado Terraform remoto.
2. Genera certificados de laboratorio nuevos y guarda la clave raíz fuera del repo, en almacenamiento protegido.
3. Revisa el plan y el costo estimado del gateway. La variable `deployment_approved` debe permanecer desactivada salvo que exista una ventana de prueba aprobada.
4. Provisiona/descarga el perfil OpenVPN, instala los certificados por un canal seguro en la EC2 y valida DNS, rutas y HTTPS desde cada instancia.
5. Al terminar, verifica la desconexión y elimina los recursos temporales si ya no hacen falta.

Los comandos de `terraform fmt`, `init`, `validate` y `test` son verificaciones locales; no despliegan ni demuestran un túnel vivo. No publiques state, plan, certificados ni credenciales.

## Alternativa Site-to-Site

La arquitectura administrada de AWS–Azure se mantiene en `../aws-azure-vpn`. AWS Academy denegó `ec2:CreateCustomerGateway`; por ello esa opción no está desplegada. No presentes P2S + router EC2 como sustituto equivalente si la rúbrica exige AWS Site-to-Site/BGP.
