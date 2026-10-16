# Estado vivo AWS–Azure y smoke compensado — 16/10/2026, 10:39 UTC

## AWS: dominio HTTPS arriba, origen portal en 503

- `sts:GetCallerIdentity` aceptó el perfil `default` para la cuenta del
  laboratorio `841113066612`.
- El endpoint público `https://tangamandapio.kendellnm.me/health` respondió
  HTTP 503 desde Cloudflare. La misma ruta al ALB, usando su DNS de origen pero
  conservando el hostname/SNI del dominio, respondió HTTP 503 con TLS válido
  (`ssl_verify_result=0`) y `Server: awselb/2.0`.
- `cloudformation:ListStacks`, `ssm:DescribeInstanceInformation` y
  `elbv2:DescribeLoadBalancers` recibieron AccessDenied por una denegación
  explícita de `voc-cancel-cred`. Por ello no se conoce el estado actual de la
  pila, EC2/ASG, destinos ni RDS; no se intentó modificar recursos.
- El certificado y la ruta HTTPS sí negocian TLS; la aplicación detrás del ALB
  no está disponible. No se afirma que el nuevo adaptador WebRTC esté publicado.

## Azure: Function viva, alertas y E2E sintético

- Azure CLI confirma la suscripción `Azure for Students` como `Enabled`, el
  grupo `rg-tangamandapio-rebuild-wus` como `Succeeded` y la Function
  `tangama-wms-261008` como `Running`, `httpsOnly=true`. Su
  `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió 200.
- Inventario ARM: 10 recursos del proyecto (Function, Storage, Key Vault,
  Log Analytics, Application Insights, plan, dos action groups y dos alertas).
  Las alertas `tangama-wms-fn-5xx` (severity 2) y
  `tangama-wms-fn-latency` (severity 3) están habilitadas.
- El smoke `tests/run_live_azure_erp_smoke.py` pasó ingress 401/400, venta demo,
  consumo de una unidad sintética y recepción compensatoria. El saldo volvió a
  la línea base; la cola poison estuvo vacía antes y después. Los eventos
  sintéticos permanecen intencionalmente en la auditoría Azure.
- IDs de esta corrida: venta `evt-c9131f1e86ef4f60ab56716301617d73`,
  reposición `evt-cb1a5ef3317247bdba3fc2f6711d3930`. El productor fue el
  artefacto local con SQLite temporal; no pasó por la EC2 ni RDS de AWS.
- La consulta de Application Insights de las últimas dos horas mostró 7
  invocaciones de `process_fulfillment_message`, `resultCode=0` y 0 fallos.

## IaC, WebRTC y QA local

- Terraform normal en `iac/environments/azure-rebuild` terminó `No changes`
  (exit 0). `refresh-only` imprimió el mismo texto, pero devolvió exit 2; no se
  guardó ni aplicó un plan. Se registra como discrepancia del comando, no como
  drift confirmado.
- La puerta local más reciente aprobó 230 pruebas unitarias, 40 transacciones
  aisladas, build frontend, auditorías y validaciones IaC. Las 5 pruebas del
  adaptador ICE pasaron también.
- El commit `a136f8b` está publicado en
  `codex/aws-v11-deploy-sync`. El adaptador ICE aún no está desplegado: AWS no
  permite leer estado ni operar el ALB, y el proyecto no configura relay TURN.
  Tampoco se probó audio/video entre dos navegadores reales en este corte.

## Cierre pendiente

Hay que recuperar una sesión/política AWS operativa y consultar targets, ASG,
instancias, RDS y CloudFormation antes de cualquier cambio; luego restaurar el
portal, publicar el artefacto inmutable y repetir las pruebas en la nube. El
`503` se observó de forma directa, pero su causa interna no puede confirmarse
con las acciones AWS actualmente denegadas. Azure no requiere cambios de
infraestructura según el plan normal de este corte.
