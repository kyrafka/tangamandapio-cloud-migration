# Verificación viva de alarmas y permisos — 15/10/2026

Se renovó el perfil local `default` con credenciales temporales de AWS Academy.
STS confirmó la cuenta `841113066612`. El token no se copia a este repositorio
ni a la evidencia.

## Resultado

- El smoke autenticado de portal terminó `LIVE_E2E_PASSED` al ejecutarse por
  Systems Manager en una EC2.
- El administrador pudo consultar `GET /api/admin/alarm-subscriptions`:
  tópico configurado, confirmación requerida, 2 suscripciones de correo
  confirmadas y 0 pendientes.
- La evidencia conserva solo conteos agregados. No contiene direcciones,
  identificadores de suscripción ni credenciales.
- Comercial y Operaciones recibieron HTTP 403 en esa vista administrativa.
- No se crearon, eliminaron ni confirmaron suscripciones y no se enviaron
  mensajes de correo durante esta comprobación.
- El mismo E2E insertó una venta y una recepción de prueba sintéticas, entregó
  ambos eventos a Azure y dejó el ledger demostrativo en 10 antes y después.
- La lectura autenticada de PostgreSQL/RDS terminó 24/24 en HTTP 200, con
  concurrencia 6 y p95 de 2,005.03 ms. Se ejecutó desde el loopback de una EC2;
  no mide la ruta por ALB ni sustenta capacidad de 3,000 usuarios.

## Validación del arnés

`python -m unittest discover -s tests/cloud -p
test_live_aws_portal_azure_e2e.py -v` pasó 8 pruebas, incluida la validación de
que la salida del check solo exponga conteos agregados, rechace estados
inválidos y no acepte destinatarios duplicados. También pasó `py_compile` y
`git diff --check`.

La compuerta integral `tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 169 pruebas unitarias, 14 pruebas Node, 40
transacciones aisladas, build de Vite, auditoría de dependencias sin
vulnerabilidades conocidas, CloudFormation validado y Terraform fmt/validate/
tests mock aprobados. Esta compuerta no aplicó cambios en la nube.

Esto verifica la API desplegada vía SSM, no el flujo visual en navegador. No
modifica la evaluación pendiente de HTTPS/dominio, WebRTC, conectividad privada
AWS–Azure ni pruebas de carga a escala. El inventario Azure sigue siendo un
ledger sintético.
