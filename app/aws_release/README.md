# Paquete de la versión ejecutada en AWS

> La fuente para el inventario vigente es el [mapa actual](../../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md).
> Este README conserva notas del paquete y cortes de publicación; su presencia
> no demuestra por sí sola que una ruta o pantalla siga activa.

`current/` conserva el paquete desplegado en AWS el 8 de octubre de 2026, con
la revisión `20261008-azure-fulfillment-status`. El bundle estático se recuperó
de la publicación anterior `74ddfb2-admin-company-sort-fix-20261007`; se
mantiene separado de `src/` y `web/` porque esas carpetas locales son una
implementación anterior y no contienen el código ni los recursos estáticos
completos que sirven las instancias actuales.

El artefacto incluye Flask, sus migraciones SQLite/PostgreSQL y el frontend
compilado. Los cambios de backend de este directorio se empaquetan para AWS;
no se debe construir el despliegue desde `app/src` hasta reconstruir y validar
el frontend original de producción.

Las grabaciones usan un bucket privado independiente definido en
`iac/cloudformation/voice-recordings.yaml`. La aplicación deriva su nombre del
ARN de Secrets Manager ya inyectado en las instancias, salvo que se configure
`VOICE_RECORDINGS_BUCKET` explícitamente. En SQLite se conserva almacenamiento
local únicamente para desarrollo; PostgreSQL no habilita grabaciones sin S3.

Para validar el paquete desde este directorio:

```powershell
python -m py_compile app.py
python -m unittest discover -s tests -v
```

## Backend desplegado y validación Azure (8 de octubre de 2026)

El paquete local ahora incorpora la migración `0006_user_security_lifecycle`
y estos endpoints protegidos:

- `PATCH /api/admin/users/<id>` cambia rol, empresa y estado activo; cada cambio
  incrementa `auth_version` e invalida las sesiones anteriores.
- `POST /api/admin/users/<id>/reset-password` emite una contraseña temporal,
  la revela una sola vez y obliga al usuario a cambiarla.
- `POST /api/auth/password` valida la contraseña actual y exige una nueva de al
  menos 12 caracteres; después revoca la sesión.
- `GET /api/voice/ice-config` entrega STUN y, solo si están configurados
  `WEBRTC_TURN_URLS` y `WEBRTC_TURN_SHARED_SECRET`, credenciales TURN efímeras.
  La clave compartida nunca se devuelve al navegador.
- `GET /api/outbox/<event_id>/fulfillment-status` consulta el resultado final
  de un evento local en Azure y marca expresamente los estados simulados. El
  despacho reconoce el acuse `queued_duplicate`, que Azure usa al recibir un
  evento repetido de forma idempotente.

Estos cambios quedaron registrados como desplegados gradualmente en ambas instancias AWS como revisión
`20261008-azure-fulfillment-status`. El paquete se conserva en S3 como
`releases/tangamandapio/portal-20261008-azure-fulfillment-status-29d65428.tar.gz`;
la versión anterior permanece en el directorio de backup de cada EC2. La
migración invalida las sesiones
anteriores; los usuarios deben volver a iniciar sesión. El frontend actual no
consume todavía `ice-config` y no existe un servidor TURN configurado. La
interfaz desplegada tampoco tiene controles para editar o resetear usuarios:
esos flujos están en la API y requieren integrarse en la fuente React
recuperada/reconstruida antes de que el usuario final los use.

El ALB y ambas EC2 quedaron saludables tras el despliegue. La nueva consulta
protegida de estado WMS respondió `401` sin sesión (esperado). El 8 de octubre,
la clave ordinaria `default` de Azure se guardó en AWS Parameter Store como
`SecureString` (`/tangamandapio/azure/function-key`, versión 1). Se validó la
coincidencia con la configuración de ambas EC2 sin imprimir el valor, se hizo
el reinicio gradual y ambas instancias regresaron a `healthy`; las dos
consultaron el evento sintético en Azure y recibieron HTTP 200 con
`simulated_completed`. El Worker WMS continúa en modo demostración y no mueve
inventario.

La fuente React/CSS correspondiente al bundle actual no está incluida en este
checkout ni en el paquete de release consultado en S3: este solo contiene
`static/assets` compilados, sin `src/`, `web/` ni source map. El historial local
solo conserva una interfaz anterior. No compilar `app/web` sobre `current/static`
hasta reconstruir y validar las vistas actuales de telefonía, administración y
estilos.

## Recursos locales no redistribuidos

El paquete local puede contener música e imágenes suministradas para la interfaz.
Se excluyen del repositorio público hasta confirmar derechos de redistribución;
la aplicación conserva sus fondos de reserva si no están presentes. No subir
tokens temporales de AWS Academy ni archivos de credenciales.

## Centro de plataforma local

La página independiente `/platform` agrega una vista de operación y seguridad
para Administración y Operaciones TI, con telemetría CloudWatch opcional y
controles de edición/restablecimiento para usuarios. Las métricas no se
simulan: se muestran como no configuradas si faltan permisos o identificadores.
La guía y la política de solo lectura están en
[PLATFORM_CONSOLE.md](PLATFORM_CONSOLE.md); consulta el mapa actual antes de
afirmar el estado de publicación y prueba del panel.
