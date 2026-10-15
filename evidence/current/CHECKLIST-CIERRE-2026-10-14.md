# Checklist de cierre — corte 14/10/2026, 15:36 America/Chicago

## Comprobado

- [x] AWS CLI autenticó con el token temporal recién entregado; STS confirmó la cuenta académica. El perfil local quedó protegido para el usuario actual; no se copió el token a archivos del proyecto.
- [x] Relectura final 14:52–14:54: STS volvió a aceptar la sesión; CloudFormation siguió `UPDATE_COMPLETE` y una detección nueva terminó `IN_SYNC`; ALB 2/2 sano, ASG 2/2 `InService`, RDS `available`, y `/`, `/health`, `/ready` devolvieron 200. Azure Function `Running`/HTTPS-only y health 200; los dos servidores locales también dieron health 200.
- [x] Cierre posterior a la sonda automática (15:35–15:36): STS sigue válido, ASG 2/2 sano, ambas alarmas Target Tracking en `OK`, ALB `/health` y `/ready` 200, Azure health 200, CloudFormation `UPDATE_COMPLETE` y drift `IN_SYNC` a las 15:36:04.
- [x] CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; detección de deriva actual `IN_SYNC`.
- [x] ALB activo, 2/2 destinos `healthy`; ASG con mínimo/deseado 2, máximo 4 y ambas instancias `InService`.
- [x] SSM de solo lectura confirmó en ambas EC2 release `20261014-synthetic-catalog-v10-python312`, servicio activo y hashes completos idénticos a local para `app.py`, `erp_service.py` y `requirements.lock`.
- [x] RDS disponible, privada, cifrada y Single-AZ, con backup automático de 1 día; IaC y nube concuerdan, aunque la resiliencia/retención son limitadas.
- [x] ALB HTTP: `/`, `/health` y `/ready` responden 200; `/api/admin/users` anónimo responde 401. No hay dominio/HTTPS público comprobado. Este corte supersede el 503 histórico de las 13:11.
- [x] Microprueba de lectura por ALB: 60/60 `/health` dieron 200 con concurrencia 6, p95 447.61 ms y máximo 525.96 ms; targets siguieron sanos. ASG fue 2→2 (min 2, max 4), con tracking CPU 60%; no se forzó escalado.
- [x] Escalado automático real: una sonda CPU auto-limitada de 240 s elevó la alarma Target Tracking de `OK` a `ALARM`; la política cambió el deseado 2→3 y lanzó un tercer EC2, que entró `InService` y quedó `healthy` en ALB. Al terminar la carga, la alarma volvió a `OK`; se restauró deseado 2, el nodo extra terminó tras el drenaje de 300 s, quedaron 2/2 destinos sanos y CloudFormation terminó `IN_SYNC` a las 15:27:50. No se escribieron datos de negocio. [Reporte sanitizado](aws/AWS-AUTOSCALING-TEST-2026-10-14.json).
- [x] Azure Function `tangama-wms-261008` está `Running`, HTTPS-only, y `/api/health` responde 200.
- [x] Application Insights tras el E2E, última ventana de 10 minutos: 2 recepciones HTTP 202 y 2 ejecuciones de `process_fulfillment_message`, todas correctas; última ejecución `2026-10-14T19:57:57Z`.
- [x] Ruta autenticada de solo metadatos `/api/wms/poison-queue`: conteo aproximado 0 y `payloads_exposed=false`. No se leyó ni modificó el cuerpo de ningún mensaje; el peek directo desde la identidad local sigue denegado.
- [x] Azure Monitor: dos reglas habilitadas; Action Group habilitado con dos receptores `Enabled`. No se afirma entrega de correo Azure en este corte.
- [x] Terraform Azure `azure-rebuild` consultó ARM y devolvió `No changes`, salida 0; el hash del paquete desplegado coincide con el paquete fijado por el ejemplo de reconstrucción. Sin `apply`.
- [x] Roles live por API: admin autenticado como admin; Comercial accede a ventas y recibe 403 en administración/outbox/WMS; Operaciones accede a outbox/WMS y recibe 403 en ventas/administración. No es recorrido visual de navegador.
- [x] Preflight Tailscale actual: AWS CLI/VPC y Azure CLI autenticados, pero no hay dispositivo conectado, clave efímera local ni VNet de prueba; no se creó red ni se incurrió en cargos.
- [x] El usuario confirmó previamente la recepción de alerta y recuperación de AWS SNS; la lectura actual muestra 5 alarmas CloudWatch en `OK`, acciones habilitadas y 2 suscripciones SNS confirmadas. Falta captura independiente de bandeja para evidencia académica.
- [x] E2E del portal AWS desplegado desde EC2 por SSM: Admin inició sesión y completó el flujo ERP; Comercial y Operaciones pasaron la matriz 200/403; importación de SKU sintético, venta `completed_demo`, recepción `received_demo`, 2 eventos outbox entregados y ledger 10→10. Los pedidos/registros de auditoría QA permanecen en RDS/Azure; no se modificó infraestructura.
- [x] Lecturas autenticadas live actuales: 24/24 HTTP 200, concurrencia 6, p95 1,360.41 ms. Se ejecutaron por loopback desde la EC2; no prueban tráfico por ALB ni escalado. Resultado sanitizado: [reporte E2E](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json).
- [x] Recuperación RDS PT-DR-01: la prueba integral del 13/10 verificó marcador SQL y conteos de 14 tablas, RTO 289 s, RPO observado 14 s y limpieza de la copia/snapshot temporal. No se repitió tras el release v10; el resultado medido está en [evidencia DR](aws/AWS-DR-RESTORE-2026-10-13.md).
- [x] Gate local completo: 163 pruebas Python y 14 Node; PT-PERF-02 40/40; build, auditorías de dependencias, validación CloudFormation, Terraform fmt/validate y pruebas mock.
- [x] CSV, parser/plantilla y límites de lote cubiertos localmente: máximo 500; 501 se rechazan antes de escrituras.
- [x] El fallo de las 14:00 se identificó como bug del harness (rol admin esperado para todos), se corrigió y quedó cubierto por pruebas; no era un defecto de la cuenta admin.

