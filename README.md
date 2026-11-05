# Tangamandapio — portal empresarial y arquitectura cloud

Proyecto académico de una distribuidora ficticia. La arquitectura de referencia contempla 450 colaboradores, 220 cuentas internas, tres centros en Perú y picos de hasta 3,000 usuarios externos. Las cifras son supuestos de diseño, no mediciones de producción. El catálogo y el inventario son datos sintéticos.

## Uso e infraestructura

El portal y el WMS se despliegan por separado. AWS usa CloudFormation; Azure usa varias raíces Terraform. Las sesiones de AWS Academy caducan: antes de operar, inicia el laboratorio y verifica la cuenta con `aws sts get-caller-identity`. Para Azure, inicia sesión con `az login` y verifica la suscripción con `az account show`. Nunca incluyas credenciales, tokens, archivos de estado o planes en el repositorio.

Para preparar el entorno AWS, revisa primero [la guía de CloudFormation](iac/cloudformation/README.md). `iac/cloudformation/lifecycle.sh up` requiere cuenta y nombre de stack explícitos, los datos de la Function y su secreto ya provisionado; HTTPS necesita el certificado y el dominio. Una base nueva exige aceptación expresa y solo recrea datos sintéticos. El script solicita confirmación y genera recursos facturables.

En Azure, configura una copia local de `iac/environments/azure-rebuild/rebuild.tfvars.example` y consulta [la guía de Azure](iac/environments/azure-rebuild/README.md). El lanzador PowerShell `lifecycle.ps1 up -ExpectedSubscriptionId <GUID>` revisa la suscripción, crea el paquete de la Function y presenta el plan antes de pedir confirmación. La VPN, la red privada y otras raíces se administran por separado.

**Borrado y reconstrucción integral: pendientes.** No se ha probado un ciclo completo entre ambas nubes desde cero, ni hay un solo comando que restaure todos los datos, secretos, DNS y VPN. Terraform protege contra destrucción el almacenamiento y el Key Vault usados para recuperación; el comando general de destrucción de Azure se detendrá hasta resolver su conservación. AWS puede eliminar datos y snapshots según las opciones elegidas: revisa el alcance y los respaldos antes de ejecutar cualquier borrado. No ejecutes los comandos destructivos únicamente para comprobarlos.

El 05/11/2026 se guardó una copia manual cifrada de PostgreSQL en Azure Blob y se restauró en un entorno aislado, con 20 tablas y sus conteos verificados. **El envío automático sigue pendiente**; la clave y la copia necesitan conservarse independientemente del entorno de aplicación. Los registros fechados que siguen son históricos y no sustituyen una comprobación actual.

## Revalidación AWS–Azure — 03/11/2026, posterior a las 19:53 UTC

Se reconstruyó temporalmente el entorno AWS en la cuenta `654654388734` y se comprobó RDS PostgreSQL privado y cifrado en Multi-AZ (`us-east-1a` y `us-east-1b`), con siete días de retención. WAF permitió una solicitud normal (200) y bloqueó las pruebas de XSS y SQLi (403). El inicio de sesión administrador y las consultas de usuarios, pedidos e inventario respondieron 200 desde EC2.

El ASG escaló automáticamente de dos a tres instancias y se observaron tres destinos saludables. La carga recibió 28.187 respuestas 200 con p95 de 189,55 ms sobre un **archivo estático**; comprueba ese mecanismo de escalado, no la capacidad de 3.000 usuarios ni una carga transaccional sostenida. El resultado medido está en [la evidencia de escalado](evidence/current/aws-scale-revalidation-20261103.json).

Un evento generado en AWS (`evt-04d16ff9f38e411bae44b95efcd598cb`) llegó a Azure y terminó en `demo_fulfillment_completed`: el inventario sintético pasó de 24 a 23. La reposición de prueba (`evt-restore-b16390c6d91c43da8241265db680b5ac`) terminó en `demo_restock_completed` y recuperó el saldo de 23 a 24. El tránsito utilizó el endpoint público HTTPS de Azure; la VPN y BGP no estaban activos. La prueba de permisos `CreateCustomerGateway` fue rechazada por una SCP.

