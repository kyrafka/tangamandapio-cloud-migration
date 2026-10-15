# Prueba de escalado del ASG — 13/10/2026

## Corte posterior de permisos — 11:33 America/Chicago

El perfil `default` todavía autentica con STS, pero el laboratorio ahora
deniega explícitamente `autoscaling:DescribeAutoScalingGroups` bajo
`voc-cancel-cred`. Por ello, el estado y capacidad del ASG no se pudieron
revalidar a esta hora. El último estado observado antes de esa denegación fue
2/2 instancias sanas a las 10:43; véase la revalidación general. No interpretar
los resultados previos de escalado como una lectura actual.

## Resultado

El scale-out automático del grupo `tangamandapio-asg` funcionó con una carga
sintética de CPU. La política Target Tracking elevó el deseado de 2 a 3
instancias cuando el promedio superó el objetivo de 60%. Los tres destinos
quedaron sanos y el balanceador mantuvo `/health` en HTTP 200 con PostgreSQL
`ok`.

El scale-in automático también quedó demostrado en una segunda prueba. Se
elevó manualmente el deseado de 2 a 3 únicamente para preparar la observación;
pasado el cooldown, la alarma inferior de Target Tracking cambió el deseado de
3 a 2 a las 10:04:19 America/Chicago. No se forzó manualmente la reducción. El
nodo excedente drenó y terminó sin interrumpir el servicio. A las 10:10, el
ASG volvió a 2/2 `InService`/`Healthy`, el ALB a 2/2 `healthy`, y `/health`
respondió 200 con PostgreSQL `ok`. El stack quedó `UPDATE_COMPLETE` y una
nueva detección de drift terminó `IN_SYNC` con cero recursos divergentes.

La primera reducción del ensayo inicial sí se hizo manualmente porque entonces
la alarma baja aún no había iniciado una acción. Ese resultado se conserva
como antecedente; la segunda observación prueba el scale-in automático.

## Secuencia observada

- Línea base: deseado 2, mínimo 2, máximo 4.
- El 13/10 a las 09:02 America/Chicago se observó CPU media de 66.04%; a las
  09:07 fue 45.18%. La alarma alta inició el scale-out a las 09:10:21.
- AWS aumentó el deseado de 2 a 3 y lanzó la instancia `i-0d2cc8022415e816f`.
  Las tres EC2 llegaron a `InService`/`Healthy`; el ALB informó tres destinos
  `healthy`.
- Después de detener los generadores sintéticos, las muestras de las 09:15,
  09:20 y 09:25 registraron CPU media entre 1.02% y 1.05%. La alarma baja usa
  periodo de 60 s y 15 periodos de evaluación, pero no pasó a `ALARM`; su
  `StateReason` seguía mostrando la muestra 43.39% de las 09:05.
- Se fijó manualmente `DesiredCapacity=2` respetando cooldown. El drenaje del
  destino terminó sin afectar el health del portal.
- La comprobación final confirmó 2/2 EC2 sanas, 2/2 destinos sanos y
  `/health` HTTP 200. CloudFormation seguía `UPDATE_COMPLETE`; el chequeo de
  drift de las 09:30 terminó `IN_SYNC`.

### Segunda observación de scale-in — 09:58–10:10 America/Chicago

- La alarma baja aparecía en `ALARM`; el ASG estaba en su mínimo (2), por lo
  que no podía reducirse más. Se fijó manualmente el deseado a 3 para probar la
  respuesta automática al exceso de capacidad, sin generar carga de CPU.
- La tercera EC2 llegó a `InService`/`Healthy`. A las 10:04:19 la actividad de
  Auto Scaling registró que la alarma
  `TargetTracking-tangamandapio-asg-AlarmLow-65af6a13-bec6-4f9f-9f29-48978f67cced`
  disparó la política y cambió el deseado de 3 a 2.
- El ASG seleccionó un nodo para terminar y esperó el drenaje de conexiones del
  ALB. A las 10:10:10 ya quedaban solo las dos instancias originales, ambas
  `InService`/`Healthy`; los dos destinos estaban `healthy` y `/health` devolvió
  HTTP 200.
- La detección CloudFormation iniciada a las 10:10 terminó
  `DETECTION_COMPLETE`/`IN_SYNC`, con cero recursos divergentes.

### Revalidación de disponibilidad — 10:25 America/Chicago

Se volvió a consultar la cuenta y el stack con el perfil local `default`:
cuenta `841113066612`, stack `UPDATE_COMPLETE`, ASG deseado 2/2 (ambas
instancias `InService`/`Healthy`) y destinos del ALB 2/2 `healthy`. Una nueva
solicitud HTTP `GET /health` devolvió 200 con `database=ok` y `status=ok`.
El drift detectado a las 10:10 permanece como última detección documentada
(`IN_SYNC`); esta revalidación no ejecutó otra detección. El listener público
continúa en HTTP, sin dominio ni TLS confiable.

## Alcance

La evidencia acredita scale-out automático ante CPU sintética y scale-in
automático 3→2 al quedar capacidad ociosa, después de preparar manualmente el
deseado en 3. No demuestra throughput de transacciones, resiliencia ante fallo
de AZ ni soporte para 3,000 usuarios concurrentes. La prueba no realizó cambios
en pedidos ni en RDS. La nube sigue siendo un entorno temporal de laboratorio.

La siguiente validación debe usar carga representativa de transacciones y
medir p95/errores junto con los eventos del ASG; no se modificaron la política
ni el monitoreo durante este ensayo.
