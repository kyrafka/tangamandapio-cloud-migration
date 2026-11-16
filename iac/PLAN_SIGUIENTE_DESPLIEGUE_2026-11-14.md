# Plan del próximo despliegue — Tangamandapio

**Corte actualizado:** 16/11/2026
**Alcance:** cierre verificable de las observaciones pendientes del proyecto.
**Estado:** ya hubo cambios aplicados en AWS/Azure y Cloudflare no se modificó.
El registro vivo es [ESTADO_REAL_2026-11-16.md](ESTADO_REAL_2026-11-16.md); esta
guía conserva las fases pendientes y las salvaguardas para terminar el trabajo.

## Qué sabemos y qué no

- AWS fue consultado el 16/11 en la cuenta `481056890449`, región `us-east-2`.
  La pila `tangamandapio-live-20261116` administra el portal y está activa;
  WAF quedó restaurado a 30.000 solicitudes por IP cada cinco minutos.
- El ASG llegó automáticamente de 2 a 4 y luego a 5 durante 300.000
  solicitudes. El ensayo largo obtuvo p95 315,47 ms, pero 1,47% de errores y
  no pasa el umbral de 1%; una comprobación corta de 3.000 solicitudes dio cero
  errores y p95 263,86 ms. Luego el ASG bajó automáticamente 5→4→3→2; terminó
  con dos nodos sanos y la deriva de CloudFormation en `IN_SYNC`/0.
- RDS sigue cifrada y disponible, Single-AZ y con un día de retención. No hay
  copia PostgreSQL reciente automatizada en Azure Blob ni restauración aislada.
- Azure tiene la Function Flex privada, Private Endpoint, colas, Blob,
  Application Insights y dos routers Tailscale en Azure. El secreto AWS sí
  coincide con la clave específica de `receive_fulfillment_event`; AWS todavía
  no tiene ruta privada hacia la Function, así que el evento no se ha probado.
- Cloudflare mantiene `Flexible`; el certificado ACM está pendiente del CNAME
  de validación que el usuario dejó para después. No modificar DNS compartido
  hasta que el usuario complete ese paso.
- Terraform CLI ya está disponible localmente; hay que validar cada raíz
  separada antes de cualquier plan/aplicación. `iac/ESTADO_REAL_2026-11-16.md`
  separa lo confirmado de lo que continúa pendiente.
- `terraform fmt -check -recursive iac/environments` pasó y `azure-rebuild`
  pasó `init -backend=false`/`validate`. La suite `tests/iac` pasó 89 pruebas.
  No se aplicó Terraform.

## Principios para reconstruir sin duplicar recursos

1. Confirmar primero la cuenta, región, suscripción y grupos de recursos correctos; hacer inventario de solo lectura y revisar costos antes de crear recursos.
2. Tratar `iac/cloudformation/aws-lab.yaml` como la pila principal de aplicación/red de AWS. No aplicar simultáneamente `iac/environments/demo`: crea otra VPC `10.10.0.0/16` y subredes propias.
3. En Azure seleccionar explícitamente la raíz Terraform que corresponda al estado encontrado. Si un recurso existente debe quedar bajo Terraform, importar su ID al estado correcto antes de planificar; no recrearlo a ciegas.
4. Revisar planes de Terraform y Change Sets de CloudFormation y resolver reemplazos, borrados y deriva antes de cualquier `apply` o actualización.
5. Mantener fuera de IaC la zona DNS compartida de Cloudflare. No cambiar registros de otros servicios ni publicar secretos.

## Secuencia de trabajo

### Fase A — preflight de solo lectura

- Verificar identidad AWS con el perfil explícito y región `us-east-2`; confirmar que sea la cuenta personal objetivo y que la política permita inventario.
- Verificar tenant, suscripción y grupos Azure; localizar Function Flex, VNet/subredes, Private Endpoint, Queue, Blob, Key Vault y Application Insights.
- Registrar inventarios y costo inicial observados con hora y región. Si hay denegaciones de política, parar esa operación y anotar el servicio/acción; no probar rutas para eludir la política.
- Comparar lo encontrado con las pilas y estados existentes. No borrar bases, snapshots, claves ni contenedores durante la reconciliación.

**Salida:** inventario de recursos con propietario IaC, región, estado, costo/retención conocida y acción propuesta.

### Fase B — validar plantillas y seleccionar raíces

- Ejecutar `cfn-lint` en la plantilla principal y revisar parámetros, nombres, referencias y políticas de borrado.
- Instalar/usar una versión funcional de Terraform y validar **una raíz seleccionada por vez** (`fmt -check`, `init -backend=false` solo para raíces sin backend remoto requerido, `validate`, luego `plan`). No inicializar ni cambiar el backend del estado productivo como experimento.
- Revisar `iac/cloudformation/lifecycle.sh` y sus requisitos. Su alcance actual no es un botón mágico multinube: no reconstruye DNS, enrolamiento/aprobación Tailscale, las distintas raíces Azure ni recuperación regional completa.
- Confirmar artefactos de aplicación, parámetros y secretos necesarios sin imprimir valores. Mantener la AMI fijada mediante parámetro si se busca reproducibilidad exacta.

