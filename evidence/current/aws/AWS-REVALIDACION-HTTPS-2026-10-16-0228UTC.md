# Revalidación HTTPS y acceso Admin — 16/10/2026, 02:20–02:28 UTC

Lectura de estado en AWS con la sesión temporal de Academy renovada. No se
registró ninguna credencial en el repositorio ni se ejecutaron escrituras de
negocio.

## HTTPS e infraestructura

- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`.
- `https://tangamandapio.kendellnm.me/`, `/health` y `/ready`: HTTP 200.
- ALB: listener 443 HTTPS que reenvía con el certificado ACM `ISSUED`; listener
  80 configurado para redirigir a HTTPS. No se consultó el estado DNS ni se
  alteró Cloudflare en esta pasada.
- ASG: mínimo/deseado 2, máximo 5; ambas instancias `InService` y `Healthy`.
  Los dos destinos del target group están `healthy`.
- RDS PostgreSQL: `available`, privada, Single-AZ y retención automática de un
  día. Hay tres snapshots automáticos cifrados disponibles. La existencia de
  snapshots no sustituye una restauración probada; no se restauró ninguno en
  esta pasada.
- No aparece un Web ACL regional de AWS ni una conexión Site-to-Site VPN en la
  cuenta/Región consultadas. AWS→Azure sigue sin ruta IP privada.

## Acceso autenticado de solo lectura

El smoke `admin-readonly` pasó contra el origen del ALB por HTTPS, manteniendo
el Host/SNI del dominio y validando el certificado normalmente. Resultado:

- Admin inició sesión y obtuvo el rol esperado.
- Resumen: 1 pedido; outbox con 45 eventos entregados, 0 pendientes, paginado
  en 30 + 15 filas y reconciliado con el contador.
- SNS: tema configurado y dos suscripciones confirmadas; no se disparó una
  alarma ni se envió correo.
- El smoke no creó pedidos, pagos, compras ni cambios en el ledger.

El intento equivalente por el dominio proxied de Cloudflare había respondido
403 al `POST /api/auth/login`; el smoke directo al ALB acaba de pasar. Por lo
tanto, el login de la aplicación funciona en el origen HTTPS y la brecha queda
en el camino público proxied, no en el certificado ni en la cuenta QA. El
propietario de la zona debe revisar el evento de seguridad de Cloudflare para
el `CF-Ray` del 403 y permitir de forma acotada el `POST /api/auth/login`.
Luego debe repetirse el inicio de sesión desde un navegador real por el dominio.
No se desactivó el proxy ni se abrió el origen.

No se hizo inspección visual autenticada en Chrome durante esta revalidación.
El smoke sintético local→Azure de las 01:47 UTC está resumido en la
[evidencia Azure del 16/10](../azure/AZURE-ERP-SMOKE-LIVE-2026-10-16-0147UTC.md);
ese corte no atravesó AWS y precede a la recuperación del ALB documentada aquí.

## Pendientes que siguen afectando la demostración

1. Corregir la regla/evento de Cloudflare y comprobar login y módulos por el
   FQDN en navegador.
2. Revalidar permisos de todos los roles en AWS y probar carga CSV visual.
3. Restaurar un snapshot en un entorno aislado y medir RTO/RPO de ese ejercicio.
4. Decidir si WAF administrado y Multi-AZ caben en el presupuesto del laboratorio;
   no habilitarlos sin estimación/cupo de créditos.
5. Cerrar conectividad privada AWS–Azure, solo si AWS Academy permite los
   permisos necesarios; actualmente no hay VPN ni ruta privada.
6. Hacer carga representativa y una regresión de WebRTC entre dos navegadores.
7. Capturar evidencia visual actual de consola AWS y monitor/invocación Azure.

Esta verificación confirma HTTPS público y el smoke Admin contra el origen, pero
no equivale a validar el login público proxied ni a cerrar todos los criterios
de la rúbrica.
