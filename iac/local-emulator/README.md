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

## Alcance

El emulador sirve para verificar integración básica con APIs compatibles y lógica local. No acredita el comportamiento real de EC2/Auto Scaling, RDS Multi-AZ y failover, WAF, VPN/Tailscale, permisos SCP/IAM de la cuenta, DNS/ACM ni latencia/capacidad de producción. La plantilla CloudFormation completa no se considera validada por esta comprobación. Esos puntos requieren validación en AWS real.

Moto mantiene el estado en memoria; al detenerlo o reiniciarlo, los recursos de prueba desaparecen. El entorno virtual `.venv` es local y está excluido de Git.
