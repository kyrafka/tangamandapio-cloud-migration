# Revalidación de release v18 — 16/10/2026, 00:45 UTC

## Resultado ejecutivo

Se publicó el release `20261015-outbox-pagination-v18-python312` en el artefacto
privado de S3 y CloudFormation terminó `UPDATE_COMPLETE` a las 00:42:53 UTC. El
artefacto mide 301,698 bytes, usa SSE-S3 y su SHA-256 es
`c629ab0e7b07c007cfa74c3eca1b9879c601829f44ad3471615cb85e3e09197f`.

La vista administrativa de WMS ahora pagina el historial y concilia el total
completo del tablero: respuesta JSON de arreglo compatible con consumidores
anteriores, metadata `X-Total-Count`/límite/desplazamiento, controles accesibles
de página y orden estable por fecha e ID. El índice de ese orden se añade por
migración idempotente tanto en SQLite como en PostgreSQL.

El gate local aprobó 209 pruebas, build frontend, auditoría de dependencias y
validación CloudFormation. Las suites dirigidas quedaron en 26 pruebas del
portal, 28 del smoke cloud y 15 de empaquetado AWS. La suite de reconciliación
prueba dos páginas de 30 + 15 eventos, total 45, sin duplicados ni omisiones.

## Estado observado después del despliegue

- Inmediatamente después de `UPDATE_COMPLETE`, el ASG quedó con 2 instancias
  `InService`; el target group mostró 2 sanos y 1 destino anterior en `draining`.
- El dominio y `/platform` devolvieron HTTP 200 en la primera comprobación.
- Una comprobación posterior mostró HTTP 503 para `/health`, `/ready` y
  `/platform` al conectar directamente al origen HTTPS del ALB; la respuesta
  llevaba `Server: awselb/2.0`. El dominio con proxy también devolvió 503.
- En esa misma ventana AWS Academy aplicó una denegación explícita
  `voc-cancel-cred` a consultas CloudFormation/ELB y a `ssm:SendCommand`. Por
  ello no se pudo determinar si el laboratorio se apagó, si se perdieron los
  destinos sanos o cuál fue la causa del 503. No se hicieron más llamadas AWS
  tras la denegación.
- El smoke autenticado dirigido al dominio HTTPS obtuvo 403 en el login antes
  de crear ventas o compras. Una segunda ejecución de solo lectura contra la
  instancia fue rechazada por `ssm:SendCommand`; no se reintentó. No hubo
  escrituras de negocio en estas pruebas fallidas.
- Azure Function `/api/health` respondió HTTP 200. El CLI de Azure no pudo leer
  sus metadatos en esta sesión; no se afirma el estado administrativo.

Por tanto, el cambio de paginación está desplegado y aprobado localmente, pero
la disponibilidad del portal y la paginación autenticada en nube quedan sin
confirmar al cierre de este corte. No se declara el release v18 operativo de
extremo a extremo.

## Qué sí está probado del comportamiento sintético

Antes del v18, el E2E v17 por ALB HTTPS creó una venta sintética, completó la
recepción de compra por Azure y reconcilió el ledger demo de 10 a 10. Esto
demuestra un flujo de inventario ficticio funcional, no stock físico de una
empresa. El historial del 15/10 también mostró 45 eventos entregados. Esa
evidencia previa no sustituye una repetición contra v18.

## Próximo paso necesario

Con una sesión de laboratorio AWS activa y permisos restaurados: comprobar
CloudFormation y target health, ejecutar `/health` y `/ready`, completar un
smoke sintético autenticado por el origen HTTPS, verificar las dos páginas del
outbox contra el total del tablero y volver a revisar drift. No intentar sortear
la denegación IAM ni repetir el smoke de escritura hasta que SSM esté autorizado.
