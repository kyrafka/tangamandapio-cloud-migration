# Estado cloud — 27/10/2026, 17:05 America/Chicago

Lecturas puntuales hechas con AWS CLI y Azure CLI/ARM. No se imprimieron ni
guardaron claves. El token temporal AWS autenticó por STS en la cuenta
`654654388734`. Este reporte no constituye una prueba de carga ni una
revisión formal de la rúbrica.

## AWS — portal

- CloudFormation `tangamandapio-live-20261026`: `UPDATE_COMPLETE`.
- `https://tangamandapio.kendellnm.me/health`: HTTP 200 (0.75 s en esta
  consulta).
- ASG `tangamandapio-asg`: mínimo 2, deseado 2, máximo 5; las dos instancias
  aparecen `InService` y `Healthy`.
- Target Group: ambos destinos aparecen `healthy` en el puerto 8080.
- RDS `tangamandapio-postgres`: `available`, `db.t3.micro`, cifrada,
  Multi-AZ y retención automática de 7 días.
- WAF regional `tangamandapio-alb` aparece asociado al ALB.
- `aws sqs list-queues` no encontró colas en esta cuenta/región. La consulta de
  Lambda no encontró funciones del proyecto con prefijo `tangama`.

Esto confirma salud del corte actual y redundancia de RDS, pero no demuestra
que el ASG escale de 2 a 3 ni que soporte 3,000 usuarios. Una prueba anterior
reportó p95 de 8.6 s con la base de datos como cuello de botella; no se repitió
carga en esta verificación.

## Azure — WMS

- Suscripción: Azure for Students, estado `Enabled`.
- Function Flex `tangama-wms-flex-261013`, grupo
  `rg-tangamandapio-rebuild-wus`, estado ARM `Running`.
- Tiene siete funciones: inventario demo, estado de cumplimiento, health,
  estado de poison queue, worker de cola, recepción de evento y actualización
  del catálogo demo.
- Terraform `azure-flex-private` terminó con plan `No changes`; pruebas mock
  3/3 y `validate` pasaron durante la aplicación verificada. La Function usa
  identidad administrada y acceso a Blob/Queue.
- Azure asignó un Private Endpoint en `10.20.1.4`; DNS privado está configurado
  para el hostname de la Function y enlazado con la VNet del proyecto.
- ARM confirma `publicNetworkAccess=Disabled`. La URL pública de health devuelve
  HTTP 403, resultado esperado tras cerrar el ingreso público.
- Antes de cerrar el acceso público se probó el flujo sintético: recepción de
  `purchase.received` → `queued` → `demo_restock_completed`; el saldo demo
  cambió de 24 a 25 y el duplicado fue aceptado sin volver a cambiarlo. Esto
  prueba el ledger ficticio e idempotencia, no un ERP/WMS comercial.
- La Function Y1 anterior `tangama-wms-261008` sigue respondiendo health 200 y
  se mantiene para continuidad. No se cambió el endpoint configurado en AWS ni
  se hizo cutover a Flex.
- Artefacto publicado:
  `artifacts/azure_function_package-aff605e3b204cfceaedc422534501d510d02fb1725e151db0db65c2a30d8085b.zip`
  SHA-256: `aff605e3b204cfceaedc422534501d510d02fb1725e151db0db65c2a30d8085b`.

## Brechas abiertas

1. **Conectividad privada AWS–Azure:** no existe túnel ni ruta entre VPC y VNet.
   AWS Academy denegó `ec2:CreateCustomerGateway`; no se intentó eludir la SCP.
   Por eso la Function Flex privada aún no es consumible desde AWS.
2. **SQS + Lambda + DLQ en AWS:** no están desplegados para el proyecto. Las
   políticas de laboratorio deniegan crear/pasar un rol IAM de ejecución con
   mínimo privilegio; no se reutilizó el rol amplio `LabRole`.
3. **Identidad:** Entra ID/SSO y MFA corporativo no están integrados.
4. **Recuperación entre nubes:** faltan copia automática de datos/respaldos a
   la otra nube y una restauración cruzada medida.
5. **Escalado:** ASG se encuentra en 2/5; falta corregir/medir el camino de
   base de datos y observar una expansión automática 2→3.
6. **Prueba integrada:** falta una solicitud iniciada en AWS que llegue por
   red privada al WMS Flex, con correlación del mismo evento en ambos lados.

No se modificó Cloudflare, el dominio, credenciales de aplicaciones ni ningún
recurso AWS en este corte. El despliegue Azure descrito ocurrió antes de esta
revalidación; aquí solo se consultó el estado.
