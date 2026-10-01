# CloudWatch Logs Insights — portal Tangamandapio
# Seleccionar el log group de ApplicationLogGroup y ajustar el rango a la ventana de prueba.

fields @timestamp, @message
| filter @message like /"path": "\/health"/ or @message like /"status": 5/
| sort @timestamp desc
| limit 100

