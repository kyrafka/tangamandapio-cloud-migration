# Revalidación cloud y calidad — 15/10/2026, 18:56 UTC

Este corte registra pruebas nuevas ejecutadas desde la sesión actual. No se
desplegó código ni infraestructura en AWS; la única escritura cloud fue una
prueba con eventos e inventario sintéticos en Azure, con compensación del saldo.

## AWS

- `sts get-caller-identity` autenticó en la cuenta Academy `841113066612`.
- El E2E AWS→Azure se detuvo antes de enviar un comando o escribir datos:
  `ssm:DescribeInstanceInformation` recibió `AccessDeniedException` por la
  política explícita `voc-cancel-cred`.
- La consola mostró el stack `tangamandapio-live-20261013` estable y en
  `IN_SYNC`; el grupo de destino tenía 2/2 instancias saludables.
- El bucket de artefactos contiene el release v12
  (`20261015-login-drawer-a11y-v12-python312`, SHA-256
  `c884314dd8ec617df90739aeee25d2f912d7e1d70ec1e66d442fbc6720407c13`). No se
  encontró el artefacto local v13 en el prefijo de releases; v13 no está
  desplegado. No se intentó eludir la denegación para subirlo.

## Azure

- Azure for Students figura `Enabled`; la prueba llegó a la Function
  `tangama-wms-261008`, que reportó `Running` y HTTPS-only.
- `tests/run_live_azure_erp_smoke.py` terminó `LIVE_E2E=PASSED`: comprobó el
  modo `demo-inventory-ledger`, validó los guardas de ingreso (401 sin clave y
  400 para fuente no autorizada), recorrió venta → outbox → Queue/Function →
  conciliación y realizó la recepción compensatoria. El saldo sintético volvió
  a su línea base. Los eventos de prueba quedan en la auditoría de Azure; no se
  usaron existencias físicas.
- Esta prueba ejecutó el release AWS local contra Azure; **no** ejecutó el
  portal desde las EC2 ni demuestra el salto AWS privado→Azure.

## Calidad local e IaC

- `tests/run_local_quality.ps1`: aprobado, 181 pruebas unitarias; incluye API
  base (64), Azure Functions (31), release AWS (46), guardas/suites cloud mock,
  carga transaccional aislada (40/40), build frontend, auditorías y
  CloudFormation. Los auditores reportaron cero vulnerabilidades conocidas.
- Node: 8 pruebas de permisos/navegación y 6 de importación CSV aprobadas; build
  Vite de producción aprobado.
- Terraform: `fmt -check`, `validate` en seis roots y cinco pruebas mock de
  compuertas de costo/red aprobadas. No se ejecutó `apply`.
- El ZIP de Azure se verificó contra el código local y su SHA-256 fijado.

## Pendiente

- La pestaña HTTPS del portal sigue en el formulario de inicio de sesión. La
  inspección de las vistas privadas y las pruebas visuales por rol esperan que
  el usuario complete ese paso en Chrome; no se ingresaron credenciales.
- Repetir el E2E desde AWS cuando la sesión/rol permita SSM. El rechazo actual
  es una denegación IAM explícita, no un token AWS inválido.
- Publicar y desplegar v13 requiere permiso de escritura AWS y una revisión del
  cambio antes de actualizar CloudFormation. HTTPS está operativo en el release
  v12.

No se guardaron credenciales, contraseñas ni claves de Function en este informe.
