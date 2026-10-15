# Prueba visual del portal en Chrome — 15/10/2026, 14:38–14:45 UTC

La prueba se hizo en la pestaña Chrome del portal publicado
`https://tangamandapio.kendellnm.me/`. No se abrió localhost ni se controlaron
otras ventanas o aplicaciones.

## Interfaz pública

- La portada, el fondo y el panel de acceso cargaron y permanecieron utilizables.
- El selector cambió de tema oscuro a claro y de vuelta a oscuro. El tema claro
  sigue viéndose muy luminoso y con contraste menor que el oscuro; es una
  observación visual, no un cambio aplicado.
- Abrir/cerrar el panel de acceso funcionó. Al enviar vacío, el navegador enfocó
  el campo de usuario y mostró su validación requerida.
- La pestaña quedó en HTTPS, con el panel de acceso abierto y sin datos
  introducidos, para que el usuario inicie sesión y permita continuar con las
  vistas privadas.

No se inició sesión con una cuenta real en esta revisión; por tanto, no se
probaron visualmente Admin, Comercial, Operaciones, ERP, CSV ni telefonía. La
prueba de formulario vacío no envió credenciales.

## E2E automatizado del portal por HTTPS

La única corrida del smoke E2E desde EC2/SSM terminó antes de autenticarse con
`POST /api/auth/login` → HTTP 403. No se confirmó si el rechazo provino de la
aplicación o de la capa perimetral; no se deshabilitó ni sorteó ninguna
protección y no se reintentó. La secuencia se detuvo antes de crear la venta,
recepción o eventos sintéticos, así que esta corrida no produjo esos cambios.
Este fallo no invalida la corrida previa exitosa dirigida al ALB, pero tampoco
la sustituye como prueba del dominio HTTPS.

Durante la automatización de interfaz, la herramienta informó además que su
telemetría externa de Statsig fue bloqueada; no era una solicitud al dominio
del portal. No se observó un error funcional del portal durante los controles
visuales descritos arriba.

## Siguiente paso

Para comprobar las vistas privadas exclusivamente en esa pestaña, el usuario
debe iniciar sesión allí con una cuenta autorizada. Después se podrá recorrer
cada rol sin compartir la contraseña en el chat.