**Salida:** planes sin reemplazos inesperados, lista de prerrequisitos y orden de aplicación por proveedor.

### Fase C — aplicar solo cambios aprobados

- AWS: aplicar únicamente el Change Set revisado de la pila principal; evitar crear una segunda VPC con el módulo `demo`.
- Azure: aplicar cada raíz requerida después de comparar plan y estado; importar recursos preexistentes cuando corresponda.
- No crear la VPN AWS administrada salvo que la cuenta permita los permisos requeridos. El diseño actual de respaldo es Tailscale autogestionada; no equivale a Site-to-Site administrada ni usa BGP.
- Conservar el estado, llaves de cifrado, secretos y respaldos que se necesiten para recuperación. No sincronizar secretos a Git.

**Salida:** identificadores y estados de despliegue verificados en ambas consolas, con evidencia fechada.

### Fase D — pruebas funcionales y de resiliencia

1. **Portal y perímetro:** HTTPS, certificado, DNS existente sin alterarlo, WAF, listener y destinos saludables del ALB; login, permisos y endpoints por rol.
2. **Base y carga:** comprobar Multi-AZ/retención real, conexiones y consultas. Generar carga gradual y registrar latencia p50/p95/p99, errores, CPU/conexiones de RDS y actividades del ASG; demostrar 2→3→4→5 si la capacidad y las alarmas lo permiten. No presentar una prueba corta como garantía de 3,000 usuarios.
3. **Evento AWS→Azure:** desde la aplicación AWS, enviar un pedido/evento sintético por la ruta privada. Usar un `event_id` único y confirmar respuesta autenticada de Function, mensaje en Queue, efecto idempotente en ledger/Blob y traza en Application Insights.
4. **VPN propia:** validar rutas ida/vuelta y endpoint privado; detener solo el router principal durante una ventana de prueba y medir el tiempo de conmutación al respaldo; restaurar el principal y comprobar retorno. Si no conmuta, restaurar servicio y dejar el resultado como fallo medido; no prometer recuperación en 5 segundos sin dato.
5. **Recuperación entre nubes:** programar exportación PostgreSQL cifrada a Blob con retención; verificar cifrado, integridad y fecha; restaurar una copia reciente en entorno aislado y validar tablas. No sobrescribir producción durante esta prueba.
6. **Región secundaria:** si presupuesto y permisos lo permiten, levantar un piloto ligero reproducible (plantilla, artefacto, secretos y copia de base); probar restauración y procedimiento DNS en un nombre de prueba, no en el dominio compartido.

**Salida:** capturas/IDs, comandos sin secretos, métricas, hora, resultado, limitaciones y costos incrementales.

### Fase E — cierre y limpieza controlada

- Crear respaldo y confirmar que se puede leer/restaurar antes de destruir cualquier entorno temporal.
- Comparar recursos activos con el manifiesto IaC; eliminar solo recursos etiquetados y pertenecientes al proyecto cuya recreación se haya verificado.
- Medir costo final y revisar que no queden recursos de cómputo/gateways de prueba. No afirmar “costo cero” solo porque el laboratorio terminó.
- Actualizar el registro operativo y comparar el diagrama esperado con la evidencia real; marcar cada componente como `confirmado`, `fallido` o `pendiente`.

## Límites y decisiones explícitas

- Azure Functions es serverless en Azure y puede conservar el procesamiento WMS. Si la rúbrica exige AWS Lambda de forma explícita, Functions no sustituye ese requisito; no se añadirá Lambda/SQS solo para duplicar el flujo sin validar primero la rúbrica y los permisos/costo.
- Tailscale es una VPN overlay autogestionada, no una VPN Site-to-Site AWS/Azure administrada, y no aporta BGP por sí sola.
- La ruta privada, failover de routers, ASG bajo carga, exportación/restauración automática y recuperación regional requieren nuevas pruebas cloud. El smoke con Moto no las simula.
- DNS/Cloudflare está fuera de estas raíces y es compartido: no se cambia durante la preparación.

## Archivos y verificación local

- AWS: `iac/cloudformation/aws-lab.yaml`, `iac/cloudformation/README.md` y `iac/cloudformation/lifecycle.sh`.
- Azure: `iac/environments/azure-rebuild/` y las raíces privadas/routers documentadas en `iac/README.md`.
- Diagrama esperado: `iac/architecture/cambios-esperados.svg` y `iac/architecture/cambios-esperados.drawio`.
- Pruebas locales: `python -m unittest discover -s tests/iac -v`; emulador: `iac/local-emulator/README.md`.

Este plan no autoriza ni ejecuta cambios cloud, destrucción, DNS, cambios de IAM ni publicación al repositorio remoto.
