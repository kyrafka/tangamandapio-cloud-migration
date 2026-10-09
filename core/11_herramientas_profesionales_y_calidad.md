# Herramientas profesionales y cierre de brechas

**Corte:** 8 de octubre de 2026 · **Alcance acordado:** AWS + Azure; OCI no se
implementa por instrucción recibida para el trabajo en vivo. La rúbrica escrita
todavía nombra AWS–OCI, así que se necesita conservar la autorización docente
del cambio de alcance en el informe final.

La infraestructura viva se resume en
[MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md);
este documento describe herramientas y prácticas, no un inventario adicional.

## Qué se mejoró en este corte

- La puerta GitHub Actions valida por separado backend/flujo, frontend e IaC
  AWS/Azure. Incluye las tres suites Python, sondeo de salud, carga pequeña,
  auditoría de dependencias y validación de ambas plantillas CloudFormation y
  ambos entornos Terraform.
- El workflow tiene permisos mínimos de lectura, cancela ejecuciones antiguas y
  fija sus acciones de terceros por SHA completo. No recibe credenciales cloud ni
  despliega infraestructura automáticamente.
- El job de Python instala desde `app/requirements-ci.lock` con hashes
  obligatorios; el mismo lock alimenta `pip-audit` y `cfn-lint`.
  `tests/check_python_lock.py` verifica que sus versiones satisfagan los rangos
  de los manifiestos de ejecución. El lock incluye `pip-tools` para regeneración
  trazable; los manifiestos de despliegue conservan rangos compatibles. El
  comando y cada cambio de lock se revisan, no se actualizan a ciegas.
- El frontend declara versiones exactas y `pnpm` fijo. `build:check` compila en
  `app/web/dist`, sin vaciar ni reemplazar `app/src/static`, que es un artefacto
  de publicación separado.
- La validación Terraform no usa `-upgrade` y exige lockfile de solo lectura:
  comprueba lo existente sin renovar dependencias ni aplicar recursos.
- Dependabot quedó configurado para revisar Actions, frontend, tres manifiestos
  Python y los dos entornos Terraform. Solo abrirá PRs cuando esta configuración
  se incorpore al repositorio remoto; cada cambio seguirá pasando por CI.

La puerta local equivalente es `tests/run_local_quality.ps1`; para formato y
validación de IaC (sin recursos cloud):

```powershell
.\tests\run_local_quality.ps1 -ValidateTerraform
```

El workflow confirma calidad del código del repositorio, no demuestra que AWS o
Azure estén activos ni que una prueba de navegador/infraestructura se haya hecho.

## Herramientas adecuadas para este proyecto

| Capa | Herramienta recomendada | Uso concreto aquí | Estado honesto |
|---|---|---|---|
| Revisión de arquitectura | AWS Well-Architected Tool y Azure Well-Architected Review | Revisar seguridad, confiabilidad, operaciones, rendimiento y costo por carga | Guía de diseño; falta cerrar una revisión con respuestas y evidencias |
| CI y cadena de suministro | GitHub Actions, dependencias fijadas con hashes, auditoría de paquetes; luego SBOM y firma del artefacto | Bloquear cambios sin pruebas; asociar artefacto y checksum al commit | Puerta y lock reproducible implementados; SBOM/firma y despliegue no automatizados |
| Mantenimiento de dependencias | Dependabot para Actions, pnpm, pip y Terraform | Proponer actualizaciones revisables con CI, sin aplicar cambios automáticamente | Configurado localmente; se activa al publicarse en GitHub |
| Identidad de despliegue | GitHub OIDC → rol IAM/Entra federado | Credenciales temporales restringidas por repositorio, rama y entorno | Pendiente; no habilitar hasta revisar confianza y aprobación |
| Infraestructura como código | CloudFormation para AWS; Terraform para Azure; drift/change set/plan | Evitar dos herramientas administrando el mismo recurso; revisar antes de aplicar | Validación CI/local; reconciliación del estado vivo aún obligatoria |
| Observabilidad AWS | CloudWatch dashboard/alarms/logs; CloudTrail; SSM | Salud ALB/ASG/RDS, errores, auditoría y acceso administrativo sin SSH público | Ya modelado en IaC; alarma recuperada con evidencia del corte sigue pendiente |
| Observabilidad Azure | Azure Monitor + Application Insights + Log Analytics/KQL | Invocaciones, excepciones, duración, dependencias y correlación del `event_id` | Function registra eventos estructurados; verificar telemetría y retención en portal |
| Flujo de negocio | `event_id` común, outbox, idempotencia, reintentos y cola poison | Seguir un pedido desde RDS hasta la respuesta del worker | Código de demo; reconciliar el evento/resultado en Azure sigue siendo prueba pendiente |
| Pruebas web | Playwright en Chromium para roles y recorridos; Synthetics para una URL pública | Login, permisos, crear pedido, salud y recuperación de una vista | No añadido: faltan definir cuentas de prueba/ambiente y evitar exponer credenciales |
| Seguridad de IaC | Checkov o Trivy como informe inicial; Access Analyzer en AWS | Detectar reglas públicas, permisos amplios, cifrado y exposición accidental | Recomendado; primero triage de hallazgos, no afirmar que está habilitado |
| Protección/detección | WAF, CloudTrail, GuardDuty/Config; Entra ID, Defender for Cloud | Bloqueo controlado, cambios sospechosos, identidad y postura | Algunos recursos pueden cobrar o no estar habilitados en Academy; activar por ventana |
| Optimización de costo | AWS Budgets/Cost Explorer y Azure Cost Management | Presupuesto, etiquetas, alertas, inventario y apagado del laboratorio | Falta una estimación reproducible y capturas de costo del ciclo final |
| Recuperación | RDS PITR/backup, restore aislado; versionado/lifecycle S3/Blob | Medir RPO/RTO, validar lectura, eliminar recurso temporal y guardar evidencia | Restauración PITR aislada ya validada; falta acordar y medir RTO/RPO formalmente |

