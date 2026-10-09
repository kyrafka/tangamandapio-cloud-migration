# Matriz de evaluación — corte 08/10/2026

Esta matriz sigue los **14 criterios y 20 puntos** del XLSX del curso. La nota
es una autoevaluación provisional; la conversión numérica asumida y las
limitaciones/evidencias por criterio están en
[10_evaluacion_rubrica_entregable_final_2026-10-08.md](10_evaluacion_rubrica_entregable_final_2026-10-08.md).
Para comprobar qué recursos cloud existen al corte actual, consulta
[MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md);
esta matriz evalúa la rúbrica y no sustituye ese inventario.

| # | Criterio | Máximo | Nivel actual | Estimación |
|---:|---|---:|---|---:|
| 1 | Análisis del problema y requerimientos | 1.0 | Excelente | 1.00 |
| 2 | Diseño de arquitectura cloud | 2.0 | Bueno | 1.50 |
| 3 | Redes VPC/VCN | 2.0 | En proceso | 1.00 |
| 4 | Cómputo, almacenamiento y BD | 1.5 | Bueno | 1.125 |
| 5 | Seguridad cloud | 2.5 | En proceso | 1.25 |
| 6 | Alta disponibilidad y escalabilidad | 1.5 | En proceso | 0.75 |
| 7 | Monitoreo y observabilidad | 1.0 | En proceso | 0.50 |
| 8 | Infrastructure as Code | 1.5 | Bueno | 1.125 |
| 9 | Backup, RTO/RPO y recuperación | 1.5 | En proceso | 0.75 |
| 10 | Arquitectura AWS–OCI / multicloud | 1.5 | En proceso | 0.75 |
| 11 | Costos y optimización | 0.5 | En proceso | 0.25 |
| 12 | Pruebas técnicas | 1.0 | Bueno | 0.75 |
| 13 | Documentación técnica | 0.5 | En proceso | 0.25 |
| 14 | Sustentación y defensa técnica | 0.5 | No evaluable aún | 0.00 |
|  | **Total estimado** | **20.0** |  | **11.00** |

**Alcance por resolver:** la descripción/plantilla escrita pide AWS + OCI,
mientras que la instrucción de trabajo comunicada fue AWS + Azure y sin OCI.
El proyecto sigue el alcance AWS–Azure; obtener/documentar la aprobación del
docente y anexarla antes de entregar. No presentar OCI como implementado.

**Estado importante:** 59 pruebas locales, build frontend aislado, auditorías de
dependencias, `cfn-lint` y validaciones Terraform aprobaron. La última evidencia
cloud registrada el 08/10 incluye stack AWS en `UPDATE_COMPLETE`/drift
`IN_SYNC`, restauración PITR temporal validada y flujo AWS→Azure con inventario
ficticio idempotente; esta revisión de calidad no reconsultó las nubes. Sigue
pendiente medir RTO/RPO, escala/alarma, validar roles autenticados en navegador,
el despacho automático end-to-end tras su activación, A/V real y dominio HTTPS
confiable.