## Pendiente — sin check hasta obtener evidencia

- [ ] Seleccionar e importar un CSV desde la interfaz real del portal desplegado; confirmar la previsualización y el resultado persistido. La ruta API live sí pasó.
- [ ] Recorrer visualmente el portal con admin, Comercial y Operaciones, especialmente menús, acciones denegadas y vistas de administración.
- [ ] Medir concurrencia/latencia de un flujo de ventas por ALB/RDS y estimar capacidad para 3,000 usuarios; la sonda CPU anterior prueba el mecanismo de escalado, no el rendimiento de la aplicación.
- [ ] Dar contexto a los intentos de lanzamiento cancelados anteriores (`Client.InternalError` durante el arranque del lab); no se reprodujeron en las pruebas manual ni automática exitosas, pero CloudTrail no dio causa concluyente.
- [ ] Adjuntar captura o registro de bandeja de alerta/recuperación AWS para la sustentación; CloudWatch/SNS están comprobados y el usuario confirmó la recepción, así que no hace falta repetirla ahora.
- [ ] Probar una alerta Azure de extremo a extremo (disparo y entrega). La configuración está habilitada, pero el test oficial de notificación no es compatible con esta suscripción gratuita; no inventar recepción.
- [ ] Si la rúbrica requiere correo saliente fuera del portal: configurar un relay SMTP y un remitente/dominio verificado, y probar entrega y rebote. El correo interno persistente funciona como buzón del portal; Mailpit solo recibe correo de prueba local y no entrega a Internet.
- [ ] Decidir si la rúbrica exige elevar RDS a Multi-AZ y ampliar retención; actualmente IaC y nube concuerdan en Single-AZ/1 día.
- [ ] Red privada AWS–Azure/VPN. Se deja para el final como acordado: añade costo aun en una prueba temporal; el E2E actual usa HTTPS público.
- [ ] WebRTC: llamada de audio/video bidireccional real entre dos navegadores, incluyendo estados de mute/cámara.
- [ ] Dominio propio y HTTPS confiable para el portal, al final del cierre.
- [ ] Confirmar publicación del estado y ejecución del workflow en GitHub; en este corte no se afirma que estos cambios locales se hayan subido ni que CI remoto haya corrido.

La restauración RDS del 13/10 ya probó integridad SQL, RTO/RPO y limpieza;
repetirla es una regresión opcional si una migración futura cambia el esquema,
no un pendiente bloqueante del release v10.

## Límites que no cuentan como defectos de una demo sintética

El WMS conserva un ledger de inventario ficticio; esta prueba demuestra integración y consistencia del saldo, no movimientos físicos. Finanzas cubre operaciones del portal, no contabilidad legal. El correo interno y Mailpit local no acreditan buzones corporativos ni un relay SMTP productivo. La expansión nacional/internacional y los 3,000 usuarios son objetivos de dimensionamiento, no capacidad medida.

## Evidencia detallada

- [Revalidación cloud y E2E](CLOUD-REVALIDATION-2026-10-14.md)
- [QA local](QA-LOCAL-2026-10-14.md)
- [Catálogo sintético](CATALOGO-SINTETICO-IMPORT-2026-10-14.md)
- [Registro maestro](../../core/00_registro_maestro.md)
