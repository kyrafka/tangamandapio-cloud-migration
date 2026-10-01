# CloudFormation — laboratorio AWS

Plantilla ejecutable en AWS Academy sin instalar Terraform. Implementa:

- VPC `10.10.0.0/16` y seis subredes en dos zonas.
- Internet Gateway, NAT Gateway y tablas de rutas separadas.
- ALB público y dos instancias privadas administradas por Auto Scaling.
- RDS PostgreSQL privado con secreto generado en Secrets Manager.
- S3 cifrado, versionado y bloqueado al acceso público.
- Security Groups por capa.
- CloudWatch Logs con retención de un día y logs de acceso/error por instancia.
- CloudWatch Agent con memoria, disco raíz y proceso Gunicorn, además de los logs de aplicación.
- Dashboard de CPU, salud, latencia p95, 5xx, CPU y conexiones RDS.
- Cuatro alarmas: CPU de aplicación, targets no saludables, errores 5xx y CPU de RDS.
- API con readiness, correlación de solicitudes, validación de entrada y headers defensivos.

## Ejecución

La ruta orquestada recomendada está en `../../orchestration/aws/`: valida, genera un change set y exige una confirmación explícita antes de ejecutar recursos facturables.

```bash
chmod +x ../../orchestration/aws/*.sh
../../orchestration/aws/preflight.sh
../../orchestration/aws/create_change_set.sh
```

`deploy.sh` se conserva como alternativa directa solo para una ejecución controlada.

## Limpieza obligatoria

```bash
./destroy.sh
```

La plantilla utiliza `LabInstanceProfile`, provisto habitualmente por AWS Academy. No debe ejecutarse fuera de ese entorno sin revisar el perfil de instancia.

Antes de volver a desplegar, ejecutar localmente `tests/run_local_quality.ps1`. Las pruebas cloud preparadas están explicadas en `tests/README.md` y nunca deben ejecutarse sin revisar costo, región y limpieza.
