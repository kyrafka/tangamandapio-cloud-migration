# Tangamandapio — portal empresarial y arquitectura cloud

Proyecto académico de una distribuidora ficticia. La arquitectura de referencia contempla 450 colaboradores, 220 cuentas internas, tres centros en Perú y picos de hasta 3,000 usuarios externos. Las cifras son supuestos de diseño, no mediciones de producción. El catálogo y el inventario son datos sintéticos.

## Estado conocido — 29/10/2026

- **Portal público:** `https://tangamandapio.kendellnm.me/` respondió HTTP 503 en la última consulta. El TLS del dominio negocia, pero la aplicación no está saludable en esa comprobación.
- **AWS:** STS autenticó la sesión del laboratorio, pero las consultas de inventario de servicios fueron denegadas por una política explícita. El último corte documentado del 27/10 registra ALB, WAF, ASG, EC2 y RDS Multi-AZ; ese inventario no se pudo revalidar hoy.
- **Azure:** se inventariaron Functions, Storage, Key Vault, Application Insights, Log Analytics, alertas, VNet, DNS privado, Private Endpoint y VPN Gateway P2S. La Function antigua respondió 200 desde su endpoint público. La Function Flex privada devolvió 403 al consultarla desde Internet, acorde con el acceso público deshabilitado; esto no verifica la ruta privada.
- **Conectividad privada:** el registro del 29/10 describe una ruta probada desde AWS mediante un router EC2 que se conecta al P2S de Azure. Es una alternativa de un solo router/gateway, no una VPN Site-to-Site administrada por AWS ni BGP. No se pudo revalidar desde AWS en esta revisión.
- **Recuperación:** se copió y restauró un fixture JSON sintético entre S3 y Azure Blob con hashes iguales. No fue una copia ni restauración de RDS.

Las verificaciones fechadas no sustituyen un inventario vivo. No se aplicó ni eliminó infraestructura en esta actualización documental.

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
