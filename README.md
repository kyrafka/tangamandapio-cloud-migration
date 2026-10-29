# Tangamandapio — portal empresarial y arquitectura cloud

Proyecto académico de una distribuidora ficticia. La arquitectura de referencia contempla 450 colaboradores, 220 cuentas internas, tres centros en Perú y picos de hasta 3,000 usuarios externos. Las cifras son supuestos de diseño, no mediciones de producción. El catálogo y el inventario son datos sintéticos.

## Estado conocido — 29/10/2026, 21:14 UTC

- **Portal público:** `/` y `/health` respondieron HTTPS 200; la API protegida respondió 401 sin sesión. No se confirmó login ni salud de RDS.
- **AWS:** se cambió intencionalmente la cuenta del lab. STS autentica en la cuenta nueva; el inventario de la cuenta anterior ya no aplica. CloudFormation, EC2, Auto Scaling, ALB y RDS deniegan consultas de solo lectura por política explícita del laboratorio. No se pudo iniciar una prueba desde EC2 ni revalidar el escalado; no se modificó AWS.
- **Azure:** Function Y1 `/api/health` 200; Flex privada `403` desde Internet y Private Endpoint `Approved`. Un evento sintético recorrió Queue/Function, dejó `demo_restock_completed`, el replay fue idempotente y App Insights registró el mismo ID. El ledger ficticio recibió +1 unidad; no es stock físico ni E2E iniciado por AWS.
- **Conectividad privada:** gateway Azure P2S está `Succeeded`; la métrica mostró un máximo de una conexión hace unas horas y luego no registró puntos. La tabla de rutas consultada está vacía. No se revalidó el camino AWS→Flex; P2S + router EC2 no es AWS Site-to-Site/BGP.
- **Recuperación:** Storage Azure exige HTTPS/TLS 1.2, cifra blobs y conserva borrados 7 días; no tiene versionado. No se exportó ni restauró PostgreSQL desde Blob.

No se cambió infraestructura AWS/Azure. Un evento QA sí añadió una unidad al ledger ficticio de Azure. El detalle de verificaciones y límites está en la [evidencia Azure](evidence/current/azure/AZURE-LIVE-CHECK-2026-10-29.json), el [reintento de acceso AWS](evidence/current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json) y la [matriz de criterios](core/04_matriz_rubrica.md).

## Qué hace el sistema

El portal reúne funciones B2B para distribuidores y módulos ERP para equipos internos. El ERP cubre ventas, compras, finanzas operativas, datos maestros, permisos y mensajería dentro del portal. La mensajería interna no proporciona buzones corporativos ni SMTP saliente. Azure Functions procesa eventos del WMS de demostración y actualiza un ledger sintético idempotente; no administra stock físico.

## Documentación principal

- [Infraestructura y estado de AWS/Azure](iac/README.md)
- [CloudFormation de AWS: despliegue y recuperación](iac/cloudformation/README.md)
- [Terraform: entornos y módulos](iac/)
- [Matriz de criterios y evidencia](core/04_matriz_rubrica.md)
- [Arquitectura empresarial y alcance del ERP](core/12_arquitectura_empresarial_portal_erp_correo.md)
- [Índice de capturas y evidencia seleccionada](evidence/README.md)
- [Portal y servicios de aplicación](app/README.md)
- [Plan de pruebas](tests/README.md)

## Estructura

| Ruta | Contenido |
|---|---|
| `app/` | Portal, API, ERP, paquete de release AWS, Azure Functions y pruebas de aplicación. |
| `iac/cloudformation/` | Plantillas AWS y scripts con preflight para revisar, reconstruir y eliminar stacks. |
| `iac/environments/` | Raíces Terraform independientes para Azure, red y pruebas de laboratorio. |
| `iac/modules/` | Módulos reutilizables de red y operaciones. |
| `core/` | Caso, arquitectura, costos, propuesta y rúbrica. |
| `evidence/current/screenshots/` | Capturas de consola y del portal. Cada imagen debe conservar su fecha y contexto. |

## Alcance y reconstrucción

La IaC describe los recursos, pero no contiene credenciales, certificados privados, snapshots de base de datos ni todos los artefactos y secretos necesarios para recuperar el servicio. Por eso aún no se ha demostrado una reconstrucción limpia de punta a punta desde una cuenta vacía. Antes de aplicar IaC, confirma la cuenta y región, inspecciona el estado remoto, protege los datos y secretos requeridos y revisa el change set o plan. Nunca publiques credenciales del laboratorio ni archivos `.tfstate`/planes.

Las guías de IaC describen preflight, confirmaciones, costos y límites de cada entorno. Esta documentación no afirma que un despliegue esté funcionando si la evidencia viva no lo confirma.
