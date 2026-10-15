# ARCHIVO — Fase OCI (fuera del alcance acordado)

> Este plan es un antecedente del enfoque AWS–OCI y está **supersedido** por el
> alcance AWS + Azure comunicado por el usuario. No crear VCN, Object Storage,
> cómputo ni integración AWS–OCI a partir de este archivo. La discrepancia con
> los documentos académicos escritos y su efecto en la rúbrica se registra en
> [la evaluación vigente](10_evaluacion_rubrica_entregable_final_2026-10-08.md).

El contenido que sigue se conserva únicamente como historial de decisiones,
no como trabajo pendiente vigente.

## Alcance propuesto

- VCN con CIDR distinto al AWS, subred pública y privada, route tables, Internet/NAT Gateway y NSG de mínimo privilegio.
- Object Storage cifrado como destino de respaldo o evidencia de recuperación.
- Recurso de cómputo/servicio mínimo de recuperación, solo si la cuenta/cuota lo permite.
- OCI Monitoring y evidencia de inventario, configuración de red y costos.
- Integración AWS–OCI autenticada y cifrada para una copia de respaldo o evento sintético, con prueba de recuperación.

## Criterio de aceptación

No basta crear recursos en ambas nubes. Debe existir un flujo demostrable AWS -> OCI, autenticación/secretos controlados, objeto o dato recibido, logs en ambos extremos y una recuperación o lectura validada.
