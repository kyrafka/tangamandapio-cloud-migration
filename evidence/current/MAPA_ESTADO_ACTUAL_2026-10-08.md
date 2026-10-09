# Mapa del estado actual — 08/10/2026

**Corte:** 19:48 CDT. **Alcance:** solo recursos y pruebas que constan como existentes/observados. La consulta actual fue de solo lectura; no se aplicó Terraform ni CloudFormation.

## Lo que está activo ahora

### AWS — `us-east-1`

- CloudFormation `tangamandapio-live-20261005`: `UPDATE_COMPLETE`, **51 recursos**, último cambio registrado el 08/10. Drift reportado `IN_SYNC`.
- La plantilla descargada de CloudFormation coincide, tras normalizar saltos de línea, con `iac/cloudformation/aws-lab.yaml`; `validate-template` pasó.
- ALB y target group activos; **2/2 targets healthy**. Auto Scaling: mínimo 2, deseado 2, máximo 4; 2 instancias `InService` y sanas.
- RDS PostgreSQL: `available`, Multi-AZ, cifrado, privada (`PubliclyAccessible=false`), `db.t3.micro`, backups automáticos de 7 días.
- `GET /health` respondió `status=ok` y `database=ok`. La comprobación HTTPS usó `curl -k`: no valida confianza del certificado. No hay dominio propio ni HTTPS confiable verificado.

### Azure — `westus`

- Resource Group `rg-tangamandapio-261005-wus`: estado `Succeeded`.
- Inventario actual: **10 recursos de nivel superior**, todos con `provisioningState=Succeeded`: Function App y plan, Storage, Key Vault, Application Insights, Log Analytics, dos Action Groups (uno de Smart Detection) y dos alertas de métricas (5xx y latencia).
- `tangama-wms-fn`: habilitada, estado de runtime `Running`, `httpsOnly=true`.
- El flujo es **demostrativo**: Blob/Queue y ledger de inventario ficticio. No está conectado a existencias reales ni a un ERP/WMS autorizado. En las ejecuciones revisadas anteriormente el resultado explícito fue `simulated_fulfillment_completed`; no se ha comprobado en este corte una invocación nueva ni una modificación real de stock.
- La restauración PITR de RDS se probó anteriormente con una copia temporal de lectura y luego se eliminó. Falta documentar mediciones formales de RTO/RPO.

## Aplicación y pruebas realizadas

- El portal local que sirve `127.0.0.1:8080` pertenece a la copia `Tangamandapio_SAC_LIMPIO`, fuera de este repositorio. La corrección más reciente separó fallos de endpoints opcionales y redirige sesiones vencidas al login.
- Último control local documentado: **59/59 pruebas** y build de producción aprobado; seis roles se ejercitaron con cuentas sintéticas y una base aislada. Esto no valida las cuentas persistentes del sitio publicado.
- La interfaz de telefonía/WebRTC está implementada, pero no se verificó una llamada bidireccional real de audio/video entre dos navegadores y redes distintas. La pila de grabaciones existe; no se probó aquí un ciclo real de grabar/reproducir.
- Las capturas de consola mostradas en navegador no quedaron archivadas como PNG; [CAPTURAS_PENDIENTES.md](CAPTURAS_PENDIENTES.md) conserva la lista de evidencias que aún falta guardar.

## IaC y preparación de despliegue

| Área | Hecho comprobado | Estado real para aplicar |
|---|---|---|
| AWS CloudFormation | `aws-lab.yaml` coincide con la plantilla viva; validación AWS correcta; stack sin drift. `deploy.sh` ahora crea un change set revisable, conserva parámetros actuales (incluidos `NoEcho`) y no lo ejecuta por defecto. | **Listo para preparar/revisar un update** del stack existente. No se desplegó ningún cambio en este corte. |
| Terraform AWS `environments/demo` | `fmt -check` y `validate` pasan; código cubre solo una nueva VPC segmentada y Azure opcional. No hay Terraform state. | **No es el gestor del AWS activo.** Aplicarlo crearía una VPC adicional; no usar para actualizar el stack CloudFormation. |
| Terraform Azure `environments/azure-demo` | `fmt -check` y `validate` pasan. El state local (02/10) registra el grupo viejo `rg-tangamandapio-261001r2-wus`, no el actual `rg-tangamandapio-261005-wus`. Además, el `terraform.tfvars` local no define `function_package_path`; el `plan -refresh-only` se detuvo por esa variable faltante. | **No listo para aplicar.** Falta respaldar y reconciliar/importar recursos actuales en un state aislado, incluir alertas/Action Groups y producir/verificar el plan sin reemplazos ni borrados. No se tocó state ni nube. |

## Aún no debe presentarse como terminado

- WMS/ERP real y descuento de inventario empresarial.
- Invocación Azure correlacionada de extremo a extremo en el corte actual, con evidencia durable de resultado.
- Aplicación automática de cambios Azure mediante Terraform después de reconciliar state.
- Medición formal de RPO/RTO para la restauración PITR ya probada.
- Prueba A/V real entre dos navegadores; grabación/reproducción de voz comprobada.
- Dominio propio con certificado confiable y capturas de evidencia archivadas.

## Cambios hechos en este corte

Se corrigió la guía de infraestructura para que refleje el inventario actual, se reemplazó el script AWS que apuntaba al stack antiguo y podía resetear parámetros por defecto por uno que prepara un change set y conserva valores previos, y se etiquetaron los ejemplos Terraform de Azure como sandbox aislado. No hubo `apply`, `execute-change-set`, reinicio ni borrado cloud.
