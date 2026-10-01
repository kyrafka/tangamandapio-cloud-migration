# Registro maestro — núcleo vigente

**Proyecto:** Diseño e implementación de un centro de datos cloud empresarial para Tangamandapio S.A.C.  
**Alumno:** Jose Dario Zuñiga Medina — 202310610  
**Docente:** Fernando Manuel Asin Gomez  
**Corte:** 30/09/2026

## 1. Caso y objetivo

Tangamandapio S.A.C. es una empresa ficticia peruana de distribución mayorista, retail omnicanal y logística regional. Cuenta con 450 colaboradores, sedes/centros de distribución en Lima, Arequipa y Trujillo, 220 usuarios internos y picos de hasta 3,000 clientes u operadores externos concurrentes durante campañas.

Su datacenter centralizado concentra portal B2B, pedidos, inventario, despacho, archivos, reportes e identidad. La migración elimina puntos únicos de falla, segmenta redes, protege datos, permite crecer por demanda y habilita continuidad comprobable sin detener el negocio.

## 2. Arquitectura objetivo

```text
Clientes y operadores
        |
Internet -> seguridad/HTTPS -> AWS ALB -> Vite/Nginx + API escalable -> RDS PostgreSQL privada
                                                   |                         |
                                                   +-> S3 documentos          +-> outbox de eventos
                                                                                     |
                                                                          TLS + event_id
                                                                                     v
Azure Function -> Storage Queue -> WMS/despacho -> Blob privado -> Monitor/Log Analytics

OCI (fase posterior): VCN segmentada + continuidad/backup/recuperación e integración AWS–OCI.
```

La solución es **híbrida** mientras datacenter y sedes coexisten con la nube, y **multicloud** porque cada proveedor recibe una responsabilidad empresarial concreta. No se usará una nube privada.

## 3. Responsabilidad por proveedor

| Proveedor | Dominio | Recursos de demostración |
|---|---|---|
| AWS | Venta y transacción crítica | VPC, ALB, ASG/EC2, RDS PostgreSQL, S3, IAM/Secrets Manager, CloudWatch y mecanismo outbox/reintento |
| Azure | Cumplimiento logístico asíncrono | Function, Storage Queue, Blob privado, Managed Identity/RBAC, Key Vault, Log Analytics y Application Insights |
| OCI | Continuidad y criterio VCN/multicloud | VCN, subredes, NSG, Object Storage/backup, monitoreo y prueba de integración segura con AWS |

Azure es un complemento operativo real. OCI no se sustituye: se implementará antes del cierre final para responder a la exigencia AWS–OCI/VCN de la plantilla y rúbrica.

## 4. Reglas de verdad

1. Diseño, código y despliegue son estados distintos; nunca se presentan como equivalentes.
2. Toda prueba debe incluir captura, fecha, nube, región, recurso, configuración, resultado y limpieza cuando aplique.
3. No se almacenan contraseñas, tokens, claves, DNS efímeros, cuentas ni datos personales en repositorio, capturas o informe.
4. Cada ventana de nube tiene: inventario previo -> validación IaC -> despliegue -> pruebas -> evidencia -> eliminación/apagado -> inventario final.
5. Los antecedentes de `evidence/legacy/` sirven para rescatar procedimientos, no para demostrar este núcleo.

## 5. Estado inicial verificable

| Área | Estado | Límite de la afirmación |
|---|---|---|
| AWS | Plantilla CloudFormation y procedimiento validados; laboratorio finalizado | La credencial AWS Academy denegó describir o eliminar recursos; no se afirma cierre del stack actual sin inventario verificable |
| Azure | Vertical WMS temporal aplicado en West US | Se crearon 12 recursos; Functions registradas, pero la invocación HTTP devolvió 500 y el cierre está pendiente |
| OCI | No iniciado | No hay VCN ni integración real |
| Aplicación | Código y pruebas locales disponibles | No se declara publicación cloud hasta validarla detrás del ALB |

## 6. Definición de terminado

El proyecto queda listo para sustentar solo cuando demuestre: aplicación y persistencia reales, segmentación de red, control de seguridad, balanceo/HA, observabilidad, recuperación probada, IaC reproducible, costos/cierre y una integración real entre AWS y OCI. Azure fortalece el caso WMS, pero no reemplaza esa última condición.

## 7. Actualización de ejecución — 30/09/2026

La evidencia AWS se mantiene separada entre el piloto histórico y el preflight vigente. La sesión final de AWS Academy presentó una denegación explícita para describir o borrar recursos de CloudFormation; por tanto, el proyecto no afirma que el stack actual fue desplegado, probado o eliminado en esa sesión sin un inventario verificable.

En Azure, Terraform aplicó el vertical WMS temporal en West US y creó 12 recursos. Tras corregir el empaquetado, el host registró `HttpHealth` y `HttpFulfillment`; ambas rutas devolvieron HTTP 500 con clave válida. No se declara la persistencia Blob/Queue ni la integración AWS-Azure como aprobadas. Los registros actuales están en [evidence/current/azure](../evidence/current/azure/README.md); el cierre sigue pendiente de autenticación CLI, destrucción y comprobación de inventario cero.
