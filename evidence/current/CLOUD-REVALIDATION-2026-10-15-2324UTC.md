# Revalidación cloud v17 — 15/10/2026, 23:21–23:24 UTC

## Resultado

CloudFormation `tangamandapio-live-20261013` terminó `UPDATE_COMPLETE` tras el
despliegue gradual v17. El cambio actualizó el launch template/ASG y las
referencias de artefacto en observabilidad y escalado; no reemplazó RDS. Una
detección posterior terminó `IN_SYNC` con cero recursos desviados.

El paquete activo es `20261015-dashboard-health-card-v17-python312`, SHA-256
`f2a4f3b8b58fae62529d27842c8422cc0c408f189efbef8956125f2e3891c8fa`. Se
publicó en el bucket privado de releases con SSE-S3. El cambio corrige el
indicador de salud del panel para reflejar el estado agregado expuesto por
`/health`, sin publicar el estado de dependencias internas.

## Comprobaciones vivas

| Comprobación | Resultado |
|---|---|
| Dominio `tangamandapio.kendellnm.me` por HTTPS/TLS confiable | HTTP 200 |
| `/health`, `/ready` y bundle JS v17 | HTTP 200 |
| HTTP sin TLS | 301 a HTTPS |
| Grupo de Auto Scaling | 2 deseadas, 2 `InService` sanas, máximo 5 |
| Destinos ALB | 2 `healthy`; un destino sustituido en drenaje durante limpieza |
| RDS | `available`, privada y cifrada; Single-AZ, 1 día de backup |
| Azure Function `tangama-wms-261008` | `Running`, HTTPS-only; `/api/health` HTTP 200 |
| Drift CloudFormation posterior al despliegue | `IN_SYNC`, 0 recursos desviados |
| GitHub Actions para `a257a71` | 3 jobs `success` |

## Prueba funcional AWS→Azure

Una ejecución única del smoke autenticado desde una EC2, a través de
ALB-origen HTTPS, terminó `LIVE_E2E_PASSED`:

- Catálogo QA sintético importado correctamente.
- Venta: `completed_demo`; reposición/recepción: `received_demo`.
- Dos eventos outbox fueron entregados a Azure.
- Azure funcionó en modo `demo-inventory-ledger`; saldo sintético volvió de 10
  a 10. No representa existencias físicas.
- Comercial pudo registrar ventas y Operaciones consultar outbox/inventario;
  sus intentos de acceso a rutas administrativas devolvieron 403. Admin tuvo
  acceso a esas rutas.
- 24/24 lecturas autenticadas a la BD respondieron 200, concurrencia 6,
  p95 208.71 ms. Es una prueba pequeña, no una proyección de 3,000 usuarios.
- SNS mostró dos suscripciones confirmadas y cero pendientes.
- Esta pasada no ejercitó Finanzas, el buzón interno/relay SMTP ni una ruta de
  fallo/reintento hasta poison queue. El quality gate local cubre el flujo de
  Finanzas y un SMTP de prueba en memoria; eso no demuestra entrega SMTP externa
  ni poison-message real en Azure.

El smoke deja eventos sintéticos de auditoría y puede crear o reutilizar los
registros de prueba `SKU-QA-V10-20261014` y su socio QA. La cantidad del ledger
quedó compensada en su línea base.

## Pendiente para completar la rúbrica y la verificación del proyecto

- Red privada AWS–Azure (VNet/VPN/rutas; el preflight anterior quedó bloqueado
  por una denegación SCP de AWS Academy).
- RDS Multi-AZ/failover y una política de backup más larga; ya existe una
  restauración aislada probada (RTO medido 260 s, RPO superior observado 8 s).
- WAF y prueba de seguridad independiente.
- Prueba de escala/autoescalado representativa; no se ha probado carga de 3,000
  usuarios.
- Recorrido visual autenticado en Chrome, incluyendo CSV, vistas por rol,
  Finanzas y correo interno.
- Ejercitar en Azure un fallo recuperable, sus reintentos, el envío a poison
  queue y el procedimiento de inspección/reproceso. Los tests locales verifican
  la política, pero este corte solo validó el camino exitoso.
- Validar entrega por un relay SMTP real si se quiere correo fuera del buzón
  interno del portal. El adaptador SMTP pasó contra un servidor de prueba local;
  no hay evidencia de relay externo configurado/probado en la nube.
- Llamada WebRTC con dos navegadores reales ahora que hay HTTPS confiable.
- Capturas actuales de consola AWS, monitor Azure y evidencia de alarmas/
  recuperación para la sustentación; medir Cost Analysis real de Azure/AWS.

El WMS es funcional como flujo de demostración con datos sintéticos y Azure
procesa los eventos; no es un WMS físico conectado a inventario real. Esta
revalidación no afirma que se hayan cerrado los pendientes anteriores.
