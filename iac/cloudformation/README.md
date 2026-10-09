# AWS CloudFormation — stack actual del laboratorio

El stack vigente comprobado es `tangamandapio-live-20261005` en `us-east-1`. La plantilla local `aws-lab.yaml` coincide exactamente con la plantilla almacenada en CloudFormation y `validate-template` pasó el 08/10/2026. La consola reporta `UPDATE_COMPLETE`, drift `IN_SYNC`, 51 recursos, dos destinos saludables y RDS disponible, privado, cifrado, Multi-AZ y con siete días de backup.

CloudFormation es la única herramienta que administra este stack AWS. `iac/environments/demo` es una red Terraform separada, sin state y no debe aplicarse sobre el entorno vivo.

## Preparar un despliegue

La secuencia de `deploy.sh` valida la plantilla, exige que el stack existente esté estable y sin drift, y genera un change set `UPDATE`. Mantiene todos los parámetros actuales con `UsePreviousValue=true`, incluidos los secretos `NoEcho`; no restablece Multi-AZ, WAF, Backup ni certificados a los valores por defecto del template. No ejecuta el change set a menos que se solicite explícitamente.

```bash
cd iac/cloudformation
STACK_NAME=tangamandapio-live-20261005 AWS_REGION=us-east-1 ./deploy.sh
```

Revisar cuidadosamente la tabla de cambios. Para ejecutar, repetir con `APPLY_CHANGE_SET=true`, `CONFIRM_STACK_NAME=tangamandapio-live-20261005` y escribir `APPLY` cuando lo solicite. No pasar contraseñas por argumentos ni reemplazar parámetros secretos; el script conserva sus valores previos.

Solo para publicar un artefacto nuevo, establecer juntos `APPLICATION_ARTIFACT_KEY` y `APPLICATION_ARTIFACT_REVISION` después de correr pruebas y subir el objeto versionado al bucket. El script no empaqueta ni sube código por sí mismo.

## Lo que esta plantilla no demuestra

- El endpoint `/health` contestó 200 y `database=ok`; la prueba usó `curl -k`, por lo que no demuestra cadena TLS confiable.
- No se verificó un dominio propio ni certificados confiables del navegador.
- La aplicación Azure sigue usando inventario simulado; no es un WMS conectado a stock empresarial.
- No se ejecutaron cambios de infraestructura en este corte.

`destroy.sh` es una operación destructiva y no es parte del despliegue normal. No ejecutarlo para “actualizar” el stack.
