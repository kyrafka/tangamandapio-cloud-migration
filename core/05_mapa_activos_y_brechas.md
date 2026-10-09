# Mapa de activos y brechas — corte 21:26 UTC (histórico)

**Corte:** 08/10/2026. **Alcance acordado:** AWS para portal/transacciones y
Azure para el WMS de demostración. OCI queda fuera del trabajo operativo; los
documentos escritos del curso aún la mencionan, por lo que la excepción debe
respaldarse por escrito antes de entregar (ver [evaluación de rúbrica](10_evaluacion_rubrica_entregable_final_2026-10-08.md)).

Este inventario corresponde a las 21:26 UTC del 08/10. Para lo que existe al
corte más reciente, usa [MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md); los datos aquí se conservan como bitácora de ese ciclo.

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
| AWS | STS, CloudFormation, ASG, ALB, RDS y rutas públicas | Stack `UPDATE_COMPLETE`, drift `IN_SYNC` 0; ASG/targets 2/2 saludables; auto-dispatch true, retry 60 s; RDS available/Multi-AZ/cifrado/7 días. |
| Azure | Function `tangama-wms-fn`, health, inventario y cola poison | Health 200. Mensaje poison observado y conservado: Blob y metadato SHA son íntegros, envelope Queue difiere; ya hay resultado de fulfillment. Ledger es ficticio. |
| Cambios | AWS y Azure | Template AWS reconciliado y cambio gradual aplicado; Function Azure sin cambios en esta ejecución; copia PITR temporal validada y eliminada. |

## 3. Matriz de brechas priorizadas

| Prioridad | Brecha | Criterio de cierre |
|---|---|---|
| P0 | Alcance escrito AWS–OCI vs. instrucción comunicada AWS–Azure | Adjuntar aceptación del docente y reflejar la decisión en el informe final. |
| P0 | IaC AWS no reconciliada | **Cerrado en este corte:** template local reconciliado; stack post-cambio en `IN_SYNC`, 0 drift. |
| P0 | Recuperación no probada | **Prueba PITR aprobada:** copia aislada disponible y legible desde EC2; se eliminó. Falta medir RTO/RPO formal. |
| P0 | WMS empresarial no integrado | El flujo AWS→Azure ya se probó con SKU/cantidad e idempotencia, pero modifica solo un ledger ficticio; acordar contrato y credenciales del WMS real o presentarlo explícitamente como demo. |
| P1 | HA/escalabilidad no demostradas bajo fallo/carga | Probar pérdida controlada de destino, capacidad ASG y recuperación; registrar métricas. |
| P1 | Observabilidad incompleta | Mostrar dashboards y una alarma que se active/recupere, además de tratar la poison queue. |
| P1 | Seguridad e integración de roles | Pruebas automatizadas de autorización aprobadas; falta sesión manual en navegador. HTTPS confiable y cookie `Secure` se difieren con el dominio. |
| P1 | Integración y recuperación WMS de nube a nube | Despacho automático y retry 60 s habilitados y con test unitario; falta un pedido vivo autenticado con la configuración nueva. Poison diagnosticado y preservado; decidir archivado/retirada. |
| P1 | Costos y documentación final | Estimación mensual con supuestos; informe final y capturas crudas actuales de consola/monitores. |
| P2 | Telefonía A/V real | Probar audio/video bidireccional en dos navegadores/redes; no declarar “comprobado” solo por pruebas API. |
| P2 | Dominio HTTPS | Dejarlo para el cierre acordado: DNS, ACM, redirección y verificación del certificado/cookie. |

## 4. Siguiente secuencia segura

1. Confirmar alcance AWS–Azure con el docente, sin crear recursos OCI.
2. Mantener el template reconciliado como fuente; no recrear ni re-aplicar
   infraestructura salvo que el próximo change set sea revisado.
3. Crear un pedido sintético desde una sesión autorizada y confirmar el nuevo
   despacho automático en Azure; preservar el poison hasta decidir su archivo.
4. Validar visualmente `/platform` y la matriz de roles en navegador; las
   pruebas automatizadas ya cubren los permisos principales.
5. Ejecutar pruebas controladas de HA/escala y alarmas; documentar el flujo
   demo como tal, calcular costos y confirmar limpieza.
6. Consolidar informe final y capturas; dominio/HTTPS queda para el final.

No reutilizar credenciales temporales ni poner claves/tokens en evidencias. La
puerta local para repetir las suites es `tests/run_local_quality.ps1`; la
validación opcional Terraform usa `-ValidateTerraform` y no aplica recursos.
