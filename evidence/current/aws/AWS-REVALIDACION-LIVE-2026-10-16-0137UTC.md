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

## Alcance de esta verificación

- Se actualizaron únicamente las credenciales temporales del perfil local AWS y
  se hicieron lecturas de STS, EC2, Auto Scaling, ELB, CloudFormation, RDS y
  CloudTrail.
- No se modificó ni eliminó ningún recurso cloud.
- No se validaron módulos autenticados del portal porque el health check público
  devuelve 503.
- Este resultado supersede cualquier afirmación anterior de que el portal AWS
  estaba accesible en este corte. HTTPS está configurado, pero el servicio web no
  está sano.

## Siguiente diagnóstico

Obtener evidencia adicional del fallo de provisión desde la consola EC2/Auto
Scaling del laboratorio o de AWS Health/Service Quotas, y contrastarla con el
`LaunchTemplate` versión 18 y los eventos del ASG. No cambiar tipo, AMI ni
capacidad hasta contar con una causa verificable. Una vez las instancias queden
`InService` y saludables, repetir health check externo y las pruebas funcionales
del portal.
