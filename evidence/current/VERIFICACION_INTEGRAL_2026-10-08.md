# Verificación integral — 08/10/2026

Este informe conserva su corte de 19:10–19:16 CDT. El inventario posterior de
19:48 CDT y la disposición de Terraform se actualizaron en
[MAPA_ESTADO_ACTUAL_2026-10-08.md](MAPA_ESTADO_ACTUAL_2026-10-08.md), que es la
fuente vigente para el estado actual; los conteos de EC2 de este informe son
una lectura anterior y no deben usarse como inventario más reciente.

Este corte conserva la observación de 19:10–19:16 CDT (08/10/2026); el
[mapa actual de 19:48 CDT](MAPA_ESTADO_ACTUAL_2026-10-08.md) lo supera para el
inventario vigente. En esa revisión se reabrió la
sesión temporal del laboratorio para poder consultar la consola; las consultas
de recursos fueron de solo lectura. No se lanzó, reinició ni eliminó a propósito
ningún recurso de aplicación durante esta verificación.

## Resultado ejecutivo

- **Panel local:** corregido en la copia que realmente sirve `127.0.0.1:8080`,
  `Tangamandapio_SAC_LIMPIO`. El refresco ya no depende de que todos los
  endpoints opcionales respondan a la vez. Los indicadores y pedidos sobreviven
  a un fallo de un endpoint secundario; una sesión expirada devuelve al login
  en vez de dejar un panel vacío. El navegador actual sin sesión muestra el
  formulario de acceso, como corresponde.
- **AWS:** consola y CLI autenticados. En `us-east-1` hay **9 EC2**: **2 en
  ejecución y 7 terminadas**. El ALB `tangamandapio-alb` está `active`; en la
  lectura final sus **2 destinos están sanos**. La primera lectura encontró un
  destino en `Target.FailedHealthChecks` mientras arrancaba; al repetirla, el
  grupo mostró 2 sanos y 0 anómalos. RDS `tangamandapio-postgres` está
  `available`, Multi-AZ, con 7 días de retención. `/health` devuelve 200 por
  HTTPS cuando se omite la validación TLS; dominio/certificado confiable queda
  fuera de este corte. El laboratorio sigue activo y marca $19.1/$50 usados;
  Vocareum indica “No running instance” aunque EC2 muestra dos en ejecución,
  por lo que no debe interpretarse esa línea del panel como inventario EC2.
- **Azure:** el monitor de `process_fulfillment_message` muestra 12 éxitos y 5
  fallos en los últimos 30 días. Las dos filas más recientes de hoy son
  exitosas (código 0; 236 y 403 ms). La vista de trazas del detalle no devuelve
  filas, así que no se afirma que esos éxitos hayan actualizado inventario.
- **Roles:** probados en navegador sobre una instancia temporal del mismo build
  que sirve el puerto 8080, con seis cuentas sintéticas y base aislada.
  Administración accede a gestión; cliente no
  puede abrir `/admin`; comercial, operaciones, bodega y auditor ven las
  herramientas correspondientes a su permiso. La consola muestra cuentas,
  roles/permisos y acciones permitidas, no contraseñas en claro.
- **WMS:** continúa siendo una demo académica. Blob/cola y `demo-inventory-ledger`
  prueban el flujo técnico con datos sintéticos, no existencias reales ni un
  WMS/ERP autorizado. Para hacerlo real hace falta el contrato y acceso
  autorizado al sistema de inventario que será fuente de verdad.
- **Diferido por decisión del proyecto:** prueba A/V entre dos navegadores
  reales y dominio con HTTPS de confianza. No se usaron cámara ni micrófono.

## Panel local y roles

El puerto 8080 no lo sirve el repositorio de este directorio, sino la copia
vecina `C:/Users/Diego/Documents/ChatGPT/Tangamandapio_SAC_LIMPIO/app`. Se
parcheó únicamente el frontend de esa copia, sin alterar su base de datos ni
sus cuentas persistentes.

La causa de los KPI vacíos era agrupar endpoints esenciales y opcionales en un
solo `Promise.all`: el error de un endpoint de roles/administración podía
cancelar toda la actualización visual. El frontend ahora separa ambos grupos,
retiene datos esenciales ante fallos opcionales, informa del servicio que no
respondió y trata el 401 como sesión vencida. Pruebas nuevas cubren un 503
opcional sin pérdida de KPI y expiración de sesión.

| Rol probado en navegador | Vistas observadas | Restricción observada |
|---|---|---|
| Administrador | Resumen, pedidos, WMS, telefonía, usuarios, empresas, auditoría y consola admin | Gestión de roles/usuarios visible; contraseñas no se muestran en claro |
| Comercial | Resumen, pedidos y telefonía | Sin administración ni auditoría |
| Cliente | Resumen y pedidos | `/admin` denegado; solo pedidos autorizados |
| Operaciones | Resumen, pedidos, WMS, telefonía y auditoría | Acceso operativo; sin consola de usuarios |
| Bodega | Resumen, pedidos y WMS | Sin controles de reintento administrativo |
| Auditor | Resumen, pedidos, WMS y auditoría | Sin acciones de telefonía o administración de usuarios |

