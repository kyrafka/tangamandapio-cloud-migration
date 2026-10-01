# Mapa de activos y brechas — fase actual

**Decisión de ejecución:** Azure queda congelado. No se crean recursos, no se aplica Terraform y no se modifica su configuración hasta una orden posterior. El Resource Group existente se conserva sin cambios.

## 1. Activos disponibles

| Activo | Estado | Uso en el núcleo |
|---|---|---|
| `iac/cloudformation/aws-lab.yaml` | Candidato AWS normalizado a Tangamandapio; revisión estática local aprobada | Validar en CloudFormation y revisar el cambio antes de crear recursos |
| `iac/modules/aws_network/` | Módulo Terraform de red | Referencia/reutilización; no aplicar sin validar entorno |
| `app/` | Portal, API, pruebas y simuladores locales normalizados a Tangamandapio | `15` pruebas locales aprobadas; falta prueba real detrás del ALB |
| `tests/aws/` | Scripts de seguridad, storage, alarma y restore | Revisar nombres, parámetros y costo antes de ejecutar |
| `iac/modules/oci_network/` | Base técnica OCI archivada del enfoque anterior | Punto de partida para VCN, no evidencia ni despliegue |
| `evidence/current/aws/baseline-before-core/` | Registro AWS de Tangamandapio anterior al nuevo núcleo | Antecedente parcial; no cierra las pruebas CUR |
| `evidence/legacy/andemarket-historical/` | Capturas y registros con otro nombre/alcance | Solo procedimiento recuperable |

## 2. Dependencias para AWS

| Dependencia | Situación | Acción antes de levantar |
|---|---|---|
| AWS Academy Learner Lab | Apagado al último cierre | Usuario inicia una nueva ventana de laboratorio |
| CloudFormation | Plantilla normalizada y revisada localmente | Validar y revisar changeset dentro de AWS Academy |
| Aplicación | Portal estático y API preparados; no comprobados detrás de ALB vigente | Ejecutar prueba real de portal, salud y pedidos contra el ALB |
| Base de datos | Configurada en IaC, sin evidencia vigente de SQL | Probar alta, consulta, aislamiento y backup |
| HTTPS | No garantizado por el piloto HTTP anterior | Resolver dominio/ACM o documentar limitación académica |
| Costo | NAT, ALB, RDS y EC2 generan consumo | Ventana corta, plan de cierre y captura final |

## 3. Mapa de rubrica por prioridad

| Prioridad | Criterios | Entregable verificable |
|---|---|---|
| P0 | Arquitectura, VPC/VCN, seguridad, IaC | Diagramas actuales, plantilla validada y configuraciones de red |
| P0 | Cómputo/BD, HA, pruebas | App real, RDS privada, ALB, dos targets y prueba de caída |
| P1 | Monitoreo, backup, RTO/RPO | Dashboard, alarma, restore y tiempos medidos |
| P1 | Costos | Presupuesto y cierre con inventario final |
| P0 final | AWS–OCI/multicloud | VCN OCI e integración real, segura y demostrable |

## 4. Secuencia de trabajo aprobada

1. Validar el flujo, seguridad, pruebas y plan de cierre AWS desde CloudShell de AWS Academy.
2. Desplegar AWS únicamente cuando el Learner Lab esté activo; capturar evidencia CUR-AWS y destruir todo al cierre.
3. Ejecutar Azure como dominio operativo únicamente después del cierre comprobado de AWS y con presupuesto controlado.
4. Diseñar/ejecutar OCI para continuidad y la integración exigida por la rúbrica.
