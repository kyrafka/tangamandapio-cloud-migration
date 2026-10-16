# Revalidación de grabaciones y despliegue — 16/10/2026, 16:38 UTC

## Corrección de reproducción de audio

La ruta privada de reproducción devolvía HTTP 500 al comparar `expires_at` de
PostgreSQL (`datetime`) con un texto ISO. Se normalizó la fecha a UTC antes de
evaluar la expiración y se añadieron pruebas para los tipos `datetime`, ISO con
offset y UTC (`Z`), además de una regresión del endpoint.

El arreglo está desplegado como `20261016-voice-recording-playback-v20-python312`.
El SHA-256 del artefacto es
`c3c1f3e4ec928865802695887fc118a1f78767739880da72233f13d03236df45`.
Se validó por HTTPS con una sesión Admin de solo lectura, conectando al origen
AWS con validación TLS normal: el catálogo reportó una grabación y el endpoint
privado devolvió HTTP 200, `audio/webm` y 71,709 bytes, coincidentes con los
metadatos. No se descargó ni reprodujo el contenido en esta comprobación.

El intento automatizado mediante el dominio pasó por Cloudflare y recibió HTTP
403 antes de llegar al portal; por ello la comprobación autenticada se hizo
directamente contra el origen del ALB, sin cambiar ni desactivar controles de
Cloudflare. La interacción visual con Chrome no se completó porque la
herramienta de control del navegador se detuvo antes de poder interactuar.

## Estado AWS observado

- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`.
- Parámetros de artefacto: revisión v20 y SHA-256 coincidente con el paquete.
- Detección de drift: `IN_SYNC`, cero recursos desviados.
- Los 27 parámetros de la plantilla local corresponden a los 27 parámetros
  registrados por el stack.
- Balanceador: dos instancias objetivo en estado `healthy`.
- Dominio HTTPS `/health` y `/ready`: HTTP 200.

## Verificación local

- `tests.cloud.test_live_aws_portal_azure_e2e`: 40 pruebas aprobadas, incluidas
  las pruebas de reproducción y de opt-in seguro.
- `git diff --check` y compilación sintáctica del test: aprobados.
- Puerta de calidad completa: 235 pruebas unitarias aprobadas; validación y
  formato de Terraform, pruebas Terraform, cfn-lint, build del frontend y
  auditorías de dependencias aprobados. Sin operaciones de nube desde la puerta.

La grabación de audio sigue almacenada según la retención ya configurada; esta
corrección no elimina ni modifica su contenido.
