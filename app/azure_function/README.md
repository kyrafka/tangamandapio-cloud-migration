# Receptor Azure de fulfillment

La Azure Function recibe `POST /api/fulfillment/events` con nivel de autorización Function. Cuando el operador configura `WMS_SHARED_TOKEN` desde Key Vault, exige además la cabecera `X-WMS-Token`; el secreto nunca va en el código ni en Terraform. El piloto académico puede operar solo con la clave Function cuando el rol de estudiante no tiene permiso de plano de datos para sembrar secretos. Solo acepta eventos sintéticos `order.created` y un `event_id` seguro. Escribe una sola copia JSON en Blob y solo encola el mensaje cuando esa copia se creó; una repetición devuelve `duplicate` sin volver a encolar.

La Function usa identidad administrada. No recibe claves de Storage ni secretos en el código. Las pruebas deben registrar el mismo `event_id`, el hash, el estado HTTP, el Blob, el mensaje de Queue y la traza de Application Insights.