## Consultas de operación para la demostración

En Application Insights / Logs, usar una consulta inicial de ejecuciones y
fallos (confirmar el nombre exacto que emite el runtime de la Function):

```kusto
requests
| where timestamp > ago(24h)
| where name has "process_fulfillment_message"
| summarize ejecuciones=count(), fallos=countif(success == false),
            p95_ms=percentile(duration, 95) by bin(timestamp, 5m)
| order by timestamp desc
```

Para seguir la correlación sin sacar el payload del pedido:

```kusto
traces
| where timestamp > ago(24h)
| where message has "event_id="
| project timestamp, severityLevel, message, operation_Id
| order by timestamp desc
```

La prueba vale solo si la Function envía telemetría a ese recurso y aparecen
filas recientes. Un dashboard vacío no es éxito ni fallo de negocio: es evidencia
incompleta; confirmar conexión, tabla, filtros y retención antes de presentar.

En AWS, el recorrido mínimo del dashboard es: `HealthyHostCount` y latencia/5xx
del ALB → capacidad y actividad de ASG → CPU/conexiones/espacio de RDS → estado
de la alarma al generar y retirar una señal sintética aprobada. Mantener pruebas
de carga pequeñas y etiquetadas; no usar tráfico real ni disparar fallos de
instancias en una sesión con saldo incierto.

## Brechas que aún afectan la rúbrica

La autoevaluación existente de **11.00/20** usa una conversión estimada porque
la hoja no asigna una nota numérica exacta a cada descriptor; no equivale a una
calificación docente. La puerta nueva mejora la evidencia de IaC/pruebas, pero
por sí sola no concede los puntos live. Para cerrar el proyecto, lo prioritario
es:

1. **Alcance y arquitectura:** adjuntar la instrucción docente AWS–Azure frente
   a AWS–OCI escrito, y entregar un informe final único con arquitectura real,
   objetivo y componentes efectivamente desplegados.
2. **Red/seguridad:** evidencia actual de VPC/subredes/rutas/SG, RDS privada,
   permisos mínimos y denegación por rol; conservar dominio/HTTPS para la fase
   final solicitada.
3. **Escala y continuidad:** prueba acotada de ALB/ASG/recuperación y evento
   Azure; restauración RDS aislada con tiempos RTO/RPO; revisar mensajes de error
   repetido/poison sin borrarlos inadvertidamente.
4. **Observabilidad:** capturas recientes de inventario AWS y monitor Azure,
   invocación correcta con un `event_id` y alarma que dispara y vuelve a OK.
5. **Portal:** prueba de cada rol en navegador, gestión segura de usuarios y
   manual de demo; A/V real entre dos navegadores queda aplazado como indicó el
   usuario.
6. **Costo y sustentación:** supuestos de tráfico/retención, estimación mensual,
   evidencia de presupuesto y guion que explique límites del WMS ficticio.

No agregar Kubernetes, un segundo balanceador, Grafana administrado ni Service
Bus por estética. Para el volumen y objetivo académico actual, el stack
administrado existente es más fácil de explicar, medir y cerrar con seguridad.

## Fuentes oficiales

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/wellarchitected-framework.html)
- [Endurecer GitHub Actions](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats)
- [Supervisar Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/monitor-functions)
- [Supervisar ejecuciones de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-monitoring)
- [Configurar monitorización de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/configure-monitoring)
