# Revalidación AWS en vivo — 2026-10-16 01:37 UTC

## Resultado

El token temporal nuevo quedó en el perfil local `default`. Se verificó que su
identificador coincidiera con el recibido, sin imprimir ni guardar las claves en
esta evidencia. STS autenticó la cuenta `841113066612` con el rol de laboratorio
`voclabs`. Las consultas de inventario AWS funcionaron.

La infraestructura HTTPS está presente, pero el portal no está operativo en
este corte. La URL pública `https://tangamandapio.kendellnm.me/health` respondió
HTTP 503.

## Estado observado

| Componente | Evidencia del 16/10 UTC | Evaluación |
|---|---|---|
| CloudFormation | `tangamandapio-live-20261013`, `UPDATE_COMPLETE` (última actualización 00:27:59 UTC) | Stack aplicado; no prueba salud de la aplicación |
| ALB | `tangamandapio-alb`, `active`, `internet-facing` | Existe y responde a nivel de balanceador |
| HTTPS | Listener 443 HTTPS; listener 80 redirige a 443 | TLS configurado en el ALB |
| Target group | Puerto 8080, health check `/health`, cero destinos registrados | Sin backend saludable |
| ASG | `tangamandapio-asg`, mínimo/deseado 2, máximo 5; cero instancias | Capacidad deseada no satisfecha |
| Lanzamientos EC2 | Intentos recientes terminan como `Client.InternalError: Client error on launch` | Causa raíz aún no identificada |
| AMI y tipo | AMI `ami-097855b862d5b1eb2` disponible; `t3.micro` ofrecido en `us-east-1a/b` | No apunta a AMI inexistente ni tipo no ofrecido |
| Subredes del ASG | Ambas disponibles, 251 IP libres cada una | No hay evidencia de agotamiento de IP |
| RDS | `tangamandapio-postgres`, `available`, Single-AZ, retención 1 día | Base accesible en AWS; no ofrece redundancia Multi-AZ |

Los últimos eventos de escalado consultados (01:20 UTC) reportan que las
instancias no alcanzan `InService` y se terminan con `Client.InternalError`.
CloudTrail muestra solicitudes `RunInstances` aceptadas desde Auto Scaling,
pero no registra un error API que explique la terminación. La salida de consola
de las instancias consultadas está vacía. Por lo tanto, aún no se puede atribuir
el fallo a la aplicación, la AMI, la red o una cuota del laboratorio.

## Diagnóstico adicional — 01:44 UTC

- El objeto del release v18 existe en el bucket privado (301,698 bytes); su
  clave y digest coinciden con los parámetros vivos y con el paquete que genera
  la puerta local.
- El Launch Template v18 usa `t3.micro`, AMI disponible, perfil
  `LabInstanceProfile` y dispositivo raíz `/dev/xvda` correcto. El tipo se ofrece
  en ambas zonas usadas por el ASG.
- Las subredes están disponibles con 251 IP libres cada una. Ambas enrutan al
  NAT `available`; la subred del NAT tiene ruta activa al Internet Gateway.
  Esto reduce la probabilidad de falta de espacio de red o de salida, pero no
  demuestra que el bootstrap de cada instancia se completara.
- `RunInstances` y la asunción del rol por EC2 aparecen aceptados en CloudTrail;
  no se encontró código/mensaje de error de API. No hay streams de la aplicación
  para las últimas instancias fallidas.
- Una sonda directa HTTPS al ALB, con Host del dominio y omitiendo únicamente la
  comprobación de nombre del certificado del hostname AWS, también devolvió
  503. La URL del dominio con validación TLS normal devolvió 503.

La falla sigue sin causa raíz confirmada. No se cambia AMI, tamaño, red ni
capacidad sin logs o una señal del plano de control que justifique la corrección.

CloudFormation drift detection terminó a las 01:49 UTC como `IN_SYNC`; 39
recursos que admiten consulta de drift reportaron `IN_SYNC` y no hubo estados
`MODIFIED`, `DELETED` ni `NOT_CHECKED`. La pila informa 47 recursos (`36
CREATE_COMPLETE`, `11 UPDATE_COMPLETE`). Esto compara configuración declarada
contra recursos compatibles con drift; no valida salud de EC2, targets del ALB,
la aplicación ni la restauración de RDS.

## Recuperación revalidada — 02:10 UTC

El token temporal compartido para esta sesión sí quedó activo en el perfil local
`default`: STS autenticó la cuenta académica `841113066612`. Se repitieron las
consultas después de la recuperación automática del grupo:

| Comprobación | Resultado observado |
|---|---|
| CloudFormation | `UPDATE_COMPLETE`; última actualización registrada `00:27:59 UTC` |
| Auto Scaling | `tangamandapio-asg`, mínimo/deseado 2, máximo 5; dos instancias `InService` y `Healthy` |
| Target group | Dos destinos `healthy` en puerto 8080 |
| Portal HTTPS | `/`, `/health` y `/ready` respondieron HTTP 200 con validación TLS normal |
| RDS | `available`, PostgreSQL, Single-AZ (`MultiAZ=false`), retención de backups de 1 día |

La sesión Chrome ya autenticada como Administrador cargó la consola de
plataforma: CloudWatch mostró solicitudes ALB, latencia p95, dos destinos
saludables, ASG 2/2, PostgreSQL y métricas RDS. WAF aparece como «No desplegado».
El inventario mostró 14 SKU (12 de catálogo y dos de QA); el outbox mostró 45
eventos y la paginación recorrió 30 + 15. La lista de usuarios mostró las tres
cuentas activas tras pulsar «Actualizar usuarios». La primera carga presentó
momentáneamente placeholders y una tabla vacía; la consulta de refresco la
completó, por lo que queda como posible intermitencia de carga que merece una
regresión, no como un bloqueo persistente.

Desde la consola, «Consultar Azure» sobre un evento existente devolvió
`demo_restock_completed` y la UI indicó que la recepción solo afecta el ledger
ficticio. Esto valida en vivo la consulta autenticada desde el portal AWS hacia
el estado guardado en Azure; no es una ruta privada, ni una nueva venta, ni una
prueba de movimiento de inventario real. No se creó ni alteró información de
negocio durante este paso.

## Alcance de esta verificación

- Se actualizaron únicamente las credenciales temporales del perfil local AWS y
  se hicieron lecturas de STS, EC2, Auto Scaling, ELB, CloudFormation, RDS y
  CloudTrail.
- No se modificó ni eliminó ningún recurso cloud.
- En el corte inicial de 01:37–01:49 UTC el portal devolvía 503; la revalidación
  posterior de 02:10 UTC documenta la recuperación y las comprobaciones
  autenticadas que sí se completaron.
- No se aplicaron cambios AWS ni Azure. La lectura web fue de solo lectura y la
  consulta de estado WMS usó el endpoint GET existente.

## Siguiente diagnóstico

Mantener vigilancia de la intermitencia del primer render de la consola y
repetir su carga en una sesión nueva. Antes de cualquier modificación posterior,
revisar el motivo del reemplazo automático de instancias y comparar la plantilla
CloudFormation viva con IaC. No ampliar RDS ni desplegar WAF/VPN sin una decisión
de alcance y costo; la aplicación está disponible en el corte de 02:10 UTC.