El desmontaje terminó con `PROJECT_STACKS_AND_RETAINED_DATA_PURGED`. En `us-east-1` solo quedó la pila base de Academy: no se observaron EC2, ASG, ALB, RDS, NAT, EIP, WAF ni buckets del proyecto, ni snapshots manuales o backups automáticos. Se conservaron cinco secretos de Tangamandapio, que pueden generar cargos. Academy mostró **Lab terminated**, AWS **Terminated** y `00:00`.

El medidor de Academy indicó **US$18,60 de US$50** tanto al inicio como al cierre; Academy documenta un retraso de 8–12 horas, así que la lectura no permite calcular el costo real de esta sesión ni su promedio por hora. Azure Cost Management mostró **US$0,0023796** acumulados en el mes tanto al inicio como al cierre, también con posible retraso. Los recursos Azure preexistentes se conservaron y no se probó el ciclo integral de borrado y reconstrucción de Azure.

### Corte anterior — 03/11/2026, 19:53 UTC

- **Portal y dominio:** `https://tangamandapio.kendellnm.me/` y `/health` devuelven Cloudflare `530 / 1016`; el origen no resuelve actualmente. No se modificó Cloudflare.
- **AWS (cuenta del laboratorio `654654388734`, `us-east-1`):** la consola muestra solo la pila base de Academy (`CREATE_COMPLETE`). No hay instancias EC2, grupos de Auto Scaling, balanceadores, bases RDS, colas SQS ni Web ACL de WAF del proyecto. Por eso hoy no se puede repetir el escalado 2→3 ni un recorrido iniciado en AWS. El perfil local de AWS CLI no quedó actualizado: la revisión automática bloqueó el cambio antes de escribir credenciales; las consultas anteriores de este corte se hicieron en la consola autenticada.
- **Azure:** Function `tangama-wms-261030` está `Running` y HTTPS-only; `/api/health` devolvió 200. El ledger autenticado contiene 13 SKU sintéticos. Las lecturas protegidas y la recepción POST sin clave devolvieron 401. Existen `fulfillment-events` y `fulfillment-events-poison`; la consulta de poison devolvió 0 mensajes.
- **Eventos WMS:** Application Insights registró dos solicitudes `health` en las últimas 24 horas, cero trazas `queued_event` y cero `wms_demo_` de resultado. El recorrido AWS→Azure sí se demostró históricamente desde EC2 hacia Azure Queue/Function por HTTPS público; no cruzó la VPN. Hoy no está activo ni revalidado porque no hay infraestructura AWS del proyecto.
- **Conectividad privada:** el inventario actual de Azure no devuelve VNet, VPN Gateway ni Private Endpoint del proyecto; solo aparecen Network Watchers de plataforma. El piloto anterior de router EC2 + Azure P2S fue de un solo camino, sin alta disponibilidad ni BGP, y ya no se observa desplegado.
- **BGP pendiente:** diseñar y probar luego VPN administrada AWS–Azure con BGP, rutas privadas propagadas y tolerancia a la caída de un túnel. El diseño IaC está descrito en [`iac/environments/aws-azure-vpn`](iac/environments/aws-azure-vpn/README.md), pero no está desplegado.
- **Recuperación y escala:** no hay RDS vivo que exportar/restaurar ni ASG activo para medir escalado. No se cambiaron recursos AWS/Azure ni se envió un evento de prueba en este corte.

Las observaciones de ese corte anterior preceden a la reconstrucción y pruebas descritas arriba. Los E2E, el piloto P2S y las pruebas de escalado de octubre son antecedentes fechados. Ver [evidencia histórica AWS→Azure](evidence/current/aws/AWS-AZURE-E2E-2026-10-16-0231UTC.md), [piloto P2S](evidence/current/azure/AZURE-AWS-INTEROP-2026-10-13.md), [prueba histórica de escalado](evidence/current/aws/AWS-AUTOSCALING-TEST-2026-10-14.json) y la [matriz de criterios](core/04_matriz_rubrica.md).

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
