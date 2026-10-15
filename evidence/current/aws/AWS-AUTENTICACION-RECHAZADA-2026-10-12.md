# Intento de autenticación AWS — 12/10/2026

**Resultado:** no autenticado. El perfil `default` de AWS CLI se actualizó con
las credenciales temporales suministradas en la conversación. `aws sts
get-caller-identity` respondió `InvalidClientTokenId` (`The security token
included in the request is invalid`). El perfil local no mostró variables de
entorno AWS que lo sobrescribieran.

Solo se intentó STS y se consultó la configuración local con valores sensibles
enmascarados. No se pudo leer el inventario AWS, CloudFormation, EC2, ALB o RDS.
No se ejecutó ninguna operación de escritura en AWS.

Las credenciales no se reproducen en este archivo. Al haber sido pegadas en el
chat, deben considerarse expuestas: reiniciar/renovar la sesión de Learner Lab
y emitir credenciales temporales nuevas antes de volver a autenticar. Hasta
entonces, el perfil `default` local puede seguir fallando y el estado AWS queda
**sin verificar**; los registros de octubre 8–9 son históricos, no evidencia del
inventario actual.

Se repitió STS tras volver a comprobar el perfil local: exit code 254,
autenticación rechazada. No se intentó ninguna operación de inventario ni
escritura cloud después de ese resultado. La red BGP AWS–Azure y el test de
restore RDS quedaron preparados y validados localmente; ninguno se desplegó.
En la revalidación posterior, la puerta local aprobó las 68 pruebas y añadió
guardas explícitas contra despliegue sin aprobación de costo y desmontaje sin
confirmación. También detectó y corrigió el empaquetado de la sonda SQL; su
round-trip local gzip/Base64 pasa. No se ejecutó el restore en RDS.

## Reintento con el token repetido por el usuario — 12/10/2026

Se volvió a escribir en el perfil local `default` la terna que el usuario
repitió y se comparó en memoria, sin imprimir sus valores. `aws sts
get-caller-identity --profile default` volvió a responder
`InvalidClientTokenId`. No había variables de entorno AWS sustituyendo el
perfil. Por tanto, el perfil contiene el valor solicitado, pero AWS no lo
acepta; una copia local no renueva un token temporal rechazado. No se hizo
inventario, despliegue ni otra escritura en AWS. No se vuelve a copiar la
credencial en documentación.
