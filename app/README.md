# Aplicación de demostración

Laboratorio local de una interfaz React/Vite y dos servicios para demostrar pedidos, health checks, persistencia y el contrato AWS-Azure sin usar credenciales cloud.

## Interfaz web

La interfaz se encuentra en `web/`. Permite registrar pedidos, consultar pedidos recientes y visualizar el estado de la API y la base de datos. Durante el desarrollo, Vite usa un proxy local hacia Flask para no exponer CORS. Para generar el frontend que Flask servirá en el mismo origen:

```powershell
cd web
pnpm install
pnpm build
```

El build genera `src/static/`. Después de iniciar Flask, `http://localhost:8080/` sirve el portal y `http://localhost:8080/api` mantiene la descripción JSON de la API.

## Servicios y endpoints

Servicio principal (`aws-app`):

- `GET /`: identidad de la instancia.
- `GET /health`: salud del servicio y la base de datos.
- `GET /ready`: disponibilidad de la base de datos y dependencias necesarias.
- `GET /api/orders`: lista de pedidos.
- `POST /api/orders`: crea un pedido con `customer` y `total`.
- `GET /api/multicloud`: consulta la salud del receptor Azure.
- `POST /api/multicloud/sync`: envía un evento al receptor Azure.

Servicio secundario (`azure-service`), simulación local del contrato de Azure Function:

- `GET /health`: salud del servicio autenticado.
- `GET /ready`: readiness autenticado del receptor.
- `POST /api/fulfillment/events`: recibe eventos autenticados e idempotentes.
- `GET /api/events`: enumera eventos recibidos durante la ejecución.

## Pruebas locales

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Simulación con contenedores

```powershell
$env:DEMO_FUNCTION_KEY='reemplace-para-su-prueba-local'
docker compose up --build
```

Prueba de persistencia:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/orders -ContentType application/json -Body '{"customer":"Cliente Demo","total":49.90}'
Invoke-RestMethod -Uri http://localhost:8080/api/orders
```

Prueba multicloud simulada:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/multicloud
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/multicloud/sync -ContentType application/json -Body '{"event_id":"evt-20260925-0001","event_type":"order.created","order_id":101}'
```

## Diferencia entre versión local y versión cloud

La versión local usa SQLite para probar sin infraestructura. La versión AWS desplegada utilizó PostgreSQL/RDS mediante el código incluido en CloudFormation. SQLite no representa la base de datos final.

Actualmente existen dos empaquetados de la aplicación: `app/src` con el build Vite para desarrollo local y un portal estático ligero embebido en `iac/cloudformation/aws-lab.yaml` para el laboratorio. Este último sí permite demostrar el flujo web/API/RDS, pero no equivale a publicar el build Vite versionado. Unificarlos en una imagen versionada es una mejora pendiente para evitar deriva entre ambientes.

La clave predeterminada de Docker Compose es exclusivamente local. Para cualquier demostración compartida debe definirse `DEMO_FUNCTION_KEY` y no publicarse el puerto del receptor fuera del equipo de prueba.
