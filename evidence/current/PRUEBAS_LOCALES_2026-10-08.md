# Resultado de pruebas locales — 08/10/2026

Este primer resultado registra una ejecución anterior: **58 pruebas aprobadas,
0 fallidas**. La sección posterior “Actualización de la puerta profesional”
registra la ejecución más nueva (59/59). Para inventario cloud vigente,
consulta [MAPA_ESTADO_ACTUAL_2026-10-08.md](MAPA_ESTADO_ACTUAL_2026-10-08.md).

| Suite | Resultado | Cobertura principal |
|---|---:|---|
| `app/tests` | 22 aprobadas | Salud, pedidos, autenticación, aislamiento por empresa, cabeceras y contrato Azure simulado. |
| `app/azure_function_tests` | 14 aprobadas | Checksum, deduplicación, validación SKU/cantidad, descuento idempotente con lease, rechazo atómico, eventos históricos sin líneas y bindings HTTP/Queue. |
| `app/aws_release/tests` | 22 aprobadas | Ciclo de usuarios, permisos, grabaciones S3 simuladas, TURN efímero, outbox/WMS, pedido SKU/cantidad durable y consola de plataforma/CloudWatch simulado. |

Puerta reproducible:

```powershell
.\tests\run_local_quality.ps1
```

La puerta ahora ejecuta las tres suites (antes solo corría `app/tests`), compila
Python y construye el frontend si `pnpm` y las dependencias locales están
instaladas. El build Vite terminó correctamente y emitió `app/src/static`.

Validaciones IaC ejecutadas aparte, sin credenciales ni `apply`:

```powershell
tools\terraform-1.16.0\terraform.exe fmt -check -recursive iac\modules\aws_network
tools\terraform-1.16.0\terraform.exe fmt -check -recursive iac\modules\azure_operations
# init -backend=false -upgrade y validate en iac/environments/demo y azure-demo
app\.venv\Scripts\cfn-lint.exe iac\cloudformation\aws-lab.yaml iac\cloudformation\voice-recordings.yaml
```

Terraform validó ambos entornos. En esa corrección también se reparó el módulo
`demo`: su llamada opcional a Azure no pasaba `key_vault_name` ni
`function_package_path`; los parámetros existen ahora y solo se exigen cuando
`enable_azure=true`. `cfn-lint` terminó sin errores. `init` descargó/resolvió
proveedores localmente; no creó ni modificó recursos cloud.

Estas pruebas son locales y aisladas. No prueban permisos de cámara/micrófono,
llamadas WebRTC entre dos redes, recursos vivos de AWS/Azure, un ERP/WMS real ni
una restauración de backups. Las simulaciones se identifican explícitamente en
el código y la interfaz.

El despliegue WMS intentado el 08/10 no quedó confirmado: Zip Deploy no recibió
respuesta de SCM/Kudu. En una revisión posterior del mismo día, `/api/health`
respondió `200`; la nueva ruta `/api/wms/inventory` y el descuento de stock no
se revalidaron en Azure. El ledger de inventario probado en estas suites es
local/sintético, no stock vivo.

En aquella revisión, AWS `/health` respondió `200` con `database=ok`, AWS
`/platform` devolvió `404`, Azure `/api/health` respondió `200` y
`/api/wms/inventory` devolvió `404` sin clave; Azure CLI mostró la suscripción
habilitada y AWS STS rechazó el perfil local. El registro se conserva como
histórico y fue superado por el corte cloud de 21:26 UTC descrito en
`CIERRE_NUBE_2026-10-08.md`.

## Actualización de la puerta profesional — 08/10/2026

Ejecución local posterior: **59 pruebas aprobadas, 0 fallidas** (22 API base,
14 Azure Functions, 23 release AWS). `tests/run_local_quality.ps1` terminó con
`QUALITY_GATE=APROBADA`; incluye auditoría de dependencias Python, validación
CloudFormation, build frontend aislado y auditoría de producción pnpm.

- Frontend: `pnpm install --frozen-lockfile`, `pnpm run build:check` y
  `pnpm audit --prod --audit-level high` pasaron. El build se guardó en
  `app/web/dist`; no se tocó `app/src/static`. La auditoría identificó y se
  corrigió `source-map-js` 1.2.1→1.2.2; no quedan alertas altas reportadas.
- Python: `app/requirements-ci.lock` reúne los tres manifiestos de ejecución y
  las herramientas CI en versiones exactas con hashes. `pip-audit` no encontró
  vulnerabilidades conocidas en ese conjunto. El workflow instala con
  `--require-hashes`; el lock se regenera y revisa al cambiar los manifiestos.
- CloudFormation: `cfn-lint` pasó en `aws-lab.yaml` y `voice-recordings.yaml`.
- Terraform: `fmt -check`, `init -backend=false -lockfile=readonly` y
  `validate` pasaron en `demo` y `azure-demo`. No hubo `apply` ni cambios a
  recursos.
- Rendimiento: 50 solicitudes GET a `http://127.0.0.1:8080/health`, concurrencia
  5, cero errores, p95 345.66 ms (umbral 2000 ms). Es una muestra local corta,
  no una prueba de escalado cloud.
- CI: agregado `.github/workflows/quality-gate.yml` con permisos de lectura,
  acciones fijadas por SHA, tests y validaciones de ambas nubes, auditoría y
  smoke test. También `.github/dependabot.yml`. No se ejecutó en GitHub desde
  esta sesión y aún no está activo hasta subir los archivos al remoto.

Esta actualización es de código y evidencia local; no inicia el laboratorio,
no usa credenciales cloud y no modifica AWS ni Azure. Las pruebas no demuestran
WebRTC A/V entre dos redes, todas las vistas del portal en navegador, inventario
real de negocio ni alarmas cloud recuperadas.
