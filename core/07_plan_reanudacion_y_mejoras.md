# Plan de cierre cloud — corte vivo 29/10/2026

El portal público ya responde 200 y Azure procesó una recepción sintética con cola, worker, idempotencia y trazas. El usuario confirmó que la cuenta AWS Academy se cambió intencionalmente, así que el inventario histórico pertenece a la cuenta anterior. En el reintento del 29/10 a las 21:27 UTC, STS autenticó en la cuenta nueva, pero el laboratorio denegó `List`/`Describe`; no hay reconciliación segura de recursos, RDS, Auto Scaling ni VPN en ella. Se conserva este orden para la siguiente sesión.

## Cerrado en este corte

1. `/` y `/health` públicos: HTTPS 200. `/api/auth/session`: 200 no autenticado; `/api/dashboard`: 401 esperado. No se probó login ni base de datos.
2. Azure Functions Y1/Flex aparecen desplegadas. Y1 `/api/health` 200; Flex privado 403 desde Internet; Private Endpoint `Approved`.
3. Evento QA `qa-recv-20261029211311-97957bdb` aceptado por Azure Queue, procesado como `demo_restock_completed`, repetido como `queued_duplicate` y registrado en App Insights; el ledger ficticio cambió una unidad, no dos. Poison queue: 0.
4. Storage Azure: TLS 1.2/HTTPS, cifrado Blob, soft delete 7 días; sin versionado y con acceso de red pública. No equivale a backup PostgreSQL.

## Pendiente y bloqueos

1. **AWS read-only e inventario:** pedir al laboratorio que quite la denegación o una vista autorizada. Hasta entonces no desplegar, cambiar DNS, probar RDS/ASG ni afirmar el estado del stack.
2. **Restauración PostgreSQL entre nubes:** obtener conexión/credenciales de DB y permiso para leer el backup; generar exportación cifrada hacia Blob, retenerla, verificar checksum y restaurarla aislada. Nunca guardar dump ni secretos en GitHub.
3. **Escalado y cuello RDS:** leer conexiones, CPU, latencia, pool y CloudWatch; si las métricas prueban agotamiento de conexiones, evaluar RDS Proxy. Solo entonces ejecutar carga progresiva y capturar el paso ASG 2→3 con p95/errores.
4. **Red privada:** gateway Azure P2S `Succeeded`; una conexión P2S apareció en métricas históricas, no hay puntos actuales; route table consultado vacío. Confirmar rutas/túnel desde el router y AWS→Flex. P2S + router es una alternativa autogestionada, no AWS Site-to-Site/BGP.
5. **Eventos:** Azure Functions ya cumple un flujo serverless Azure con Queue/Blob. No crear Lambda duplicada salvo criterio explícito; si el curso pide Lambda, primero obtener rol mínimo autorizado. AWS no se puede comprobar ahora.
6. **Entra ID/MFA:** sigue sin comprobarse ni desplegarse; requiere registrar/configurar OIDC en el tenant y preservar un acceso break-glass. No reemplazar el login actual sin validar el tenant y permisos.
7. **GitHub y ciclo de vida:** CloudFormation y Terraform describen recursos, pero no se probó reconstrucción integral. El script `destroy.sh` es solo AWS, protegido y destructivo; no hay un comando único validado para levantar/borrar ambas nubes. Las raíces Azure también dependen de estados separados. No se debe añadir ni ejecutar un borrado orquestado hasta recuperar el inventario, confirmar los estados remotos y probar los backups/restores.

## Verificación siguiente

- Resolver la política de solo lectura de AWS antes de cualquier `change set`, `apply`, carga o restore de RDS.
- Consultar Azure P2S `P2SConnectionCount` y métricas de Function en el mismo corte de la prueba privada.
- Completar restore cruzado, registro de trazas y escalado únicamente con datos medidos; actualizar la matriz sin atribuir pruebas locales a nube.
- Mantener capturas/consolas sin claves, cookies, correos personales ni payloads sensibles.

Consulta la [matriz por criterio](04_matriz_rubrica.md), el [runbook AWS](01_aws_ejecucion.md), el [runbook Azure](02_azure_ejecucion.md) y el [inventario IaC](../iac/README.md).
