# Matriz de cumplimiento vigente

| Criterio | Evidencia/meta actual | Fase que lo cierra |
|---|---|---|
| Análisis y requisitos | Caso, problema, RF/RNF y restricciones en el registro maestro | Core/documento final |
| Arquitectura | Diagrama lógico, físico, AWS, OCI y multicloud actualizados | AWS + OCI |
| VPC/VCN | VPC AWS segmentada; VCN OCI pendiente | AWS + OCI |
| Cómputo, storage y BD | AWS transaccional; Azure WMS; OCI continuidad | AWS + Azure + OCI |
| Seguridad | SG/NSG, IAM/RBAC, cifrado, secretos, TLS y pruebas de denegación | Todas |
| HA/escalabilidad | ALB, ASG, prueba de caída y reemplazo | AWS |
| Observabilidad | CloudWatch y OCI Monitoring; Azure telemetría complementaria | AWS + Azure + OCI |
| IaC | CloudFormation AWS, Terraform Azure/OCI y ejecuciones reales | Todas |
| Backup/RTO/RPO | Restore real y tiempos medidos | AWS + OCI |
| Multicloud | Flujo integrado AWS–OCI real; Azure WMS como valor adicional | OCI |
| Costos | Estimación, inventario inicial/final y limpieza | Todas |
| Pruebas | Evidencias CUR por categoría | Todas |
| Documentación/defensa | Informe, diagramas, anexos y demo reproducible | Cierre |
