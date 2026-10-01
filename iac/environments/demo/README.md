# Entorno Terraform demo AWS Azure

Este entorno describe la VPC AWS y el vertical Azure de operaciones. Por seguridad y costo, `enable_azure=false` es el valor predeterminado: un `terraform plan` local no debe crear recursos Azure.

## Antes de aplicar Azure

1. Iniciar sesión con `az login` en la suscripción Azure for Students.
2. Confirmar que `eastus` está disponible o sustituir la región.
3. Elegir un nombre globalmente único para `azure_storage_account_name`.
4. Establecer presupuesto y alerta de costos; capturar la pantalla inicial.
5. Aplicar, probar el evento, tomar capturas y ejecutar `terraform destroy` al terminar.

No guardar credenciales, claves de Storage Account ni archivos `terraform.tfvars` reales en Git.
