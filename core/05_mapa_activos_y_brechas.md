# Mapa de activos y brechas — corte 21:26 UTC (histórico)

**Corte:** 08/10/2026. **Alcance acordado:** AWS para portal/transacciones y
Azure para el WMS de demostración. OCI queda fuera del trabajo operativo; los
documentos escritos del curso aún la mencionan, por lo que la excepción debe
respaldarse por escrito antes de entregar (ver [evaluación de rúbrica](10_evaluacion_rubrica_entregable_final_2026-10-08.md)).

Este inventario corresponde a las 21:26 UTC del 08/10 y se conserva como
bitácora histórica. Para el intento AWS más reciente, usa
[AWS-DESPLIEGUE-V11](../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md)
y la [matriz de rúbrica actualizada](04_matriz_rubrica.md); la
[revalidación del 14/10](../evidence/current/CLOUD-REVALIDATION-2026-10-14.md)
precede a v11. No presentes las tablas de esta bitácora como estado actual.

## Verificación operativa registrada — 08/10/2026, 21:26 UTC

- CloudFormation local reconciliado contra el template vivo; validación de plantilla aprobada y stack `IN_SYNC` (0 drift) después del cambio controlado.
- Despacho automático habilitado (`AUTO_DISPATCH_EVENTS=true`) y reintento cada 60 s, confirmado en las dos instancias nuevas; ASG y ALB terminan 2/2 saludables.
- RDS original disponible y sin cambios. Restauración PITR temporal probada con lectura desde EC2 privada (10 tablas públicas presentes) y copia temporal eliminada.
- Azure Function health 200. El poison message observado quedó preservado: el hash de Queue no coincide con el SHA-256 válido del Blob; existe resultado de fulfillment y el outbox AWS indica `delivered` en 1 intento.
- Calidad local: 59/59 pruebas y build de frontend aprobados. La cobertura de roles es de pruebas automatizadas; el login live confirmó cookie `Secure` y la validación autenticada en navegador queda pendiente de HTTPS confiable.
- Audio/video, dominio y HTTPS confiable siguen diferidos a propósito. El WMS de Azure sigue siendo una simulación de inventario.

## 1. Activos disponibles

| Activo | Estado comprobado | Uso / límite |
|---|---|---|
| `iac/cloudformation/aws-lab.yaml` | Reconciliada con la plantilla viva; `cloudformation validate-template` aprobado | Conserva el estado real de RDS/seguridad/backups y activa el despacho automático; drift del stack: 0. |
| `iac/modules/aws_network/` | Módulo Terraform con formato validado | Diseño/red AWS; no reemplaza la plantilla CloudFormation del stack. |
| `iac/environments/demo/` | `terraform validate` aprobado; `enable_azure=false` por defecto | Entorno compuesto AWS/Azure, sin `apply` en esta revisión. |
| `iac/modules/azure_operations/` y `iac/environments/azure-demo/` | `fmt` y `validate` aprobados | El paquete de Function ya se publicó manualmente; revisar plan y drift antes de usar IaC o `apply`. |
| `app/` | Portal/API, Function Azure, release AWS y tres suites locales | 59/59 pruebas; build frontend aprobado; `/platform` está publicado detrás del login; el ledger SKU/cantidad sigue siendo demo. |
| `tests/aws/` | Pruebas preparadas para S3, alarmas, denegación y restore | Revisar región, costo, alcance y limpieza; no equivalen a pruebas ya ejecutadas. |
| `iac/modules/oci_network/` | Material heredado | Archivo fuera del alcance; no desplegar. |
| `evidence/current/` | Registros y capturas de ciclos distintos | Respetar fecha/origen; no presentar una tarjeta como captura cruda ni evidencia histórica como estado vivo. |

## 2. Estado cloud observado en esta revisión

