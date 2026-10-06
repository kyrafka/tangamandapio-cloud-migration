# Manual de evolución local y telefonía IP

**Proyecto:** Tangamandapio S.A.C.
**Corte:** 05/10/2026
**Propósito:** usar esta guía cuando se continúe el portal o se quiera añadir un piloto de telefonía IP. No activa servicios cloud ni crea costos por sí sola.

## 1. Diagnóstico local verificado

| Área | Ya existe | Falta antes de declararlo productivo |
|---|---|---|
| Backend | Flask, sesiones, control de rol en servidor, empresas B2B, auditoría, pedidos, outbox y métricas Prometheus. Las 21 pruebas locales pasan. | MFA/recuperación de contraseña, limitación de intentos, CSRF explícito, rotación de sesión, pruebas de autorización de todos los endpoints y migraciones formales de base de datos. |
| Frontend | React/Vite con inicio de sesión, panel por rol, pedidos, outbox, usuarios, empresas y auditoría. El build de producción pasa. | Estados de carga/error más completos, pruebas de interfaz, accesibilidad con teclado/lector de pantalla, paginación, filtros, edición controlada y diseño móvil validado en dispositivos reales. |
| Integración WMS | Contrato local, outbox, idempotencia y reintento; Function Azure preparada con identidad administrada. | Despacho real AWS→Azure con autenticación entre nubes, cola de reintentos programada y trazabilidad de un mismo `event_id` en ambos proveedores. |
| Observabilidad | Métricas de aplicación, configuración local Prometheus/Grafana/Portainer y recursos de CloudWatch/Azure Monitor definidos. | Dashboards y alertas de un mismo ciclo cloud, prueba de falla y registro de respuesta operativa. |

## 2. Orden recomendado para mejorar portal y backend

### Prioridad 1 — seguridad y operación

1. Desplegar siempre con HTTPS, certificado ACM y cookie `Secure`; el HTTP del laboratorio solo sirve para datos sintéticos.
2. Añadir limitación de intentos de login, bloqueo temporal y registro de acceso fallido.
3. Incluir token CSRF para operaciones que cambian datos y rotar la sesión después del login.
4. Mantener secretos fuera del repositorio: Secrets Manager en AWS y Key Vault en Azure.
5. Añadir migraciones versionadas para PostgreSQL; no depender de crear tablas implícitamente en el arranque.

### Prioridad 2 — experiencia de usuario

1. Agregar filtros por fecha, estado y empresa a pedidos/outbox.
2. Paginar tablas y mostrar estados de carga, vacío y error con acciones de recuperación.
3. Añadir detalle de pedido y una línea de tiempo de evento WMS.
4. Validar navegación con teclado, contraste, foco visible y pantallas móviles.
5. Incorporar pruebas de interfaz para login, rol denegado, pedido y reintento.

### Prioridad 3 — integración y continuidad

1. Despachar el outbox en segundo plano y aplicar reintento exponencial; no depender de la respuesta web del cliente.
2. Correlacionar `request_id`, `event_id`, pedido y usuario en los logs de AWS y Azure.
3. Probar restauración de RDS y objeto versionado de S3; documentar RPO/RTO.
4. Hacer una prueba de carga breve y una prueba de pérdida/reemplazo de un target del ALB.

## 3. Telefonía IP: arquitectura recomendada

La telefonía no debe conectarse directamente a RDS, al portal ni al WMS. Es un dominio de comunicaciones con permisos propios.

```text
Softphone/VPN o teléfono SIP
          |
       TLS/SRTP
          v
PBX Asterisk aislada (piloto local)  ── o ──  Amazon Connect (producción)
          |                                      |
          +-- cola Comercial / Logística          +-- colas, horarios y grabaciones
          |                                      |
          +------------------- API interna de consulta de pedido ----------------+
```

### Decisión de plataforma

| Escenario | Recomendación | Razón |
|---|---|---|
| Práctica sin costo cloud | **Asterisk 20 LTS** en una VM o equipo local aislado, con dos softphones. | Permite aprender extensiones, colas y SIP sin exponer puertos a Internet. |
| Operación empresarial | **Amazon Connect** en AWS, con números/colas gestionados y grabación bajo política corporativa. | Reduce administración de PBX, escala mejor y se integra con el dominio AWS del portal. |
| No recomendado | FreePBX/Asterisk publicado directamente a Internet. | Riesgo alto de fraude SIP, ataques de registro y cargos por llamadas. |