Pruebas ejecutadas: **35/35 pruebas frontend** y build de producción correcto
en la copia servida por 8080. La puerta reproducible de este repositorio pasó
**59/59 pruebas**, además de validaciones de dependencias, build, CloudFormation
y Terraform descritas en `PRUEBAS_LOCALES_2026-10-08.md`. Se usó base de datos
temporal para las seis sesiones sintéticas; el sitio 8080 mostró el login sin
sesión y las cuentas reales no se cambiaron.
El servidor aislado de pruebas ya está detenido. El archivo de base temporal
solo contiene esas cuentas sintéticas y quedó en `%TEMP%\tangamandapio-e2e-0af783dc696640f99502847ea2b8ff52\smoke.db` porque el entorno bloqueó su eliminación; no es la base usada por el portal 8080.

## AWS: verificación en consola y CLI

Lectura repetida después de autenticar la consola:

| Componente | Resultado comprobado |
|---|---|
| EC2 | 9 instancias listadas; 2 `running`, 7 `terminated`; tipos `t3.micro` |
| Application Load Balancer | `tangamandapio-alb`, estado `active` |
| Target group | `tangamandapio-tg`, puerto 8080; lectura inicial 1 `healthy`/1 `unhealthy` al arrancar; lectura final 2 `healthy`/0 anómalos |
| RDS | `tangamandapio-postgres`, `available`, `MultiAZ=true`, retención 7 días, `db.t3.micro` |
| Salud HTTP | HTTP redirige a HTTPS; `/health` respondió 200 con `curl -k`. La verificación normal falla por confianza TLS y no se consideró certificado válido |
| AWS Academy | Laboratorio `Ready`, 03:57:56 disponibles en la vista observada, $19.1 de $50 usados; el estado “No running instance” no coincide con el inventario EC2 de consola/CLI |

La consola web EC2 se abrió y mostró el inventario; también se vio el resumen
actual del target group (2 en buen estado, 0 en mal estado). Ambas capturas se
visualizaron en la conversación, pero el conector del navegador no ofrece
exportar esos fotogramas a PNG local; por integridad no se rotulan como PNG
archivados. No se guardó una captura nueva de Azure por la misma limitación y
para evitar archivar datos de identidad del encabezado. Los PNG existentes bajo
`evidence/current/**/screenshots` son evidencia histórica con la fecha indicada
en sus nombres, no capturas de este corte.

## Azure: evidencia de ejecución y alcance

En el monitor de Azure Functions, el conteo de 30 días fue 12 correctas / 5
fallidas. Las ejecuciones más recientes visibles el 08/10 fueron:

| Hora mostrada por Azure Portal | Estado | Resultado | Duración |
|---|---|---:|---:|
| 2:55:29 PM | Correcta | 0 | 236 ms |
| 2:55:22 PM | Correcta | 0 | 403 ms |

El panel de consulta de trazas para la invocación seleccionada indicó “No se
encontraron resultados”. Esto verifica que Azure recibió y ejecutó la función,
pero no da evidencia suficiente del resultado de inventario. El código local
identifica el modo del endpoint de inventario como `demo-inventory-ledger` y
declara `is_real_erp=false`. Por eso las etiquetas `simulated_completed` y
`simulated_fulfillment_completed` deben conservar la palabra “simulado” en UI,
documentación y sustentación.

Un WMS real necesita, como mínimo, una integración autorizada a una fuente de
inventario, catálogo SKU, almacén/ubicación, cantidad y unidad, reglas de
reserva/ajuste, idempotencia, confirmación de picking/despacho, credenciales
en Key Vault, trazabilidad y reconciliación. Sin esos datos no se debe
descontar stock real ni presentar el Blob de demo como WMS productivo.

## Responsive y accesibilidad

Revisión estática del frontend activo: hay breakpoints para escritorio/tableta/
móvil (incluidos 1100, 700, 620, 560 y 480 px), estilos `focus-visible`,
preferencia `prefers-reduced-motion`, controles etiquetados y tablas con
encabezados semánticos. El navegador expuso los controles de formulario y
navegación al árbol de accesibilidad durante los smoke tests.

No se instaló un auditor externo ni se hizo una certificación WCAG; tampoco se
forzó un viewport móvil en el navegador disponible. Queda pendiente una pasada
manual a 390 px y 768 px, teclado completo y un escáner automatizado antes de
declarar conformidad formal.

## Incidencias/pendientes

1. Vigilar ambas EC2/targets y el health check; una lectura transitoria falló
   durante el arranque y la lectura final ya fue sana. No se reinició ni
   reemplazó ninguna instancia.
2. Aclarar por qué el panel de AWS Academy dice “No running instance” mientras
   EC2/CLI enumeran dos en ejecución; vigilar el crédito del laboratorio.
3. Archivar PNGs nuevos de EC2/target group/RDS y de
   Azure invocaciones/trazas, con encabezados de cuenta/identidad ocultos.
4. Obtener trazas de aplicación para la Function y hacer una prueba sintética
   extremo a extremo que correlacione aceptación, cola, resultado Blob y estado
   final; no inferirla solo del contador de invocaciones.
5. Integrar un WMS/ERP de prueba autorizado si el alcance exige inventario
   real; mantener la demo sintética mientras tanto.
6. Ejecutar la matriz responsive y de teclado indicada arriba.
7. Mantener diferidos WebRTC A/V entre navegadores y HTTPS confiable/dominio.

No se desplegó código a AWS/Azure, no se modificó infraestructura, no se creó
un pedido cloud, no se tocó la poison queue y no se restauró ni alteró RDS.
