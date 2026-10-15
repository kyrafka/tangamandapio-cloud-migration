# Azure Terraform plan — 14/10/2026

## Revalidación más reciente — 08:14–08:15 America/Chicago

Terraform 1.16.0 ejecutó un plan normal de solo lectura para
`iac/environments/azure-rebuild`, usando `rebuild.tfvars.example` y el archivo
local ignorado `alert-recipients.local.tfvars`. El plan consultó ARM y terminó
con salida 0:

```text
No changes. Your infrastructure matches the configuration.
```

No se guardó un plan aplicable, no se ejecutó `apply` y no se modificó Azure.
Esto reconcilia el root `azure-rebuild` con el estado remoto en este corte, no
los recursos AWS ni una conexión privada AWS–Azure. La confirmación del usuario
sobre recepción de alerta y recuperación se refiere a la prueba SNS de AWS; no
se usa como evidencia de entrega Azure.

## Revalidación más reciente — 07:16–07:18 America/Chicago

Azure CLI confirmó la suscripción `Azure for Students` como `Enabled`; ARM
mostró `rg-tangamandapio-rebuild-wus` en `Succeeded` con diez recursos,
incluida `tangama-wms-261008`. Su endpoint `/api/health` respondió HTTP 200
con `status=ok`. Esto no prueba una invocación de fulfillment.

Una segunda lectura de Azure confirmó el grupo `Succeeded` y `/api/health`
volvió a responder 200. Terraform 1.16.0 volvió a ejecutar un plan normal contra el root
`iac/environments/azure-rebuild`, con `rebuild.tfvars.example` y el archivo
local ignorado `alert-recipients.local.tfvars`. Resultado: `No changes. Your
infrastructure matches the configuration.` (salida 0). No se guardó un plan
aplicable, no se ejecutó `apply` y no se modificó Azure. No se probó la entrega
de alertas en este corte.

## Revalidación del state — 04:30–04:31 America/Chicago

Se ejecutó un plan normal con Terraform 1.16.2, `-detailed-exitcode` y
`rebuild.tfvars.example`. Terraform refrescó los recursos administrados en
Azure Resource Manager y finalizó con salida 0:

```text
No changes. Your infrastructure matches the configuration.
```

No se guardó un plan aplicable, no se ejecutó `apply` y no hubo cambios de
infraestructura. El state continúa local e ignorado por Git; este resultado
reconcilia el root Terraform `azure-rebuild` con ARM en este corte, pero no
prueba conectividad privada ni despliegue comercial del WMS.

## Revalidación adicional — 02:50:40–02:51:38 America/Chicago

Se repitió un plan normal de solo lectura con Terraform 1.16.0 y
`rebuild.tfvars.example`; resultado `No changes`, salida 0. No se guardó un
plan aplicable, no se ejecutó `apply` y no cambió la infraestructura.

## Resultado — 01:44 America/Chicago

Se comprobó en modo lectura la configuración `iac/environments/azure-rebuild`
contra la suscripción activa **Azure for Students**. `az account show`
confirmó que la cuenta está `Enabled`; el identificador de suscripción del
state local coincide con el de la sesión activa. El state contiene 20 recursos
y está ignorado por Git.

Terraform 1.16.2 validó la configuración (`terraform validate`: correcto) y
ejecutó un plan normal con `rebuild.tfvars.example`. ARM no reportó diferencias:

```text
No changes. Your infrastructure matches the configuration.
TERRAFORM_PLAN_EXIT=0
```

No se ejecutó `apply`, no se guardó un plan aplicable y no se cambiaron recursos
ni configuración. El plan normal consultó el estado remoto, así que esta
comprobación es más reciente que el timestamp del archivo state local; ese
archivo sigue siendo local y no se debe versionar, copiar ni compartir.

## Alcance

Esto confirma que la infraestructura Azure actual coincide con **este root
Terraform y sus variables de reconstrucción**. No significa que la Function sea
un WMS comercial: procesa el ledger sintético descrito en la evidencia E2E del
14/10. Tampoco prueba VPN AWS–Azure, entrega SMTP externa ni recuperación de
datos. El dominio/HTTPS del portal se habilita en el ALB de AWS y sigue en
espera de un FQDN bajo control del equipo.

No aplicar una destrucción o recreación de este root para cerrar HTTPS; el TLS
del portal no requiere cambios en Azure.
