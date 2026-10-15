# Revalidación de módulos ERP y cola poison — 15/10/2026, 23:45 UTC

## Prueba remota controlada

Se ejecutó el modo `admin-modules` del smoke autenticado desde una instancia
EC2 hacia el portal por el origen ALB HTTPS. Resultado:

| Componente | Resultado comprobado |
|---|---|
| Azure poison queue | Endpoint autenticado respondió `ok`; conteo aproximado 0. No se leyeron ni modificaron mensajes y la API confirmó que no expone payloads. |
| Finanzas | Se creó una cuenta por pagar sintética de S/ 0.05, se liquidó como `paid` y se volvió a consultar para verificar persistencia en el portal. |
| Correo interno | `smtp_configured=false`, transporte `portal_only`. Admin envió un mensaje sintético al buzón Comercial; apareció en Enviados y en la Bandeja del destinatario, que pudo marcarlo como leído. No hubo SMTP ni salida a Internet. |
| Resumen y outbox | Admin reportó 1 pedido, 0 pendientes y 45 entregados. La lista de pedidos mostró el único pedido; la vista de outbox devuelve como máximo 30 filas y las 30 recientes estaban entregadas. El agregado no queda conciliado exhaustivamente con las 45 porque la API pagina/limita la lista. |
| Alertas | SNS está configurado; hay 2 suscripciones confirmadas y 0 pendientes. La prueba fue de lectura: no se disparó alarma ni se envió correo. |

Los resultados fueron `LIVE_ADMIN_MODULE_SMOKE_PASSED` y
`LIVE_ADMIN_READONLY_SMOKE_PASSED`. La clave de Azure se obtuvo en memoria
desde el secreto referido por CloudFormation; no se imprimió ni guardó en esta
evidencia. El test no cambió la configuración de la cola y no intentó enviar
correo externo.

La cuenta por pagar es una operación funcional del ledger demo, no una
transferencia bancaria ni un asiento contable legal. El correo queda dentro del
portal; la entrega SMTP externa no está configurada ni probada.

## Validación local

- Suite específica del smoke cloud: 26 pruebas aprobadas.
- Quality gate completo: 205 pruebas unitarias, compilación frontend,
  validación CloudFormation y auditoría de dependencias aprobadas.
- Terraform no se ejecutó en este quality gate; no hubo `plan` ni `apply`.
- Las comprobaciones fueron de aplicación y API: no constituyen una prueba
  visual autenticada en Chrome, prueba de entrega SMTP, carga representativa,
  escalado automático, WebRTC ni conectividad privada AWS–Azure.

No se incluyen credenciales, claves de función, identificadores de usuario,
referencias de documentos ni contenido del mensaje en el registro de salida.
