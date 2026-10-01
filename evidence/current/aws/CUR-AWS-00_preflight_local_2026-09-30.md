# CUR-AWS-00 — Preflight local previo a AWS

**Fecha:** 30/09/2026  
**Alcance:** preparación técnica local; este registro no sustituye las capturas ni las pruebas realizadas en AWS Academy.

| Verificación | Resultado real |
|---|---|
| Pruebas de aplicación | `15` pruebas unitarias ejecutadas con éxito mediante `tests/run_local_quality.ps1`. Incluyen salud, pedidos, validación de entrada, cabeceras defensivas, página del portal y receptor de eventos Azure simulado. |
| Portal local | La ruta `/` identifica a Tangamandapio S.A.C.; se comprobó con prueba automatizada. |
| Plantilla AWS | Revisión estática: sin identificadores AndeMarket; define portal B2B, seis subredes en dos AZ y RDS PostgreSQL privada. Los bloques de UserData están completos. |
| Validación CloudFormation | Pendiente de ejecutar dentro de la sesión temporal de AWS Academy (`aws cloudformation validate-template`). La CLI local no tiene credenciales temporales cargadas. |
| Terraform | No se declara validado: el lock de proveedores requiere conciliación y este equipo no puede alcanzar el registro de Terraform. No se aplicó ningún recurso. |

## Condición para continuar

Abrir CloudShell dentro de una sesión activa de AWS Academy. Allí se validará la plantilla y, antes de crear el stack, se revisarán región, inventario inicial y los recursos con costo (NAT Gateway, ALB, EC2 y RDS).

