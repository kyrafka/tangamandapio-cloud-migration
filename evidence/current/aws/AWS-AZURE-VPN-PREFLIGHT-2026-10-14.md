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
