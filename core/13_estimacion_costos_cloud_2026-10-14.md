# Estimación de costos cloud — 14/10/2026

## Para qué sirve y qué no es

Es una estimación reproducible de precio público para comparar decisiones, no
una cotización ni el importe facturado por AWS Academy/Azure for Students. Se
excluyen impuestos, créditos académicos, descuentos contractuales y cargos
variables que todavía no tienen una medición mensual fiable. La salida no debe
presentarse como “costo total de producción”.

El corte de inventario consultado el 14/10/2026 a las 02:03 America/Chicago
mostró en AWS `us-east-1`: ASG con mínimo/deseado de dos `t3.micro`, una RDS
PostgreSQL `db.t3.micro` Single-AZ con 20 GB gp3 y retención de backup de un
día, un ALB, un NAT Gateway con una IPv4 pública y dos secretos. No está
habilitado WAF ni AWS Backup. El cálculo mantiene esos tamaños y 730 horas al
mes para los recursos horarios. Azure conserva Function Linux Consumption
`Y1`, Storage LRS, dos colas, Blob privado, Log Analytics y Application
Insights; el tope configurado de ingestión es 0.1 GB/día.

## Resultado base AWS

Recalcular desde PowerShell, sin credenciales ni llamadas a la nube:

```powershell
./iac/scripts/estimate_cloud_costs.ps1
```

La corrida por defecto estima **US$91.92/mes de subtotal modelado AWS** antes
de impuestos. Supone 730 horas, un LCU promedio consumido por hora y 10 GB/mes
procesados por NAT. El valor es un subtotal, no un techo: S3, logs, snapshots
adicionales, salida/cross-AZ, consumo real del ALB, IPv4 de otros servicios y
posibles cargos de transferencia pueden aumentarlo. El precio NAT usado es el
ejemplo público estadounidense de AWS y debe verificarse en Pricing Calculator
para la región/cuenta antes de presupuestar gasto real.

| Componente | Supuesto mensual | Cálculo USD |
|---|---:|---:|
| EC2 Linux `t3.micro` | 2 × 730 h × $0.0104/h | $15.18 |
| EBS gp3 | 16 GB-mes × $0.08 | $1.28 |
| RDS PostgreSQL `db.t3.micro`, Single-AZ | 730 h × $0.018/h | $13.14 |
| RDS gp3 | 20 GB-mes × $0.115 | $2.30 |
| ALB | 730 h × $0.0225/h | $16.43 |
| Capacidad ALB | 1 LCU promedio × 730 h × $0.008 | $5.84 |
| NAT Gateway | 730 h × $0.045/h | $32.85 |
| Procesamiento NAT | 10 GB × $0.045/GB | $0.45 |
| IPv4 pública en NAT | 1 × 730 h × $0.005/h | $3.65 |
| Secrets Manager | 2 secretos × $0.40 | $0.80 |
| **Subtotal modelado** | | **$91.92** |

Las variables de carga se pueden ajustar, por ejemplo:

```powershell
./iac/scripts/estimate_cloud_costs.ps1 -ComputeHours 160 -SharedInfrastructureHours 730 -AverageAlbLcuPerHour 0.1 -NatProcessedGb 2
```

Ese escenario produce un subtotal de **US$64.19/mes**: EC2/RDS operan 160 h,
pero ALB/NAT/IPv4 siguen 730 h. No equivale a apagar el laboratorio.

Esto no representa apagado completo: ALB, NAT y su IPv4 continúan generando
costo por hora aunque EC2/RDS se detengan. Para eliminar cargos persistentes
hay que destruir los recursos cobrables después de conservar y verificar los
respaldos necesarios.

## Azure y límites de medición

