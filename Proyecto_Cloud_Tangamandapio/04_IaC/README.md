# Infraestructura como código

| Herramienta | Responsabilidad | Guía |
|---|---|---|
| CloudFormation | VPC, ALB, ASG, RDS, WAF, alarmas y pilas auxiliares en AWS. | [Uso de CloudFormation](cloudformation/README.md) |
| Terraform y ARM OneDeploy | Red y servicios base de Azure, Function Flex privada y conectividad. OneDeploy publica el WMS. | [Uso de Terraform](terraform/README.md) |

## Orden de reconstrucción

1. Verificar cuenta AWS, suscripción Azure, backend y credenciales temporales.
2. Preparar los servicios base y la red de Azure. Crear la Function Flex y publicar el ZIP del WMS.
3. Crear el stack AWS con artefacto del ERP, certificado ACM, hostname y referencia al secreto de la Function.
4. Restablecer Tailscale, DNS privado y ruta a 10.20.1.4. Verificar HTTPS desde ambas EC2.
5. Reinstalar la copia diaria y comprobar un pedido y una restauración aislada.

Cada pila auxiliar debe tener un solo propietario de cambios, según el estado de Terraform o CloudFormation. El [orden detallado](../../iac/README.md#orden-de-reconstrucción) enumera las dependencias.

## Evidencia para el criterio 8

La descripción del proyecto pide automatizar parte de la infraestructura. La rúbrica reconoce la automatización de una parte relevante y valora, en el nivel superior, la infraestructura reproducible y el código organizado.

El stack principal y las pilas auxiliares de AWS están desplegados con CloudFormation. Terraform administra los servicios compartidos de Azure y la infraestructura de la Function Flex privada. El [ensayo en el emulador](../../evidence/current/aws/AWS-IAC-EMULATOR-2026-11-19.json) verificó el subconjunto de red y S3. Esa prueba acredita el subconjunto indicado. Un ensayo integral desde cuentas vacías queda como ampliación.