| Proveedor | Comprobación | Resultado y límite |
|---|---|---|
| AWS | STS, CloudFormation, ALB, destinos y RDS — 14/10/2026, 10:37 | Cuenta correcta; stack `UPDATE_COMPLETE`, deriva reportada `IN_SYNC`, `/health=200`, destinos 2/2 sanos. RDS `available`, cifrada/privada, Single-AZ y backup 1 día. |
| Azure | Function `tangama-wms-261008`, health e IaC — 14/10/2026, 10:37 | Function `Running`, `/api/health=200`; `terraform plan` terminó `No changes`. El ledger es sintético por alcance; tres ventas y una recepción QA llegaron desde el portal AWS. |
| Cambios | AWS y Azure | No se aplicó infraestructura durante esta revalidación. La venta/recepción QA y los SecureString de cuentas demo sí son datos/secretos de aplicación; el inventario sintético no implica stock comercial. |

## 3. Matriz de brechas priorizadas

| Prioridad | Brecha | Criterio de cierre |
|---|---|---|
| P0 | Alcance escrito AWS–OCI vs. instrucción comunicada AWS–Azure | Adjuntar aceptación del docente y reflejar la decisión en el informe final. |
| P0 | IaC AWS no reconciliada | **Cerrado en este corte:** template local reconciliado; stack post-cambio en `IN_SYNC`, 0 drift. |
| P0 | Recuperación no probada | **Prueba PITR aprobada:** copia aislada disponible y legible desde EC2; se eliminó. Falta medir RTO/RPO formal. |
| P0 | Alcance del WMS académico | **Aclarado:** la Function Azure y su ledger Blob son una simulación intencional alimentada con datos sintéticos; no se exige ni se afirma inventario comercial. El flujo AWS→Azure con SKU/cantidad, ventas, recepción e idempotencia ya está probado. Un WMS empresarial queda como evolución solo si el caso lo requiere. |
| P1 | HA/escalabilidad no demostradas bajo fallo/carga | Probar pérdida controlada de destino, capacidad ASG y recuperación; registrar métricas. |
| P1 | Observabilidad incompleta | Mostrar dashboards y una alarma que se active/recupere, además de tratar la poison queue. |
| P1 | Seguridad e integración de roles | Pruebas automatizadas de autorización aprobadas; falta sesión manual en navegador. HTTPS confiable y cookie `Secure` se difieren con el dominio. |
| P1 | Integración y recuperación de eventos AWS→Azure | E2E autenticado desde el portal AWS probado: 7/7 eventos outbox entregados; tres ventas `completed_demo`, recepción `received_demo`; balances sintéticos conservados. La conectividad usa HTTPS público. La poison queue se documentó históricamente; falta una revisión operacional actual y no se alteró su mensaje. |
| P1 | Costos y documentación final | Estimación mensual con supuestos; informe final y capturas crudas actuales de consola/monitores. |
| P2 | Telefonía A/V real | Probar audio/video bidireccional en dos navegadores/redes; no declarar “comprobado” solo por pruebas API. |
| P2 | Dominio HTTPS | Dejarlo para el cierre acordado: DNS, ACM, redirección y verificación del certificado/cookie. |

## 4. Siguiente secuencia segura

1. Confirmar alcance AWS–Azure con el docente, sin crear recursos OCI.
2. Mantener el template reconciliado como fuente; no recrear ni re-aplicar
   infraestructura salvo que el próximo change set sea revisado.
3. Preservar el dataset QA sintético y revisar la poison queue de forma aislada;
   el recorrido autenticado de venta/recepción portal→Azure ya está probado.
4. Validar visualmente `/platform` y la matriz de roles en navegador; las
   pruebas automatizadas ya cubren los permisos principales.
5. Ejecutar pruebas controladas de HA/escala y alarmas; documentar el flujo
   demo como tal, calcular costos y confirmar limpieza.
6. Consolidar informe final y capturas; dominio/HTTPS queda para el final.

No reutilizar credenciales temporales ni poner claves/tokens en evidencias. La
puerta local para repetir las suites es `tests/run_local_quality.ps1`; la
validación opcional Terraform usa `-ValidateTerraform` y no aplica recursos.