La Function `Y1` no tiene una cuota fija de cómputo; en una suscripción elegible
de pago por consumo Microsoft incluye 1 millón de ejecuciones y 400,000 GB-s
mensuales por suscripción. El almacenamiento que necesita Functions se factura
aparte, por lo que esta estimación no le asigna $0 a Blob/Queue. La ingestión
de logs está limitada localmente por IaC a 0.1 GB/día (máximo teórico cercano a
3 GB en 30 días); Microsoft publica 5 GB/mes gratis por cuenta de facturación
para el nivel de Logs correspondiente, pero el beneficio y su consumo compartido
deben confirmarse en el Cost Analysis de la suscripción. No se cuenta como
ahorro garantizado. Los datos guardados y las transacciones de Blob/Queue,
retención, alertas con dimensiones y transferencia entre regiones se mantienen
como variables sin volumen observado.

Por eso el dato útil hoy es: **AWS modelado ≈ $91.92/mes + Azure variable no
medida** en funcionamiento continuo, con los supuestos indicados. Para el
costo real del laboratorio hacen falta Cost Explorer y Azure Cost Analysis con
un rango cerrado posterior a la ingestión de facturación; el reporte AWS de
mes en curso consultado en este corte mostraba líneas positivas/negativas que
se compensaban y el periodo aún estaba abierto. No sirve para validar el precio
de lista ni proyectar un mes completo.

## Sensibilidad y optimización

- ALB y NAT aportan juntos alrededor de $49.28/mes de cargos horarios bajo este
  modelo; apagar solo la aplicación no elimina esos cargos.
- Reducir el ALB a 0.1 LCU promedio reduce el supuesto de capacidad de $5.84 a
  $0.58/mes; el cargo horario del ALB sigue igual.
- Cada 100 horas menos de EC2 y RDS reduce el subtotal en unos $3.88, pero el
  almacenamiento sigue facturándose y la disponibilidad del servicio se pierde
  mientras se detienen.
- Evaluar endpoints gateway de S3 y limitar egress puede reducir procesamiento
  NAT; sustituir el NAT administrado requiere revisar seguridad, operación y
  redundancia antes de cambiar IaC.
- Multi-AZ, retención extendida, WAF, VPN y ambientes separados no están
  incluidos. Deben agregarse como escenarios independientes y someterse a una
  revisión de costo antes de habilitarlos.

## Fuentes oficiales y fecha

Precios consultados el 14/10/2026. Las tarifas pueden cambiar; AWS indica que
el precio de la página del servicio prevalece si difiere del archivo Price List.

- AWS Bulk Price List, EC2 `us-east-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json> (Linux `t3.micro` $0.0104/h; gp3 EBS $0.08/GB-mes).
- AWS Bulk Price List, RDS `us-east-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json> (PostgreSQL `db.t3.micro` Single-AZ $0.018/h; gp3 $0.115/GB-mes).
- [AWS Prescriptive Guidance, EC2 example in `us-east-1`](https://docs.aws.amazon.com/prescriptive-guidance/latest/optimize-costs-microsoft-workloads/right-size-selection.html) (`t3.micro` Linux $0.0104/h).
- [AWS ALB pricing](https://aws.amazon.com/elasticloadbalancing/pricing/) ($0.0225/h y $0.008/LCU-h en el ejemplo de N. Virginia).
- [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/) (NAT facturado por hora y GB procesado; ejemplo público $0.045 por cada unidad en US East; IPv4 en uso $0.005/h).
- [AWS Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/) ($0.40 por secreto-mes, sujeto a tarifa vigente y uso de API).
- [Azure Functions pricing](https://learn.microsoft.com/azure/azure-functions/pricing) (subsidios del plan Consumption y nota de que el Storage asociado va por separado).
- [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/) (primeros 5 GB/mes gratis por cuenta de facturación en el nivel indicado; límites de elegibilidad aplican).
- [Azure Retail Prices API](https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices) y [calculadora oficial Azure](https://azure.microsoft.com/pricing/calculator/).
- [AWS Price List Bulk API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api-fetching-price-list-files-manually.html) y [calculadora oficial AWS](https://calculator.aws/).
