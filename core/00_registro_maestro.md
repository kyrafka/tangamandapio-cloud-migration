# Registro maestro — núcleo vigente

**Proyecto:** Diseño e implementación de un centro de datos cloud empresarial para Tangamandapio S.A.C.  
**Alumno:** Jose Dario Zuñiga Medina — 202310610  
**Docente:** Fernando Manuel Asin Gomez  
**Corte:** 02/10/2026

## 1. Caso y objetivo

Tangamandapio S.A.C. es una empresa ficticia peruana de distribución mayorista, retail omnicanal y logística regional. Cuenta con 450 colaboradores, sedes/centros de distribución en Lima, Arequipa y Trujillo, 220 usuarios internos y picos de hasta 3,000 clientes u operadores externos concurrentes durante campañas.

Su datacenter centralizado concentra portal B2B, pedidos, inventario, despacho, archivos, reportes e identidad. La migración elimina puntos únicos de falla, segmenta redes, protege datos, permite crecer por demanda y habilita continuidad comprobable sin detener el negocio.

## 2. Arquitectura objetivo

```text
Clientes y operadores
        |
Internet -> seguridad/HTTPS objetivo -> AWS ALB -> Portal B2B + API escalable -> RDS PostgreSQL privada
                                                   |                         |
                                                   +-> S3 documentos          +-> outbox de eventos
                                                                                     |
                                                                          TLS + event_id
                                                                                     v
Azure Function -> Storage Queue -> WMS/despacho -> Blob privado -> Monitor/Log Analytics
```

La solución es **híbrida** mientras datacenter y sedes coexisten con la nube, y **multicloud** porque cada proveedor recibe una responsabilidad empresarial concreta. No se usará una nube privada.

## 3. Responsabilidad por proveedor

| Proveedor | Dominio | Recursos de demostración |
|---|---|---|
| AWS | Venta y transacción crítica | VPC, ALB, ASG/EC2, RDS PostgreSQL, S3, IAM/Secrets Manager, CloudWatch y mecanismo outbox/reintento |
| Azure | Cumplimiento logístico asíncrono | Function, Storage Queue, Blob privado, Managed Identity/RBAC, Key Vault, Log Analytics y Application Insights |

Azure es un dominio operativo real para el WMS. OCI está fuera del alcance acordado del Entregable 1 y no se presenta como recurso implementado ni pendiente obligatorio.

## 4. Reglas de verdad

1. Diseño, código y despliegue son estados distintos; nunca se presentan como equivalentes.
2. Toda prueba debe incluir captura, fecha, nube, región, recurso, configuración, resultado y limpieza cuando aplique.
3. No se almacenan contraseñas, tokens, claves, DNS efímeros, cuentas ni datos personales en repositorio, capturas o informe.
4. Cada ventana de nube tiene: inventario previo -> validación IaC -> despliegue -> pruebas -> evidencia -> eliminación/apagado -> inventario final.
5. Los antecedentes de `evidence/legacy/` sirven para rescatar procedimientos, no para demostrar este núcleo.

## 5. Estado inicial verificable

| Área | Estado | Límite de la afirmación |
|---|---|---|
| AWS | Portal B2B versionado publicado temporalmente con CloudFormation; ALB/ASG, RDS privada, S3 y Secrets Manager verificados durante el recambio | La ejecución alcanzó `UPDATE_COMPLETE` el 02/10. Tras el reinicio de laboratorio, no hay una pila activa; falta reprovisionar y ejecutar la prueba posterior de login/roles |
| Azure | El ciclo inicial fue eliminado; el vertical WMS vigente está en West US con siete recursos PaaS: Function, Storage, Key Vault, Application Insights, Log Analytics, plan y grupo de alertas | La Function aparece en ejecución. Se debe repetir el flujo Health/Fulfillment del ciclo vigente tras cualquier cambio de código y cerrar costos solo con autorización |
| Aplicación | Portal B2B publicado temporalmente detrás del ALB | Health 200, pedido 201 y consulta 200 verificados; URL efímera, no se declara servicio permanente |

## 6. Definición de terminado

El proyecto queda listo para sustentar cuando demuestre: aplicación y persistencia reales, segmentación de red, control de seguridad, balanceo/HA, observabilidad, IaC reproducible y costos/cierre. La siguiente mejora funcional es conectar el outbox real de AWS con el receptor WMS validado en Azure.

## 7. Actualización de ejecución — 01/10/2026

AWS validó la plantilla CloudFormation y creó el stack temporal. Antes de que AWS Academy cancelara la credencial local, se verificaron dos targets ALB `healthy`, RDS PostgreSQL privada/cifrada, S3 con bloqueo público, dashboard y alarmas, además de `GET /health` 200, `POST /api/orders` 201 y `GET /api/orders` 200. La evidencia está en [evidence/current/aws](../evidence/current/aws/CUR-AWS-03_despliegue_y_prueba_2026-10-01.md). La cancelación ocurrió después de las pruebas: no se afirma inventario cero hasta renovar la sesión y ejecutar el cierre.

En Azure, Terraform validó y aplicó el vertical temporal en West US. Tras corregir el empaquetado remoto Linux y el TTL de Queue, `HttpHealth` devolvió 200, `HttpFulfillment` aceptó el evento con 202, el reenvío devolvió 200 por idempotencia y se verificaron el objeto Blob y el mensaje Queue. Los registros están en [evidence/current/azure](../evidence/current/azure/README.md). Posteriormente se eliminaron los dos Resource Groups de Tangamandapio y la consulta final por prefijo no devolvió recursos.

## 8. Publicación B2B en AWS — 02/10/2026

Se publicó el artefacto versionado del portal B2B en el bucket privado del stack y se actualizó el Launch Template para descargarlo en cada nodo del ASG. El primer change set revirtió de forma automática porque el secreto de sesión declaraba una clave generada sin el objeto JSON base exigido por Secrets Manager. No se sustituyeron VPC, ALB ni RDS; el rollback eliminó únicamente los secretos nuevos incompletos y mantuvo la infraestructura previa.

Corregida la plantilla con `SecretStringTemplate: '{}'`, CloudFormation la validó y el segundo change set terminó `UPDATE_COMPLETE` a las **11:56 a. m. (America/Chicago)**. Durante el recambio gradual, `GET /health` respondió HTTP 200 e indicó `database=ok`. El registro técnico completo está en [CUR-AWS-10](../evidence/current/aws/CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md).

Después de reiniciar el laboratorio, la consola de CloudFormation muestra **Pilas (0)** al filtrar Tangamandapio y el nombre DNS del ALB de esa ejecución ya no resuelve. Por ello esta publicación se conserva como evidencia técnica histórica del ciclo, no como infraestructura actualmente activa. La siguiente ejecución debe reprovisionar el stack con una credencial AWS Academy vigente y entonces repetir, con capturas reales, login/roles, rutas protegidas y los dos targets saludables.
