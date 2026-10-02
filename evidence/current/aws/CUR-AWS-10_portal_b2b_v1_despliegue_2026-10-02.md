# CUR-AWS-10 — Publicación versionada del portal B2B

**Fecha del ciclo:** 02/10/2026

**Región:** `us-east-1`

**Stack del ciclo:** `tangamandapio-live-20261001`

**Resultado del ciclo:** `UPDATE_COMPLETE`
**Hora de finalización:** 11:56 a. m. (America/Chicago) / 16:56:34 UTC

## Alcance comprobado

Se publicó el portal B2B de Tangamandapio como artefacto privado y versionado en S3. El Auto Scaling Group descargó el artefacto al iniciar cada instancia y accedió a los secretos requeridos mediante el rol del laboratorio, sin guardarlos en Git ni mostrarlos en la evidencia. La actualización sustituyó nodos de forma gradual detrás del ALB.

## Trazabilidad técnica

| Paso | Resultado verificado |
|---|---|
| Artefacto | `releases/portal-b2b-v1.tar.gz` cargado en el bucket privado del stack; 83 475 bytes, versión de código `802820f`. |
| Validación | `aws cloudformation validate-template` aprobó `iac/cloudformation/aws-lab.yaml`. |
| Permisos del rol | La simulación para el rol del laboratorio devolvió `allowed` para obtener el objeto S3 y el secreto requerido. |
| Primer change set | `PortalSessionSecret` falló porque `GenerateStringKey` no tenía `SecretStringTemplate`; CloudFormation inició rollback automáticamente. |
| Corrección | Se añadió `SecretStringTemplate: '{}'` al secreto de sesión; corrección versionada como `45274dc`. |
| Segundo change set | Siete cambios controlados: secretos, Launch Template, ASG, política de escalado, alarma y dashboard. |
| Resultado | CloudFormation informó `UPDATE_COMPLETE` el 02/10/2026 a las 16:56:34 UTC. |

## Disponibilidad durante el recambio

Mientras el Auto Scaling Group reemplazaba instancias en lotes de una, se ejecutó una consulta pública no destructiva:

```text
GET /health -> HTTP/1.1 200 OK
{"database":"ok", "status":"ok"}
```

Esto confirma continuidad del ALB y disponibilidad de PostgreSQL durante esa actualización. No sustituye la prueba específica de login, roles ni rutas protegidas de la interfaz final.

## Estado posterior del laboratorio

Después de reiniciar el laboratorio AWS Academy el 02/10, la consola de CloudFormation mostró **Pilas (0)** al filtrar Tangamandapio, y el DNS del ALB de este ciclo ya no resolvió. En consecuencia, este archivo registra una ejecución temporal finalizada; no afirma que exista un stack activo actualmente.

Para un nuevo ciclo se requiere actualizar la credencial temporal, reprovisionar la pila y repetir las capturas de infraestructura, targets saludables, login/roles y operaciones del portal.

## Seguridad de la evidencia

- No se incluyen secretos, tokens, nombres de cuenta ni datos personales.
- El rollback inicial no sustituyó VPC, ALB ni RDS; limpió únicamente los secretos nuevos que no llegaron a crearse correctamente.
- No se declara cierre de costos como una acción manual de borrado: la ausencia actual deriva del reinicio del laboratorio y se verificó en la consola de CloudFormation.
