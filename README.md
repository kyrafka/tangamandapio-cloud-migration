# Tangamandapio S.A.C. — proyecto cloud AWS + Azure

Proyecto académico de un centro de operaciones para una distribuidora ficticia. El alcance vigente es AWS para portal/transacciones y Azure para el flujo logístico demostrativo; OCI no forma parte del despliegue actual.

## Estado vigente

El [mapa de estado actual](evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md) es la referencia única para separar lo que existe hoy de los registros históricos.

| Área | Estado comprobado |
|---|---|
| AWS | CloudFormation `tangamandapio-live-20261005`, `UPDATE_COMPLETE`, 51 recursos, `IN_SYNC`; 2/2 destinos saludables; RDS disponible, privado, cifrado, Multi-AZ y backup de 7 días. `/health` responde correctamente. |
| Azure | Grupo actual en West US con 10 recursos `Succeeded`; Function `tangama-wms-fn` habilitada y `Running`. El inventario/fulfillment sigue siendo demostrativo, no un WMS conectado a existencias reales. |
| Terraform AWS | El entorno `demo` valida, pero solo crea una VPC independiente y no administra el stack CloudFormation activo. No aplicar como actualización del stack. |
| Terraform Azure | El código valida, pero su state local pertenece a un grupo anterior y falta `function_package_path` en la configuración local. No aplicar hasta reconciliar/importar el state. |
| Portal y roles | La última puerta local documentada aprobó 59 pruebas; la matriz de roles se probó con cuentas sintéticas en entorno aislado. Eso no sustituye pruebas de acceso autenticado en el sitio vivo. |
| Pendientes no declarados como terminados | WMS real, automatización cloud-to-cloud con pedido vivo tras el último cambio, A/V bidireccional en dos navegadores, HTTPS confiable/dominio y capturas crudas archivadas. La restauración PITR temporal se probó; falta medir formalmente RTO/RPO. |

No se aplicaron cambios a AWS ni Azure durante la actualización de este mapa. La plantilla AWS local coincide con la plantilla del stack; `iac/cloudformation/deploy.sh` prepara primero un change set y requiere confirmación explícita para ejecutarlo.

## Pruebas locales

```powershell
.\tests\run_local_quality.ps1
```

La última ejecución documentada pasó **59/59 pruebas**, build frontend y auditorías de dependencias. `terraform fmt`/`validate`, `cfn-lint` y las validaciones AWS también pasan. Son comprobaciones de código; no certifican un WMS real, las llamadas A/V entre redes ni el plan seguro de Terraform Azure.

## Estructura

- `core/`: registro rector, rúbrica, propuesta y brechas.
- `app/`: backend, frontend, Function Azure, release AWS y pruebas.
- `iac/`: CloudFormation activo para AWS y ejemplos Terraform separados.
- `evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md`: inventario más reciente.
- `evidence/current/`: bitácoras fechadas; cada una conserva el corte en que se tomó y no reemplaza el mapa actual.
- `deliverables/`: documentos de entrega y trabajo.

No se eliminó evidencia histórica, state local ni archivos sin seguimiento durante esta limpieza; se conservaron porque pueden contener trabajo o datos de recuperación del proyecto.
