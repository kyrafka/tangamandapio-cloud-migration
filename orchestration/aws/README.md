# Orquestación AWS desde CloudShell

Subir el repositorio o, como mínimo, la carpeta `iac/cloudformation/` y `orchestration/aws/` a CloudShell. No pegar ni guardar credenciales: CloudShell usa la sesión temporal de AWS Academy.

```bash
chmod +x orchestration/aws/*.sh
./orchestration/aws/preflight.sh
./orchestration/aws/create_change_set.sh
```

Revisar el change set. Solo tras autorización explícita:

```bash
export STACK_NAME=tangamandapio-live-20260930
export CHANGE_SET_NAME='NOMBRE_DEL_CHANGE_SET_APROBADO'
export CONFIRM_EXECUTE_AWS=YES
./orchestration/aws/execute_change_set.sh
```

Después de `CREATE_COMPLETE`:

```bash
./orchestration/aws/verify_platform.sh
```

Las pruebas de escritura, alarmas y recuperación se ejecutan por separado y conservan sus propias guardas de costo en `tests/aws/`.