Para el Entregable 1 basta presentar el diseño y, si se desea, un piloto local. Amazon Connect o números telefónicos reales **no se crean sin presupuesto y autorización**, porque pueden generar costo.

## 4. Piloto local con Asterisk

### Preparación

1. Usar una VM Linux aislada o un host de laboratorio con IP privada; reservarle, por ejemplo, `10.20.30.10`.
2. Instalar Asterisk 20 LTS desde el repositorio autorizado de la distribución o desde el paquete corporativo aprobado.
3. Crear únicamente extensiones internas de prueba: `2001` Comercial, `2002` Logística y `700` cola de atención.
4. Instalar Linphone, Zoiper u otro softphone en dos equipos de prueba dentro de la misma VPN/LAN.
5. Crear credenciales largas y diferentes por extensión; se guardan en un gestor de secretos, no en Git ni en capturas.

### Configuración mínima conceptual

En `pjsip.conf`, cada extensión necesita autenticación, un AOR y un endpoint; restringir códecs a G.711 (`ulaw`/`alaw`) para el piloto. Activar TLS/SRTP cuando se use fuera de una LAN de laboratorio.

```ini
[2001-auth]
type=auth
auth_type=userpass
username=2001
password=USAR_UN_SECRETO_UNICO

[2001]
type=endpoint
context=tangamandapio-internal
auth=2001-auth
aors=2001
disallow=all
allow=ulaw

[2001]
type=aor
max_contacts=1
```

En `extensions.conf`, el dialplan debe permitir solo las extensiones y colas necesarias; no incluir rutas salientes PSTN en un piloto.

```ini
[tangamandapio-internal]
exten => 2001,1,Dial(PJSIP/2001,20)
 same => n,Hangup()
exten => 2002,1,Dial(PJSIP/2002,20)
 same => n,Hangup()
exten => 700,1,Queue(comercial,tT)
 same => n,Hangup()
```

### Seguridad de red

- Permitir SIP solo desde la subred VPN/LAN aprobada. Para TLS usar 5061; no publicar UDP 5060 globalmente.
- Restringir RTP al rango configurado de Asterisk —normalmente 10000–20000 UDP— únicamente a clientes VPN/LAN.
- Deshabilitar llamadas internacionales/PSTN hasta que exista una política de fraude y presupuesto.
- Aplicar Fail2ban, actualizaciones periódicas, contraseñas únicas, límite de registros y logs centralizados.
- Proteger grabaciones con cifrado, control de acceso, retención definida y aviso/consentimiento conforme a la política de la empresa.

### Pruebas y evidencias del piloto

1. Registrar 2001 y 2002 desde dos softphones; capturar ambos como `Registered` sin mostrar contraseña.
2. Llamar 2001→2002 y comprobar audio bidireccional.
3. Llamar 700 y comprobar enrutamiento a la cola.
4. Mostrar en Asterisk CLI el canal activo y, luego, que la llamada terminó.
5. Capturar reglas de red/VPN y confirmar que no hay puertos SIP expuestos a Internet.
6. Guardar fecha, red de laboratorio, versión de Asterisk, resultado y cierre del piloto.

## 5. Paso a producción con Amazon Connect

1. Definir propietarios de negocio, horario, colas Comercial/Logística, idioma, grabación, retención y protocolo de atención.
2. Aprobar presupuesto, región, número telefónico y política de llamadas salientes antes de crear el servicio.
3. Configurar flujos de contacto, perfiles de seguridad y SSO; otorgar a agentes solo sus colas.
4. Integrar el portal mediante una API interna de consulta de pedido de solo lectura. La telefonía nunca obtiene acceso directo a la base de datos.
5. Enviar métricas al plano de observabilidad AWS y probar cola, transferencia, caída de agente y retención de grabación.
6. Documentar costo estimado por minuto, alertas de gasto y procedimiento de desactivación.

## 6. Definición de terminado para telefonía IP

Un piloto se considera terminado solo si registra dos extensiones, una llamada interna bidireccional, una cola, controles de red, evidencia real y cierre. La producción se considera terminada cuando además existe gobierno de identidades, política de grabación, control de costos, monitoreo y prueba de recuperación.
