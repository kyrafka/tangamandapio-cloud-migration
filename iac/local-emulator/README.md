# Emulador local de AWS

Este entorno usa Moto Server para hacer comprobaciones locales de APIs de AWS. El servidor escucha solo en `127.0.0.1:5000`; las credenciales de prueba son ficticias y cada llamada de la comprobación apunta explícitamente a ese endpoint.

## Uso

Desde la raíz del repositorio, en PowerShell:

```powershell
.\iac\local-emulator\start.ps1
.\iac\local-emulator\smoke.ps1
.\iac\local-emulator\stop.ps1
```

`start.ps1` instala Moto en `.venv` si aún no está instalado. `smoke.ps1` crea datos desechables en S3, Secrets Manager y SQS, verifica escritura/lectura y los elimina al terminar. `stop.ps1` detiene únicamente el proceso local de Moto que inició el script.

Para repetir la prueba de infraestructura y guardar su resultado:

```powershell
.\iac\local-emulator\start.ps1
.\iac\local-emulator\.venv\Scripts\python.exe .\iac\local-emulator\validate_infrastructure.py .\iac-emulator-result.json
.\iac\local-emulator\stop.ps1
```

El programa toma de `aws-lab.yaml` los recursos de la red base y S3. Usa el
módulo Terraform `iac/modules/aws_network` en un directorio temporal, sin el
estado ni el proveedor de producción. Comprueba seis subredes en dos zonas,
rutas y eliminación. Prueba además el objetivo de 3, 4 y 5 instancias y la
acción programada que registra la vuelta a 2. Moto no ejecuta esa acción por
reloj.

El reporte registra los atributos que devolvió Moto y cualquier limitación
de borrado. En esta versión, CloudFormation puede devolver `DependencyViolation`
al retirar la VPC del subconjunto. Las VPC de Terraform sí se eliminan por
su flujo normal. Al detener el emulador se descarta todo el estado residual
de la sesión, incluida la pila de CloudFormation.

## Alcance

El emulador sirve para verificar integración básica con APIs compatibles y lógica local. No acredita el comportamiento real de EC2/Auto Scaling, RDS Multi-AZ y failover, WAF, VPN/Tailscale, permisos SCP/IAM de la cuenta, DNS/ACM ni latencia/capacidad de producción. La plantilla CloudFormation completa no se considera validada por esta comprobación. Esos puntos requieren validación en AWS real.

Moto mantiene el estado en memoria; al detenerlo o reiniciarlo, los recursos de prueba desaparecen. El entorno virtual `.venv` es local y está excluido de Git.
