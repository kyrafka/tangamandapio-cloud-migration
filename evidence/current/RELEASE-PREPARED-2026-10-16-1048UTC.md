# Release AWS v19 preparado, pendiente de publicación — 16/10/2026, 10:48 UTC

- Revisión: `20261016-webrtc-ice-config-v19-python312`.
- Paquete reproducible local:
  `artifacts/portal-b2b-20261016-webrtc-ice-config-v19-python312.tar.gz`.
- SHA-256 recalculado: `e5ab7874feafd8f22ad2c0d631acbd3448188479616d42fbc1f7bb649c1e12d8`.
- CloudFormation ahora tiene la misma revisión, SHA y clave S3 content-addressed:
  `releases/tangamandapio/portal-b2b-20261016-webrtc-ice-config-v19-python312-e5ab7874feafd8f22ad2c0d631acbd3448188479616d42fbc1f7bb649c1e12d8.tar.gz`.
- El test del empaquetador aceptó el digest y `tests/run_local_quality.ps1`
  terminó `QUALITY_GATE=APROBADA` (230 pruebas unitarias, build, auditorías y
  validación CloudFormation). Las cinco pruebas del adaptador ICE también
  pasaron.
- No se desplegó: `s3api head-bucket` fue denegado (HTTP/API 403), por lo que
  ni siquiera se intentó `PutObject`. CloudFormation/ELB/SSM continúan
  denegados; el dominio público da 503. El paquete local no prueba el runtime
  cloud.

El adaptador integra la ruta backend autenticada de configuración ICE; el
relay TURN aún no está provisionado/configurado y WebRTC no está comprobado
entre dos navegadores reales. La v19 queda preparada para publicar al recuperar
permisos AWS, no se debe presentar como desplegada.
