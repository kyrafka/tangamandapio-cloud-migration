# Red Azure para OpenVPN P2S y WMS Flex

Esta raíz administra el grupo `rg-tangama-private-network`, la VNet `vnet-tangama-private`, sus cuatro subredes, un Key Vault dedicado a certificados VPN y una asignación `Key Vault Secrets Officer` limitada a ese vault para la identidad que ejecute Terraform. No crea un gateway, túnel, Function ni recurso AWS. La VNet usa `10.20.0.0/16`, separada de la VPC AWS `10.10.0.0/16`; `GatewaySubnet` se reserva para el gateway P2S y Flex tiene subred dedicada y delegada.

El estado remoto usa `azure-private-network.tfstate`. El grupo contiene recursos administrados por otras raíces: **destruye primero Flex y el gateway P2S**, comprueba que no queden recursos y solo entonces planifica la destrucción de esta raíz. AzureRM está configurado para impedir eliminar un grupo que aún contenga recursos. No apliques la raíz `aws-azure-vpn` sobre esta misma red: intenta administrar recursos y un gateway diferentes.

Para revisar el plan con la suscripción autorizada:

```powershell
terraform -chdir=iac/environments/azure-private-network init
terraform -chdir=iac/environments/azure-private-network plan -var="subscription_id=<GUID>"
```

El 04/11/2026 se aplicó la red y, tras autorización explícita, se crearon el Key Vault VPN y su asignación limitada. Se importaron al estado de Terraform y el plan posterior mostró **No changes**. La revisión automática bloqueó el intento posterior de generar y guardar certificados; el almacén estaba vacío al comprobarlo. La red no demuestra una VPN ni un WMS privado: gateway, certificados, Flex, encaminamiento y conmutación siguen requiriendo despliegue y pruebas.
