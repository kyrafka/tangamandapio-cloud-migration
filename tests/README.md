# Pruebas reproducibles de Tangamandapio S.A.C.

La carpeta separa pruebas locales gratuitas de pruebas que requieren una sesión temporal del laboratorio. Ningún script inicia AWS Academy ni crea recursos sin una autorización explícita.

## Puerta local (sin costo cloud)

Desde PowerShell, en la raíz:

```powershell
.\tests\run_local_quality.ps1
```

La carga local o contra el ALB se ejecuta con:

```powershell
python .\tests\performance\load_test.py --url http://HOST/health --requests 100 --concurrency 10 --output evidencia-perf.json
```

## Pruebas AWS con el laboratorio encendido

- `pt-sto-01-s3.sh`: escribe, descarga, compara SHA-256 y elimina el objeto temporal.
- `pt-mon-01-alarm.sh`: requiere `DEMO_ALARM_STATE=YES`; fuerza brevemente el estado para una demostración y lo devuelve a control de métricas. Esto prueba la ruta operativa, no simula CPU real.
- `pt-sec-02-rds-deny.py`: espera que el endpoint privado rechace o sea inalcanzable desde Internet.
- `pt-dr-01-rds-restore.sh`: requiere `CONFIRM_COSTLY_DR_TEST=YES`; crea snapshot e instancia temporal, mide el RTO observado y elimina ambos al salir.

Antes de ejecutar: confirmar región `us-east-1`, stack exacto, saldo y ventana disponible. Al terminar, verificar CloudFormation `DELETE_COMPLETE`, cero coincidencias del proyecto y laboratorio terminado.
