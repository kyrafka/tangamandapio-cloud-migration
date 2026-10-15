# Preflight AWS–Azure VPN — 14/10/2026, 02:17 America/Chicago

## Resultado

No se desplegó ni modificó infraestructura. El estado de las comprobaciones
fue:

- AWS STS autenticó correctamente en la cuenta del laboratorio.
- La lectura del stack portal no pudo revalidarse: CloudFormation devolvió
  `AccessDenied`. No se asume que el estado anterior siga vigente.
- Las consultas EC2 `DescribeVpnGateways`, `DescribeCustomerGateways` y
  `DescribeVpnConnections` devolvieron `UnauthorizedOperation`.
- `CreateCustomerGateway --dry-run`, con una IP reservada de documentación,
  fue denegado. Al ser una prueba `--dry-run`, no creó recursos.
- Azure CLI autenticó y mostró la suscripción `Enabled`; el grupo dedicado
  `rg-tangama-private-network` no existe (`false`).

## Conclusión y siguiente paso

La VPN AWS–Azure no está demostrada ni puede desplegarse con seguridad desde
este estado. Falta habilitar permisos IAM/SCP de lectura y creación para los
recursos Customer Gateway/VPN en AWS Academy y reconstruir/aprobar el grupo de
red Azure. El `dry-run` solo comprueba la autorización de la API indicada; no
prueba el rol de ejecución de CloudFormation. Antes de desplegar se debe volver
a confirmar el stack portal y revisar el costo horario de Azure VPN Gateway y
los cargos AWS, y ejecutar la prueba temporal previamente aprobada con limpieza
verificada.

No se intentó `apply`, `deploy`, creación ni limpieza de recursos. Tampoco se
infieren rutas, BGP o tráfico privado. La suscripción Azure está activa, pero
el grupo privado específico no está presente.

## Revalidación con token nuevo — 15/10/2026, 01:36 UTC

AWS STS autenticó en la cuenta `841113066612`; CloudFormation pudo leerse y una
nueva detección del stack del portal terminó `IN_SYNC`. La VPC del portal sigue
en `10.10.0.0/16`. Se volvió a ejecutar `CreateCustomerGateway --dry-run` con
una IP reservada para documentación: AWS lo denegó por un `explicit deny` en
la SCP `p-qa2qn8qf` para `ec2:CreateCustomerGateway`. El dry-run no creó
recursos y el perfil actual no puede desplegar esta VPN mediante el camino
Site-to-Site previsto.

En Azure, la suscripción activa no devuelve ninguna VNet en `az network vnet
list`; la consulta del recurso VPN Gateway requiere la extensión CLI
`virtual-wan`, cuya instalación no se aprobó. No se instalaron extensiones ni
se crearon recursos. La Function pública continúa healthy por HTTPS, pero esto
no sustituye una ruta privada. Para cerrar este criterio se necesita una cuenta
AWS sin el deny de Academy o que el administrador de la organización habilite
la API, además de aprovisionar la VNet/gateway y demostrar túneles/rutas; no se
debe intentar sortear la SCP.
