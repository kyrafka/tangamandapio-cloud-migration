# Tangamandapio S.A.C. — Centro de Datos Cloud Empresarial

Proyecto académico de migración de un datacenter corporativo para **Tangamandapio S.A.C.**, empresa ficticia de distribución mayorista, retail omnicanal y logística regional.

## Núcleo vigente

- **AWS:** canal transaccional público: portal B2B, API, balanceo, cómputo escalable, PostgreSQL, objetos y observabilidad.
- **Azure:** dominio operativo de cumplimiento: recepción idempotente de eventos, cola WMS, evidencia privada y telemetría.
- **OCI:** fuera del alcance del Entregable 1; la solución se sustenta en AWS y Azure.
- **Modelo:** híbrido durante la migración de sedes/datacenter y multicloud en el destino.

El único registro rector es [core/00_registro_maestro.md](core/00_registro_maestro.md). Un recurso solo se declara desplegado si existe evidencia real en `evidence/current/`.

Antes de ejecutar recursos AWS, consultar el [mapa AWS predespliegue](core/06_aws_mapa_pre_despliegue_2026-09-30.md): contiene el inventario vivo, alcance, monitoreo, costos y brechas declaradas.

## Estado operativo al 01/10/2026

| Entorno | Hecho verificable | Estado |
|---|---|---|
| AWS Academy | La sesión del laboratorio terminó en `CREATE_FAILED` antes de entregar acceso utilizable; no hay recursos Tangamandapio creados en la sesión actual. | Pendiente recuperar el laboratorio y repetir despliegue/evidencias. |
| Azure for Students | Vertical WMS temporal creado en West US: Function Linux `Running`, inventario PaaS y Health autenticado HTTP `200`. | Pendiente repetir `Fulfillment` y comprobar Blob privado + Queue. |
| OCI | Fuera del alcance acordado para este entregable. | No implementar ni presentar como parte de la solución actual. |

## Estructura

- `core/`: alcance, plan de despliegue y matriz de rúbrica vigentes.
- `iac/`: CloudFormation y Terraform a revisar/aplicar en ventanas controladas.
- `app/`: aplicación, API y receptor de eventos.
- `tests/`: pruebas formales y scripts.
- `evidence/current/`: única evidencia apta para el proyecto vigente, incluida la evidencia Azure actual.
- `evidence/legacy/` y `archive/`: antecedentes excluidos de la publicación y de la evaluación vigente.
