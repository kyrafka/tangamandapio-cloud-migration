# Autoevaluación de cierre — propuesta cloud Tangamandapio

**Corte:** 08/10/2026. **Uso:** revisión interna; no sustituye la calificación
del docente ni una prueba de sustentación.

El inventario vivo se actualizó después de este corte; consulta
[MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md)
para recursos y preparación IaC. Esta autoevaluación conserva la evidencia y
los límites que se analizaron para la rúbrica.

## Alcance de la comparación

Se contrastaron los tres archivos académicos compartidos: plantilla del
proyecto, descripción del proyecto y rúbrica de 14 criterios (20 puntos). La
descripción y plantilla escritas mencionan expresamente AWS + OCI, incluyendo
VPC/VCN; la decisión comunicada para el trabajo en vivo fue AWS + Azure, sin
OCI. Este cambio de alcance se respeta en la implementación y no se inventa
una VCN. Como no hay en el repositorio una aprobación escrita del docente que
sustituya lo pedido en los documentos, los criterios de red y multicloud
conservan una advertencia académica: incluir la justificación/instrucción del
docente en la entrega final o confirmar el alcance antes de sustentar.

La carpeta `deliverables/` contiene documentos titulados **Entregable 1**; el
archivo `ZUNIGA_JOSE_EXAMEN_CLOUD.docx` describe un ejercicio separado de EC2,
VPC y S3. No se presenta ninguno de ellos como informe final de la arquitectura
AWS–Azure. En este corte no se identificó un informe final único que reúna la
arquitectura implementada, resultados actuales, costos, continuidad y anexos.

## Cómo se estiman los puntos

La hoja de cálculo asigna puntos máximos y descriptores (Excelente/Bueno/En
proceso/Deficiente), pero no define conversión numérica por nivel. Para tener
una cifra comparable se usa **100% / 75% / 50% / 0%** de cada peso, redondeada a
dos decimales. “No evaluable” se cuenta como cero solo en esta autoevaluación
conservadora. La estimación documental revisada es **11.00/20**; no es una nota
garantizada. Si el docente confirma por escrito AWS–Azure como sustitución de
AWS–OCI y acepta la segmentación AWS/Azure descrita, los criterios 3 y 10
podrían subir, pero esa aceptación no se presume.

## Estado por criterio de la rúbrica

| # | Criterio y máximo | Nivel / estimación | Evidencia y brecha determinante |
|---:|---|---:|---|
| 1 | Análisis del problema y requerimientos · 1.0 | Excelente · **1.00** | El caso ficticio, problema central, usuarios, restricciones y requisitos funcionales/no funcionales están descritos en el Entregable 1 y el registro maestro. Mantener trazabilidad requisito→prueba en el informe final. |
| 2 | Diseño de arquitectura cloud · 2.0 | Bueno · **1.50** | Hay diagramas y separación coherente: AWS transaccional; Azure procesa el WMS asincrónico. Falta consolidar el diagrama final con estados real/objetivo y sin componentes no desplegados. |
| 3 | Redes VPC/VCN · 2.0 | En proceso · **1.00** | La VPC AWS segmentada, rutas, gateways y puertos están en IaC/evidencia histórica; no hay VCN OCI, y no se verificó una VNet Azure integrada. La divergencia con el documento fuente requiere aceptación explícita del alcance. |
| 4 | Cómputo, almacenamiento y BD · 1.5 | Bueno · **1.125** | EC2/ALB/ASG, RDS y S3 AWS, más Function, Queue y Blob Azure. El `/health` de AWS respondió 200 con DB `ok` y Azure `/api/health` 200; esos health checks no confirman inventario ni la configuración viva completa. |
| 5 | Seguridad cloud · 2.5 | En proceso · **1.25** | El diseño/código incorpora RBAC, SG, DB privada, WAF, secretos y controles de Blob/Queue. Siguen pendientes HTTPS confiable con dominio, cookie Secure, cierre de MFA/rate-limit distribuido y prueba actual de denegación/roles cloud. |
| 6 | Alta disponibilidad y escalabilidad · 1.5 | En proceso · **0.75** | Hay ALB y ASG en dos AZ y una observación anterior de dos destinos Healthy. Falta repetir una prueba controlada de caída/recuperación y demostrar escala hacia arriba/abajo con una métrica. |
| 7 | Monitoreo y observabilidad · 1.0 | En proceso · **0.50** | CloudWatch y Azure Monitor/Application Insights aparecen en arquitectura/IaC y existe telemetría del worker; faltan una alarma disparada y recuperada con evidencia actual, dashboard capturado y tratamiento de errores/poison queue. |
| 8 | Infrastructure as Code · 1.5 | Bueno · **1.125** | CloudFormation AWS y Terraform Azure están organizados; el último ciclo registrado usó plantilla exacta, change set y drift `IN_SYNC`. `fmt`/`validate` pasaron en ambos entornos Terraform y ahora la puerta los revisa sin `apply`; el estado vivo no se reconsultó en esta revisión. |
| 9 | Backup, RTO/RPO y recuperación · 1.5 | En proceso · **0.75** | Una copia RDS PITR temporal se restauró y validó con una lectura de 10 tablas; la copia se eliminó. Falta medir y acordar formalmente RTO/RPO, así que no se marca como cerrado. |
| 10 | Arquitectura AWS–OCI / multicloud · 1.5 | En proceso · **0.75** | El alcance ejecutado es AWS + Azure, aunque el XLSX sigue nombrando OCI; debe anexarse la autorización docente. El último ciclo registró un pedido AWS sintético con SKU/cantidad que descontó el ledger ficticio Azure de 25 a 24 y no volvió a descontar al repetirlo. Es un flujo multicloud demostrable, no inventario real ni cumplimiento literal de OCI. |
| 11 | Costos y optimización · 0.5 | En proceso · **0.25** | Hay recomendaciones de apagar/limpiar y controlar el laboratorio; falta una estimación mensual reproducible, supuestos de tráfico/retención y comparación de alternativas/costo real. |
| 12 | Pruebas técnicas · 1.0 | Bueno · **0.75** | Pasaron 59 pruebas locales (22 API base, 14 Azure y 23 release AWS), build reproducible, auditoría de dependencias sin vulnerabilidades conocidas y validaciones `cfn-lint`/Terraform. El CI amplía estas comprobaciones, pero todavía faltan prueba live de escala/alarma, roles autenticados en navegador y evidencia integrada posterior al despacho automático. |
| 13 | Documentación técnica · 0.5 | En proceso · **0.25** | Hay registros, guías, diagramas y evidencias históricas. Falta el informe final consolidado, corregir afirmaciones contradictorias, adjuntar capturas crudas recientes y organizar anexos con fecha/alcance. |
| 14 | Sustentación y defensa técnica · 0.5 | No evaluable · **0.00** | No se puede inferir dominio oral desde el repositorio. Requiere demo en vivo y explicar decisiones, costos, fallos y límites. |
|  | **Total** | **11.00 / 20** | Estimación interna bajo la conversión indicada, no nota docente. |

