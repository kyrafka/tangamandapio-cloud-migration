# Confirmación de estado y correlación Azure — 16/10/2026, 10:41 UTC

## AWS: no es un perfil CLI alternativo

- `aws configure list --profile default` confirma que las credenciales vienen
  de `shared-credentials-file`; no hay variables AWS de clave/token que las
  sustituyan en el entorno.
- STS sigue identificando la cuenta de laboratorio `841113066612`, pero
  `elbv2:DescribeLoadBalancers` continúa con `AccessDenied`. No se intentó una
  acción mutante.
- El dominio HTTPS público sigue en HTTP 503. El último acceso directo al ALB,
  con verificación TLS exitosa, recibió `Server: awselb/2.0` y HTTP 503. No se
  puede consultar el estado de targets para precisar la causa interna.

## Azure: resultados confirmados por Application Insights

Sin repetir el smoke, una consulta de `traces` en Application Insights encontró
las líneas de encolado y resultado para los dos IDs sintéticos creados a las
10:32 UTC:

| Evento | Encolado UTC | Resultado UTC |
|---|---:|---:|
| `evt-c9131f1e86ef4f60ab56716301617d73` | 10:32:09 | `demo_fulfillment_completed` a 10:32:43 |
| `evt-cb1a5ef3317247bdba3fc2f6711d3930` | 10:32:45 | `demo_restock_completed` a 10:32:47 |

Esto confirma que los dos mensajes alcanzaron el consumidor Azure. El smoke
comprobó además el saldo demo restaurado y poison queue vacía antes/después.
El productor era el artefacto local/SQLite, no EC2 ni RDS. Los registros
sintéticos quedan en el historial de Azure por diseño.

## Impacto para el cierre

Azure está activo y su Terraform normal no propone cambios; el portal AWS
permanece caído y el adaptador ICE de la nueva release no está desplegado. El
siguiente avance AWS requiere que la política del laboratorio vuelva a permitir
lecturas de ELB/CloudFormation/SSM y que el ALB vuelva a tener respuesta útil.
