# Evidencia del proyecto

Esta carpeta conserva capturas y resultados con fecha. Cada archivo acredita solo lo que describe y el entorno donde se tomó; una captura antigua no demuestra el estado actual de una nube.

## Último corte vivo — 29/10/2026

[`current/azure/AZURE-LIVE-CHECK-2026-10-29.json`](current/azure/AZURE-LIVE-CHECK-2026-10-29.json) reúne el estado HTTPS del portal, la denegación de inventario AWS, una recepción Azure Queue/Function con replay idempotente y la lectura de gateway/Storage. No contiene claves ni payload completo. El evento cambia el ledger sintético una unidad. No es evidencia de PostgreSQL cross-cloud, de login/roles, de túnel AWS→Flex ni de autoescalado.

El reintento posterior de AWS a las 21:24 UTC está en [`current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json`](current/aws/AWS-LIVE-ACCESS-CHECK-2026-10-29.json). STS autenticó en una cuenta distinta del inventario histórico, pero cinco consultas de solo lectura recibieron denegación explícita; no se cambió la nube ni se inició una prueba desde EC2.

## Capturas versionadas

Las capturas históricas disponibles están en:

- `current/aws/screenshots/`: consola/estado operativo de AWS del 01/10/2026.
- `current/azure/screenshots/`: consultas de inventario, salud, recorrido WMS y cierre del 01/10/2026.

Son evidencia de ese corte, no un inventario vigente. No contienen claves privadas ni credenciales de laboratorio.

## Resultados automatizados

Los archivos JSON en `current/` conservan resultados de pruebas sintéticas y de carga. Revise la fecha, ruta y concurrencia antes de compararlos; una carga de lectura o de loopback no demuestra capacidad transaccional para 3,000 usuarios.

## Bitácora local

La bitácora maestra y los registros cronológicos detallados se conservan en el equipo de trabajo y no se publican en GitHub. El estado vigente resumido para el repositorio está en [README](../README.md), [IaC](../iac/README.md) y la [matriz de criterios](../core/04_matriz_rubrica.md).

## Capturas nuevas

Antes de publicar capturas de consola, revisa que no muestren sesiones, correo personal, identificadores de cuenta, direcciones IP, tokens ni datos que no deban ser públicos. La documentación no convierte una observación visual en una validación de servicio.