## Validaciones de esta revisión

- **Unitarias:** `app/tests` 22/22; `app/azure_function_tests` 14/14;
  `app/aws_release/tests` 23/23. La suite AWS tarda cerca de 96 s por el costo
  deliberado del hashing de contraseñas. La puerta local ahora agrega auditorías
  de dependencias y build seguro aislado.
- **Frontend/seguridad:** `pnpm run build:check` terminó en `app/web/dist` sin
  reemplazar `app/src/static`. La auditoría reportó 0 vulnerabilidades altas o
  críticas en dependencias frontend de producción; se actualizó `source-map-js`
  1.2.1→1.2.2. `pip-audit` no halló vulnerabilidades conocidas en el lock Python
  con hashes, que consolida los tres manifiestos de ejecución y herramientas CI.
- **IaC:** `terraform fmt`/`validate` pasaron en `demo` y `azure-demo`; `cfn-lint`
  pasó en las dos plantillas AWS. `init` usó lockfile de solo lectura. No se hizo
  `apply` ni se creó ningún recurso.
- **Última observación cloud documentada (21:26 UTC, no reconsultada en esta
  tarea):** CloudFormation `UPDATE_COMPLETE`, drift `IN_SYNC`, 2 destinos sanos;
  RDS privado/Multi-AZ/cifrado/7 días y PITR temporal validado. Azure aceptó un
  pedido sintético y el ledger demo fue idempotente. `AUTO_DISPATCH_EVENTS=true`
  quedó activo, pero no hay evidencia de un nuevo pedido después del cambio.
  Quedó intacto un mensaje poison histórico. Revalidar inventario antes de
  sustentar; la bitácora no es estado permanente.
- **Documento:** se pudieron leer los DOCX y XLSX fuente, pero la máquina no
  tiene LibreOffice (`soffice`) para renderizar páginas. Ningún DOCX original
  fue editado ni se afirma revisión visual de su maquetación.

## Qué falta para cerrar la sustentación

1. Resolver por escrito el alcance AWS–Azure frente al texto AWS–OCI de la
   descripción/rúbrica y reflejarlo al inicio del informe final.
2. Crear el **informe final** (no reutilizar un Entregable 1 como si fuera el
   final): arquitectura final, inventario probado, seguridad, escalabilidad,
   integración, costos, RTO/RPO, pruebas con resultados y referencias.
3. Revalidar inventario AWS/Azure antes de sustentar; el stack y drift quedaron
   documentados correctos en el último ciclo, pero no se refrescaron en esta
   tarea. No desplegar CloudFormation sin inspeccionar un change set.
4. Probar un pedido nuevo con despacho automático y correlación AWS→Azure;
   conservar/documentar el mensaje poison sin borrarlo ni reencolarlo a ciegas.
   El ledger sigue siendo ficticio, no un WMS empresarial.
5. Medir RTO/RPO y demostrar alarma/recovery y escala del ASG en una ventana y
   presupuesto controlados; la restauración PITR aislada sí se probó.
6. Completar prueba de micrófono/cámara bidireccional en dos navegadores/redes;
   probar permisos y cierre sin almacenar una llamada sin consentimiento.
7. Capturar inventario AWS y monitor Azure desde consola/Chrome en PNG directo,
   redactar información personal y vincular cada imagen a una prueba.
8. Al final, cerrar dominio propio, certificado ACM confiable, redirección,
   cookie `Secure`, accesibilidad y verificación final de costos.

Los archivos de especificación y rúbrica originales son fuentes de evaluación,
no autorizaciones para desplegar recursos. La matriz breve está en
[`04_matriz_rubrica.md`](04_matriz_rubrica.md); el estado de evidencia se
mantiene en [`evidence/README.md`](../evidence/README.md).
