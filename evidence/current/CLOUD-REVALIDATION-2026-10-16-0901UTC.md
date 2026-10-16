# Revalidación cloud y matriz ERP — 16/10/2026, 08:53–09:01 UTC

## Servicio e integración

- AWS STS aceptó la sesión en la cuenta `841113066612`. CloudFormation sigue
  `UPDATE_COMPLETE`; el estado de drift más reciente reporta `IN_SYNC`. No se
  aplicó infraestructura en este corte.
- ASG: min/deseado 2, max 5; dos instancias `InService`/`Healthy`. El corte
  anterior (08:46) verificó ambos EBS raíz cifrados. El portal HTTPS `/health`
  respondió 200 y Azure Function `tangama-wms-261008` respondió 200 por HTTPS;
  Azure está `Enabled`, Function `Running` y HTTPS-only.
- E2E por ALB HTTPS: catálogo sintético, venta `completed_demo`, compra
  `received_demo`, dos eventos entregados, ledger ficticio de 10→10 y 24/24
  lecturas HTTP 200 (concurrencia 6, p95 225.67 ms).
- Admin read-only posterior: 61/61 eventos entregados, 0 pendientes,
  conciliación paginada completa y 24/24 lecturas HTTP 200 (concurrencia 6,
  p95 545.86 ms). Comercial y Operaciones conservaron 200/403 esperados; SNS
  tiene dos suscripciones confirmadas y cero pendientes. La alarma no se
  disparó. El p95 de un smoke corto no es benchmark de capacidad.

## Autorización ERP en producción

- Se ejecutaron 48 sondas HTTPS contra los seis perfiles ERP: Admin, Ventas,
  Finanzas, Compras, Datos Maestros y Auditoría. Todos los GET permitidos dieron
  200; las denegaciones dieron 403. Los POST autorizados recibieron 400 por
  payload incompleto, antes de persistir ventas, compras, socios o gastos.
- Para probar cuatro perfiles no presentes como fixtures activos se crearon
  cuatro cuentas QA aleatorias. Las cuatro se desactivaron al terminar y la
  prueba consultó Admin para confirmar `active=false`. Sus filas y auditoría
  quedan retenidas como registros inactivos; las contraseñas aleatorias no se
  imprimieron ni guardaron en Parameter Store.
- El primer intento terminó antes de crear cuentas porque el arnés esperaba un
  objeto y el endpoint devuelve una lista. Se corrigió el lector; los datos de
  SSM confirmaron que ese intento no hizo mutaciones. La segunda ejecución pasó
  48/48 y limpió las cuatro cuentas.

## Compuerta local

`tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 225 pruebas unitarias, 14 Node, 40 transacciones
aisladas, compilación Vite, auditorías de dependencias sin vulnerabilidades
conocidas, validación CloudFormation y Terraform (`fmt`, `init`, `validate` y
pruebas mock de red/costo). Sin cambios ni llamadas de aplicación a la nube
desde esa compuerta.

## Límites y trabajo restante

La matriz es de APIs; no sustituye la inspección visual en Chrome. Siguen sin
probarse WebRTC en dos navegadores y el reintento live tras una falla inducida.
No hay WAF regional, carga sostenida/3,000 usuarios ni failover RDS Multi-AZ;
RDS permanece Single-AZ y con un día de backup según el inventario previo. No
hay VNet de proyecto ni VPN: `CreateCustomerGateway` está bloqueado por SCP
explícita de AWS Academy. El WMS sigue siendo un ledger sintético; no se afirma
inventario físico ni costo Azure atribuible.

No se hizo despliegue de código de aplicación: los cambios del corte son
pruebas, evidencia y documentación. No se tocaron recursos de infraestructura.
