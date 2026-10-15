# Prueba acotada del origen ALB — 15/10/2026, 16:43 UTC

Desde la instancia gestionada `i-0248520ed78a0dad7` se conectó al DNS del ALB
usando el dominio público como SNI y `Host`, sin pasar por Cloudflare. Una
petición inicial devolvió HTTP 200 y `curl` reportó `ssl_verify_result=0`.

La microcarga posterior hizo 100 solicitudes GET a `/health`, con concurrencia
10 y validación TLS estándar de Python. Resultado: 100/100 HTTP 200, cero
errores, p50 75.59 ms, p95 101.79 ms, máximo 112.29 ms y 0.799 s de duración.
Los datos estructurados están en el [resultado JSON](AWS-ALB-ORIGIN-PERF-2026-10-15-1643.json).

La prueba no escribió pedidos ni alteró datos de negocio o infraestructura;
SSM sí registra la ejecución remota. No mide Cloudflare, transacciones
autenticadas, acceso a RDS/Azure, escalado ni 3,000 usuarios concurrentes. Es
una comprobación del camino de salud del ALB, no una prueba de capacidad.
