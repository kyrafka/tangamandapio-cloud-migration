from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables"
TEMPLATE = Path(r"C:\Users\Diego\Downloads\plantilla_proyecto_cloud_z3lbe8bgxs (5).docx")
EXPECTED_TEMPLATE_SHA256 = "e9adfcf1cf72be760c4f70a1aecc2d5a9833b5cde3d83dd6476543460a6cddce"
REPORT = OUT / "Proyecto_Final_Tangamandapio_2026-11-19.docx"
MANUAL = OUT / "Manual_Tecnico_Tangamandapio_2026-11-19.docx"


def set_paragraph(paragraph, value: str) -> None:
    first_rpr = deepcopy(paragraph.runs[0]._r.rPr) if paragraph.runs and paragraph.runs[0]._r.rPr is not None else None
    paragraph.clear()
    run = paragraph.add_run(value)
    if first_rpr is not None:
        run._r.insert(0, first_rpr)


def set_cell(cell, value: str) -> None:
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph = cell.paragraphs[0]
    set_paragraph(paragraph, value)
    for extra in list(cell.paragraphs[1:]):
        extra._element.getparent().remove(extra._element)


def set_table(table, rows: list[list[str]]) -> None:
    if len(rows) > len(table.rows):
        raise ValueError(f"Table has {len(table.rows)} rows; requested {len(rows)}")
    for ri, values in enumerate(rows):
        if len(values) != len(table.columns):
            raise ValueError(f"Table row {ri} has {len(values)} values; expected {len(table.columns)}")
        for ci, value in enumerate(values):
            set_cell(table.cell(ri, ci), value)


def set_update_fields(document) -> None:
    settings = document.settings._element
    existing = settings.find(qn("w:updateFields"))
    if existing is None:
        existing = OxmlElement("w:updateFields")
        settings.append(existing)
    existing.set(qn("w:val"), "true")


def insert_current_verification(document, before_text: str) -> None:
    """Keep the original design sections and lead with the current measurements."""
    following = next(p for p in document.paragraphs if p.text == before_text)
    heading = document.add_paragraph("Verificación operativa del 19 de noviembre de 2026")
    heading.style = following.style
    following._p.addprevious(heading._p)
    for lead, body in (
        ("Portal y permisos. ", "Se recuperó el administrador y se corrigió el destino DNS del portal. Hubo 32 lecturas HTTP 200, 42 comprobaciones de acceso del portal y 48 comprobaciones del ERP. El correo interno llegó y se marcó como leído."),
        ("Pedido y seguimiento. ", "El pedido sintético SEGUIMIENTO-DEMO-20261119-151352 recibió HTTP 201 en 61 ms. Por la ruta privada pasó de pendiente a en cola y procesado. El mismo evento se verificó en Function, Queue, Blob e Insights. Seis roles consultan el flujo. Operaciones y Administración ven las colas."),
        ("Conmutación. ", "En dos ensayos tras ajustar el monitor, el respaldo tomó la ruta en 3,21 y 8,20 s. El primer HTTP 200 completo llegó a 4,59 y 6,59 s en el primer ensayo y a 9,88 y 9,92 s en el segundo. El principal recuperó la ruta automáticamente en los dos casos. La meta de 3 s sigue pendiente."),
        ("Recuperación. ", "Systems Manager programa un respaldo cifrado diario a las 03:00 de Lima. La restauración de la copia actual en PostgreSQL aislado recuperó 20 tablas, un pedido y un evento en 35,108 s. La autorización de Blob debe renovarse al vencimiento."),
        ("Administración. ", "El administrador descarga las copias de Azure y puede respaldar pedidos y outbox en S3. En la prueba, el SHA-256 de la copia manual coincidió. El portal llevó al ASG de dos a tres destinos sanos y AWS volvió a dos automáticamente."),
        ("Carga y reconstrucción. ", "La prueba acotada al ALB sostuvo 25 usuarios virtuales durante dos minutos, con 3.013 solicitudes sin fallos y p95 de 190 ms. El 1,47 % anterior se desglosó en 4.399 fallos de transporte y ocho 502. En Moto, Terraform creó y eliminó 17 recursos y CloudFormation identificó 21 recursos de red y S3. Moto registró las tres capacidades solicitadas y sus acciones de regreso."),
        ("Telefonía. ", "Dos clientes locales intercambiaron audio WebRTC sintético en ambos sentidos. Falta validar el audio entre redes restrictivas. TURN aún no está configurado."),
        ("Costos y defensa. ", "Los presupuestos registraron USD 10,47 de USD 200 en AWS y USD 8,80 de USD 25 en Azure. RDS permanece en Single-AZ. Queda medir RPO, demostrar recuperación regional y presentar las fotos y la constancia docente para AWS–Azure."),
    ):
        paragraph = document.add_paragraph()
        paragraph.add_run(lead).bold = True
        paragraph.add_run(body)
        following._p.addprevious(paragraph._p)
    sources = document.add_paragraph("El registro iac/ESTADO_REAL_2026-11-19.md enlaza la evidencia de cada prueba y la matriz de la rúbrica.")
    following._p.addprevious(sources._p)
    following.paragraph_format.page_break_before = True


PARAGRAPHS = {
    1: "Universidad Peruana Unión",
    2: "Facultad de Ingeniería y Arquitectura · Escuela Profesional de Ingeniería de Sistemas",
    5: "TÍTULO DEL PROYECTO: Diseño e implementación de una arquitectura cloud empresarial AWS–Azure para Tangamandapio",
    6: "EMPRESA FICTICIA: Tangamandapio, distribuidora nacional",
    7: "INTEGRANTES: Jose Dario Zuñiga Medina",
    8: "DOCENTE: Fernando Manuel Asin Gomez",
    9: "CICLO ACADÉMICO: 8",
    10: "FECHA DE CORTE TÉCNICO: 19 de noviembre de 2026",
    12: "Informe técnico basado en el despliegue y las pruebas verificadas al 19/11/2026. El equipo incorporará fotografías y capturas de la demostración final.",
    15: "El índice se actualiza al abrir este archivo en Microsoft Word: Referencias → Actualizar tabla → Actualizar toda la tabla.",
    18: "Este proyecto modela una distribuidora ficticia con una operación de ventas, compras e inventario que requiere un portal B2B y un WMS integrado.",
    19: "La infraestructura desplegada combina componentes IaaS y PaaS. Se separa el estado observado del diseño deseado y de las pruebas aún pendientes.",
    20: "Empresa: distribuidora ficticia con 450 trabajadores, tres centros y hasta 3.000 clientes u operadores en escenarios pico; son requisitos del caso, no usuarios medidos.",
    21: "Problema: capacidad y recuperación limitadas, respaldos insuficientes, visibilidad parcial y dependencia de una red centralizada.",
    22: "Solución: portal ERP web detrás de WAF y ALB, Auto Scaling de EC2 y RDS PostgreSQL; Azure Functions Flex, Storage Queue, Blob y Application Insights.",
    23: "Modelos: IaaS para EC2/VNet/VPC; PaaS para RDS, Azure Functions y almacenamiento administrado; SaaS para la consola de administración cloud.",
    24: "Proveedores desplegados: AWS y Microsoft Azure. OCI no está desplegado; la sustitución AWS–Azure requiere constancia escrita del docente porque la rúbrica base menciona AWS–OCI.",
    25: "Componentes comprobados: AWS CloudFormation, VPC, ALB, WAF, ASG, RDS, S3, CloudWatch/SNS; Azure Function Flex privada, Private Endpoint, Queue, Blob, Key Vault y Application Insights.",
    26: "Resultado: el ASG escaló automáticamente de 2 a 5 y volvió a 2; un postcheck de 3.000 solicitudes tuvo cero errores. La carga larga registró 1,47% de errores y no aprobó el umbral de 1%.",
    27: "Se verificaron el pedido privado, el respaldo diario cifrado y la restauración aislada. La recuperación regional queda pendiente.",
    31: "Tangamandapio es un caso académico ficticio de distribución mayorista. Las cifras describen supuestos del enunciado y no datos de una empresa real.",
    32: "Nombre: Tangamandapio (empresa ficticia).",
    33: "Rubro: distribución mayorista y abastecimiento de productos.",
    34: "450 trabajadores estimados para el escenario académico.",
    35: "Tres centros de distribución como supuesto de diseño.",
    36: "Hasta 3.000 clientes/operadores concurrentes es el requisito pico declarado; no ha sido validado por una prueba de usuarios concurrentes.",
    37: "Sedes: tres centros nacionales sin ciudades fijadas en la documentación de origen.",
    38: "Operación propuesta: comercial diaria con picos por campañas; horario exacto pendiente de definición por el equipo.",
    39: "Servicios: portal ERP B2B, ventas/compras, control de inventario WMS, base de datos, archivos, alertas y recuperación de desastres.",
    41: "Modelo funcional supuesto para el caso; no representa una planilla real:",
    42: "Gerencia coordina Administración, Finanzas, Comercial, Operaciones/Almacén, Compras, Atención al cliente y Tecnología.",
    43: "Gerencia general",
    44: "Administración y finanzas",
    45: "Comercial y ventas",
    46: "Compras y abastecimiento",
    47: "Operaciones y almacén",
    48: "Atención al cliente y distribuidores",
    49: "Tecnología y seguridad",
    50: "Organigrama textual: Gerencia → Administración/Finanzas · Comercial/Ventas · Compras · Operaciones/Almacén · Atención al cliente · TI/Seguridad.",
    52: "Servicios digitales del escenario: portal B2B, ERP comercial, gestión de inventario WMS, identidad, base transaccional, archivos, alertas y recuperación.",
    53: "Componentes que tienen evidencia local o cloud:",
    54: "Portal web empresarial y panel de administración por rol.",
    55: "Ventas y Cliente B2B registran pedidos con SKU y cantidad. El avance se consulta por rol.",
    56: "ERP integrado en el portal; persistencia PostgreSQL administrada.",
    57: "Maestros sintéticos de clientes, proveedores y productos.",
    58: "Amazon RDS for PostgreSQL en red privada.",
    59: "Panel administrativo y permisos de aplicación con control servidor.",
    60: "S3 conserva artefactos, archivos y respaldos manuales. Azure Blob conserva eventos WMS y respaldos diarios.",
    61: "RDS retiene un día. Systems Manager exporta una copia cifrada diaria a Blob.",
    62: "WMS implementado en Azure Functions Flex con Queue, Blob y Application Insights.",
    65: "La situación anterior es un supuesto académico de infraestructura centralizada y con poca resiliencia. La implementación cloud no migra datos reales de una empresa; usa maestros y transacciones sintéticas.",
    66: "Estado del despliegue al 19/11/2026:",
    67: "AWS: dos instancias EC2 actuales en un ASG, con min 2 y max 5.",
    68: "Amazon Linux 2023 en EC2; las dos VM-router de Azure usan Linux.",
    69: "Portal ERP B2B en AWS; WMS HTTP API en Azure Functions Flex.",
    70: "PostgreSQL 18.3 administrado por RDS; db.t3.micro, 20 GiB, privada, cifrada, Single-AZ.",
    71: "S3 cifrado/versionado en AWS; Azure Storage privado con Blob y colas.",
    72: "VPC 10.10.0.0/16 y VNet 10.20.0.0/16. Dos routers AWS y dos Azure sostienen la ruta privada a 10.20.1.4/32.",
    73: "El portal público llega al ALB AWS por HTTPS/443; HTTP/80 redirige a HTTPS. La ruta pública a la Function está deshabilitada.",
    74: "WAF protege el ALB. Se verificaron HTTPS y la sesión por el dominio público tras actualizar el DNS.",
    75: "Se restauró la copia diaria cifrada de PostgreSQL en un entorno aislado en 35,108 s.",
    76: "Gmail recibió avisos de AWS y uno de Azure Monitor. UPeU sigue pendiente.",
    78: "Problema técnico: cómo mantener disponible y protegida una aplicación de distribución que escale horizontalmente y conecte un WMS privado, con recuperación verificable y un presupuesto académico controlado.",
    81: "Brechas técnicas que el diseño intenta reducir, con alcance medido:",
    82: "Problemas del escenario académico, no hallazgos de una compañía real:",
    83: "Punto único de fallo en una instalación centralizada.",
    84: "Capacidad rígida en picos de ventas y consultas.",
    85: "Segmentación de aplicaciones, datos y servicios externos incompleta.",
    86: "Sin redundancia de aplicación entre dominios de fallo.",
    87: "Respaldo manual sin restauración probada.",
    88: "Poca observabilidad de errores y dependencias.",
    89: "Credenciales y acceso administrativo requieren políticas operativas controladas.",
    90: "Exposición directa de servicios de datos sería inaceptable.",
    91: "Escalabilidad horizontal no demostrada hasta completar una carga de estrés aceptable.",
    92: "Costos variables de NAT, WAF, ALB, RDS y VM Azure deben compararse con el crédito real.",
    95: "Requisitos funcionales de la solución:",
    96: "Códigos RF del equipo; los resultados se contrastan con la matriz de pruebas.",
    97: "RF01. Publicar un portal ERP con autenticación y permisos por rol.",
    98: "RF02. Persistir datos de negocio en PostgreSQL privado y cifrado.",
    99: "RF03. Procesar pedidos en el WMS privado con función autenticada, cola, evidencias y seguimiento por rol.",
    100: "RF04. Conservar respaldos cifrados y repetir la restauración en un entorno aislado.",
    101: "Requisitos no funcionales medibles:",
    102: "Objetivos y condición de evidencia:",
    103: "Disponibilidad: dos AZ para aplicación; RDS Single-AZ es punto pendiente.",
    104: "Rendimiento: latencia p95 y tasa de errores registradas por prueba.",
    105: "Escalabilidad: ASG entre 2 y 5 nodos; 3.000 usuarios simultáneos no medidos.",
    106: "Seguridad mediante WAF, cifrado, permisos por rol y TLS verificado para el portal y el WMS privado.",
    107: "Restauración aislada observada en 35,108 s. Queda medir el RPO y validar recuperación regional.",
    108: "Mantenibilidad: infraestructura repetible y parámetros no secretos.",
    109: "Observabilidad: métricas, logs, alarmas y seguimiento de identificador de evento.",
    110: "Presupuesto de USD 200 en AWS y USD 25 mensuales en Azure. Ambos notifican.",
    114: "Restricciones conocidas:",
    115: "AWS Free Plan registró USD 150,59 de crédito restante. El crédito y los presupuestos tienen cortes distintos.",
    116: "Servicios desplegados: AWS y Azure. La rúbrica base exige AWS–OCI; falta aprobación escrita para la alternativa Azure.",
    117: "AWS us-east-2; Azure West US. No existe región secundaria lista para restaurar.",
    118: "Amazon Linux 2023 en EC2; Linux en routers Azure; PostgreSQL 18.3.",
    119: "CloudFormation, Terraform, Python, portal ERP y Azure Functions Flex.",
    120: "Los presupuestos notifican. Las consultas de gasto tienen retraso.",
    121: "El inventario y las pruebas se consolidaron al 19/11/2026.",
    123: "La aplicación se ejecuta en EC2 (IaaS). RDS PostgreSQL, Functions Flex, Storage y Application Insights son servicios administrados (PaaS). No se inventa una aplicación SaaS de terceros.",
    124: "La selección reduce administración de sistema operativo para base/funciones y conserva control del portal donde hay requisitos de red y runtime.",
    127: "Nube pública en dos proveedores con integración privada mediante routers Tailscale.",
    128: "AWS: nube pública regional us-east-2.",
    129: "No hay nube privada propiedad del proyecto.",
    130: "No es híbrida con centro de datos propio.",
    131: "AWS–Azure funciona por ruta privada. La rúbrica nombra AWS–OCI y la alternativa requiere aceptación docente escrita.",
    133: "El portal tiene un ingreso público y el WMS tiene un ingreso privado.",
    135: "Diagrama lógico de la solución desplegada:",
    136: "Usuarios → Cloudflare → WAF/ALB HTTPS → ASG EC2 (2–5) → RDS privada.",
    137: "ERP → pedido y outbox en RDS → routers Tailscale → Private Endpoint 10.20.1.4 → Function Flex → Queue → Blob e Insights.",
    139: "Inventario cloud observado:",
    140: "AWS (cuenta 481056890449) y Azure for Students.",
    141: "AWS us-east-2; Azure West US.",
    142: "AWS us-east-2a y us-east-2b para EC2; RDS en us-east-2b. Azure West US.",
    143: "VPC 10.10.0.0/16 y VNet 10.20.0.0/16.",
    144: "AWS: públicas 10.10.0.0/24 y 10.10.1.0/24; app 10.10.10.0/24 y 10.10.11.0/24; DB 10.10.20.0/24 y 10.10.21.0/24. Azure: cuatro subredes, ver sección de direccionamiento.",
    145: "AWS tiene Internet Gateway y un NAT Gateway compartido. Azure usa VNet y Private Endpoint sin NAT Gateway.",
    146: "AWS tiene dos EC2 de aplicación y dos routers Tailscale. Azure tiene dos VM-router.",
    147: "RDS PostgreSQL 18.3 Single-AZ; Azure Key Vault existe, no es base de datos.",
    148: "Buckets S3 y Azure Blob/Queues.",
    149: "ALB público en AWS.",
    150: "AWS WAF, security groups, IAM role, Secrets Manager, Azure Private Endpoint/Key Vault y alertas.",
    152: "Las tablas de aplicación apuntan el destino privado WMS a la ENI del router activo.",
    153: "Internet → WAF/ALB HTTPS/443 → ASG privado en dos AZ → RDS Single-AZ. El ERP resuelve el WMS a 10.20.1.4.",
    155: "No hay OCI en la infraestructura desplegada; no existe diagrama de recursos OCI reales.",
    156: "No se dibuja una topología OCI ficticia. Si el docente exige OCI, debe aprobarse el alcance y desplegarse/probarse antes de la defensa.",
    157: "8.5 Arquitectura híbrida y multinube AWS–Azure",
    158: "Se verificó un pedido desde AWS correlacionando el identificador en Function, Queue, Blob y Application Insights.",
    159: "El portal mostró pendiente → en cola → procesado. Operaciones y Administración observan las colas y pueden reintentar.",
    162: "La tabla usa CIDR declarados en IaC y la VNet consultada; confirmar subnet exacta si cambia el estado cloud.",
    166: "Direcciones y conectividad relevantes:",
    167: "VPC AWS tangamandapio: 10.10.0.0/16.",
    168: "Subredes públicas 10.10.0.0/24 y 10.10.1.0/24; app 10.10.10.0/24 y 10.10.11.0/24; DB 10.10.20.0/24 y 10.10.21.0/24.",
    169: "Las tablas de aplicación incluyen la ruta 10.20.1.4/32 hacia el router activo.",
    170: "Internet Gateway asociado al ALB público.",
    171: "Un NAT Gateway; genera cargo horario y por datos procesados.",
    172: "ALB HTTPS/443 entrega a app HTTP/8080. La base permite TCP/5432 desde aplicación.",
    173: "NACL no es el control principal documentado; revisar reglas por defecto antes de cambios.",
    175: "Azure usa VNet, no OCI VCN. CIDR actual consultado: 10.20.0.0/16.",
    176: "VNet `vnet-tangama-private`, 10.20.0.0/16.",
    177: "`snet-private-workloads` 10.20.0.0/24; `snet-private-endpoints` 10.20.1.0/24; `snet-flex-functions` 10.20.2.0/27; `GatewaySubnet` 10.20.255.0/27.",
    178: "La Function resuelve en AWS a 10.20.1.4. Ambas EC2 verificaron TLS y HTTP 200.",
    179: "Las VM usan IP pública para salida/administración según la configuración existente; no equivale a un gateway VPN administrado.",
    180: "Azure opera sin NAT Gateway.",
    181: "NSG gobierna subredes/VM; revisar directamente si se modifican rutas.",
    182: "OCI Security Lists: no aplican porque OCI no se ha desplegado.",
    184: "La topología y la secuencia de reconstrucción están en iac/README.md.",
    185: "La ruta AWS /32 termina en 10.20.1.4. Dos routers de Azure anuncian la red de endpoints.",
    187: "Inventario observado el 19/11/2026:",
    188: "`tangamandapio-asg`: dos EC2, nombres/IDs dinámicos.",
    189: "Portal ERP; ASG con reemplazo y escalado automático.",
    190: "Región AWS: us-east-2 (Ohio).",
    191: "Despliegue repartido en dos zonas de disponibilidad.",
    192: "Una instancia en us-east-2a y otra en us-east-2b.",
    193: "Amazon Linux 2023.",
    194: "Tipo t3.micro: 2 vCPU por instancia.",
    195: "1 GiB de RAM por instancia (tipo t3.micro).",
    196: "Volumen raíz EBS gestionado por la plantilla; tamaño 8 GiB gp3 en el diseño actual, verificar la instancia viva antes de citar inventario.",
    197: "IP privada dinámica; no fijar IPs en clientes.",
    198: "App-A 10.10.10.0/24 y App-B 10.10.11.0/24.",
    199: "Security Group app solo acepta HTTP/8080 desde el SG del ALB; DB permite 5432 desde app.",
    202: "Almacenamiento desplegado y limitaciones:",
    203: "S3 para paquetes, archivos y grabaciones; cifrado, versionado y bloqueo de acceso público observados.",
    204: "EBS para sistema operativo EC2; snapshots/backups RDS aparte.",
    205: "Disco raíz EBS de EC2 administrado por CloudFormation.",
    206: "RDS mantiene un día de respaldos. Systems Manager exporta PostgreSQL a Azure una vez al día.",
    207: "Azure Blob conserva la copia diaria cifrada bajo postgres/ durante 30 días.",
    209: "Ficha de base de datos observada:",
    210: "PostgreSQL 18.3.",
    211: "Amazon RDS PostgreSQL.",
    212: "Instancia administrada Single-AZ; no Multi-AZ.",
    213: "AWS us-east-2, zona us-east-2b.",
    214: "Subredes privadas del DB subnet group, CIDR 10.10.20.0/24 y 10.10.21.0/24.",
    215: "20 GiB; cifrado en reposo; no públicamente accesible; puerto TCP/5432 restringido al grupo de app.",
    216: "Portal ERP AWS y módulos de inventario/ventas/compras.",
    217: "La copia cifrada de Blob recuperó 20 tablas, un usuario, un pedido y un evento.",
    218: "Multi-AZ no activo; no hay conmutación de base demostrada.",
    221: "AWS usa roles de servicio para EC2 y CloudFormation. Acceso humano de CLI debe ser temporal o con credenciales protegidas; no copiar claves al informe.",
    222: "No se enumeran usuarios humanos ni se publican identificadores de claves.",
    223: "La EC2 asume el role de aplicación; permisos del servicio se limitan a secretos, S3 y telemetría requeridos.",
    224: "La policy activa de cada role debe revisarse en IAM; el informe no sustituye su simulación.",
    225: "IAM AWS gestiona principals, roles y policies del despliegue.",
    226: "Azure Entra ID administra identidades de la suscripción; no OCI IAM.",
    227: "No hay usuario OCI para esta arquitectura.",
    228: "No hay grupo OCI desplegado por el proyecto.",
    229: "No hay policies OCI desplegadas; aprobación del cambio de proveedor pendiente por escrito.",
    232: "Reglas principales documentadas:",
    233: "SG ALB: entrada pública TCP/80; SG app: TCP/8080 solo desde ALB; salida controlada según necesidades del portal.",
    234: "Azure NSG limita VM y subredes; ruta privada requiere también NSG y forwarding correctos.",
    235: "Listas de seguridad OCI: no aplican a recursos que no existen.",
    236: "El ALB público tiene WAF asociado; el acceso a RDS no usa Internet.",
    237: "Puertos de datos: 443 entrada al ALB y 80 solo redirige, 8080 ALB→app, 5432 app→RDS; 443 app→Azure por red privada continúa pendiente.",
    238: "Origen permitido: Internet solo al ALB/WAF; app solo desde SG ALB; DB solo desde SG app.",
    239: "Destinos: ALB, app EC2, RDS; Azure PE 10.20.1.4 solo desde redes/identidades autorizadas.",
    240: "El principio es abrir solo el protocolo y origen requeridos; la ruta AWS→Azure no está habilitada aún.",
    243: "Cifrado configurado y brechas:",
    244: "Estado de cifrado:",
    245: "Se verificaron TLS, el dominio público y la sesión de Administración.",
    246: "RDS cifrada; buckets AWS y Blob privados con cifrado del servicio; respaldo PostgreSQL cross-cloud debe aplicar cifrado de aplicación y autenticación.",
    247: "Secretos se gestionan fuera de Git.",
    248: "Política de manejo:",
    249: "No incluir secretos ni claves en repositorio.",
    250: "No incluir valores en capturas o evidencias.",
    251: "No incluir valores secretos en este informe/manual.",
    252: "Secrets Manager y Key Vault guardan secretos; no copiar a archivos de texto.",
    254: "Alta disponibilidad parcialmente demostrada:",
    255: "Aplicación repartida en dos AZ; dos destinos saludables.",
    256: "ASG reemplaza instancias y sostiene mínimo 2; RDS es Single-AZ.",
    257: "ALB reparte solicitudes a targets healthy.",
    258: "Escalado 2→4→5 y scale-in 5→4→3→2 real del 16/11.",
    259: "RDS no tiene standby Multi-AZ; backup de un día no sustituye redundancia de base.",
    260: "La prueba de caída de router AWS no se ejecutó porque esos routers no están desplegados; RTO de cinco segundos no está demostrado.",
    262: "Configuración del ALB:",
    263: "Application Load Balancer `tangamandapio-alb`.",
    264: "Target group `tangamandapio-tg`, targets instance/EC2.",
    265: "Health check HTTP `/health`.",
    266: "Listener TCP/443 HTTPS al grupo de destino; TCP/80 redirige a HTTPS; backend HTTP/8080 dentro del VPC.",
    267: "ACM está ISSUED. El portal público respondió por HTTPS después de actualizar el DNS.",
    268: "Dos targets sanos; portal `/`, `/health` y `/ready` HTTP 200 en prueba documentada.",
    270: "Escalado medido y límites:",
    271: "Vertical: cambiar tipo de instancia después de evaluar memoria, CPU y costo; no se probó.",
    272: "Horizontal: Auto Scaling 2–5 EC2 en dos zonas.",
    273: "Políticas objetivo de CPU y solicitudes por destino; scale-out/scale-in automáticos observados.",
    274: "CPU promedio objetivo 60%; 2.500 solicitudes por target/minuto según parámetro configurado.",
    275: "Escala al cruzar umbral sostenido; el ensayo de 300.000 requests tuvo errores de red no explicados.",
    276: "No se demostró que el sistema soporte 3.000 usuarios simultáneos; no convertir la solicitud pico en resultado.",
    278: "Monitoreo existente:",
    279: "AWS:",
    280: "CloudWatch con dashboard y cinco alarmas propias; todas OK al corte.",
    281: "Azure:",
    282: "Application Insights, Log Analytics y dos alertas 5xx/latencia en español.",
    283: "Métricas y umbrales relevantes:",
    284: "CPU y cambios de capacidad.",
    285: "Memoria requiere agente/métrica adicional; no afirmarla como monitoreada sin evidencia.",
    286: "Disco/EBS y espacio disponible requieren métrica de SO.",
    287: "Red, conexiones, latencia del ALB y métricas de WAF.",
    288: "Disponibilidad por health check de ALB y endpoint Function.",
    289: "5xx, errores de cola, fallas de Function y porcentaje de errores de prueba.",
    291: "IaC desplegada: CloudFormation administra AWS; Terraform tiene raíces separadas para Azure y VPN. No ejecutar raíces duplicadas contra la VPC existente.",
    292: "Archivos relevantes y evidencias:",
    293: "`iac/cloudformation/aws-lab.yaml` y scripts de ciclo de vida.",
    294: "Parámetros del stack y variables locales; no incluir secretos.",
    295: "La pila activa quedó UPDATE_COMPLETE. Se validaron la plantilla AWS y la raíz Azure Flex. Moto probó un subconjunto de red y almacenamiento.",
    296: "El inventario y la evidencia se detallan en iac/ESTADO_REAL_2026-11-19.md.",
    297: "Continuidad del negocio y recuperación:",
    299: "Portal y RDS son críticos; el WMS y los eventos de inventario afectan la exactitud de stock.",
    301: "Conmutación: primer HTTPS 200 entre 4,59 y 9,92 s tras los ajustes. Sigue pendiente demostrar 3 s en la ruta y reemplazo de una EC2 en 5 s.",
    303: "RDS conserva un día de recuperación automatizada como máximo de retención; RPO de la copia externa no está establecido ni medido.",
    305: "Estado de respaldo:",
    306: "PostgreSQL conserva datos de negocio, pedidos, líneas y outbox.",
    307: "RDS ofrece una ventana de un día. Systems Manager exporta a Blob a las 03:00 de Lima.",
    308: "Contenedor privado de copias: tangama-postgres-backups.",
    309: "Blob lifecycle: 30 días para ruta postgres; RDS automation: 1 día.",
    311: "La restauración validó las huellas, descifró mediante Key Vault y recuperó PostgreSQL en aislamiento. Falta medir el RPO.",
    312: "Integración multicloud desplegada por partes:",
    313: "La guía del proyecto menciona AWS y OCI; la descripción permite otros proveedores opcionales. Este equipo desplegó AWS y Azure y necesita constancia del docente para cerrar el criterio nominal.",
    314: "Inventario y prueba de integración:",
    315: "AWS: portal ERP, ASG y RDS.",
    316: "Azure: Function Flex privada, Queue, Blob, Application Insights y dos routers Tailscale.",
    317: "Transporte Tailscale con dos routers por nube, DNS privado y ruta AWS 10.20.1.4/32.",
    318: "Pedido y outbox → Function autenticada → Queue → Blob e Insights, con identificador correlacionado.",
    319: "TLS, clave específica del handler, idempotencia, redes privadas y secretos en almacenes administrados.",
    320: "La prueba privada obtuvo HTTP 201 en AWS en 61 ms y comprobó la finalización del mismo evento en Azure.",
    322: "Corte del 19/11: AWS USD 10,47 de USD 200. Azure USD 8,80 de USD 25. Son datos de gasto, separados del crédito.",
    325: "Acciones de eficiencia:",
    326: "ASG actual usa dos t3.micro como piso; el pico de cinco es temporal y debe retornar a dos.",
    327: "NAT y ALB cobran por hora mientras existen; apagar solo tras ventana de mantenimiento y validación de dependencias.",
    328: "Comparar NAT Gateway administrado con VPC endpoints y patrón de conectividad alterno; nunca eliminar una ruta de producción sin revisar.",
    329: "RDS y Functions administradas reducen trabajo operativo, aunque mantienen cargos de capacidad/almacenamiento.",
    330: "Presupuesto con alertas, etiquetas por proyecto, revisar Cost Explorer/Cost Management diariamente; presupuesto no detiene recursos.",
    332: "Plan de pruebas y resultado al corte:",
    341: "El servicio web está desplegado y el escalado real llegó a cinco nodos; falló el umbral de error de la carga larga. Las dependencias privadas y DR cross-cloud no se han validado desde el portal AWS.",
    343: "Conclusiones basadas en evidencia actual:",
    344: "Arquitectura: CloudFormation mantiene una plataforma web funcional en una región AWS y Azure aporta WMS privado.",
    345: "Seguridad: datos cifrados, TLS del portal verificado y seguimiento limitado por rol y empresa.",
    346: "Disponibilidad: el ASG opera en dos AZ, pero RDS Single-AZ es punto único de fallo.",
    347: "Escalabilidad: el ASG llegó y volvió a cinco/dos automáticamente; 1,47% errores impide aprobar la carga larga.",
    348: "Copia externa diaria cifrada. La restauración aislada tomó 35,108 s. Falta medir el RPO.",
    349: "Costos: créditos y gasto facturado requieren revisión continua; budget USD 200 es aviso, no techo.",
    350: "El pedido AWS–Azure está verificado. Falta la constancia del docente frente al requisito AWS–OCI.",
    352: "Pendientes: meta de conmutación, recuperación regional, RPO, análisis de carga larga, avisos UPeU y WebRTC entre redes restrictivas.",
    354: "Fuentes oficiales y de evidencia:",
    355: "AWS RDS PostgreSQL pricing: https://aws.amazon.com/rds/postgresql/pricing/ · RDS on-demand: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_OnDemandDBInstances.html · VPC/NAT pricing: https://aws.amazon.com/vpc/pricing/ · ALB: https://aws.amazon.com/elasticloadbalancing/pricing/ · WAF: https://aws.amazon.com/waf/pricing/.",
    356: "Azure Functions pricing: https://azure.microsoft.com/en-us/pricing/details/functions/ · Azure VNet: https://learn.microsoft.com/azure/virtual-network/virtual-networks-overview.",
    357: "Caso y evaluación: descripción del proyecto y rúbrica entregadas por el curso; no se agregan fuentes académicas no consultadas.",
    358: "Tailscale subnet routers: https://tailscale.com/docs/features/subnet-routers · Cloudflare Full (strict): https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/.",
    359: "Evidencia técnica incluida en el repositorio:",
    360: "Anexo A: topología comprobada en iac/README.md.",
    361: "Anexo B: direccionamiento y rutas en iac/ESTADO_REAL_2026-11-19.md.",
    362: "Anexo C: tabla de direcciones en esta sección 9.1.",
    363: "Anexo D: reglas principales en sección 13.2 y template CloudFormation.",
    364: "Anexo E: policies/redes se administran en IAM; no se publican credenciales.",
    365: "Anexo F: `iac/cloudformation/` y `iac/environments/`.",
    366: "Anexo G: JSON `evidence/current/aws/` y `evidence/current/azure/`.",
    367: "Anexo H: evidencia de carga, despliegue, health checks y CloudFormation.",
    368: "Anexo I: copia diaria cifrada y restauración aislada documentadas el 19/11.",
    369: "Anexo J: gasto y presupuestos del 19/11. Los precios de referencia son estimaciones.",
    371: "Informe DOCX, manual técnico DOCX, diagramas SVG/Draw.io, IaC CloudFormation/Terraform y evidencias JSON. Integrante, docente y ciclo están completados; faltan capturas autorizadas y aprobación escrita para AWS–Azure.",
    297: "19. Continuidad del negocio y recuperación",
    312: "20. Integración multinube AWS–Azure y cumplimiento de proveedores",
    373: "Estado del cierre técnico",
}


REPORT_TABLES = {
    0: [["PROYECTO INTEGRADOR · TANGAMANDAPIO"]],
    1: [["ALCANCE · Informe técnico basado en el despliegue comprobado. Se distinguen recursos activos, resultados medidos y observaciones que siguen abiertas."]],
    2: [["PROBLEMA TÉCNICO · Se verificaron la conectividad privada, el seguimiento de pedidos y la restauración externa. Continúa pendiente la aprobación del proveedor alternativo."]],
    3: [
        ["Código", "Requisito", "Indicador"],
        ["RF01", "Portal ERP web", "Portal y health checks responden; RBAC en aplicación."],
        ["RF02", "Base centralizada", "RDS PostgreSQL privada, cifrada, Single-AZ."],
        ["RF03", "WMS integrado", "Pedido privado correlacionado en Azure y seguimiento por rol."],
        ["RF04", "Copia recuperable", "RDS retiene un día. Copia diaria cifrada a Blob restaurada en aislamiento."],
        ["RNF05", "Observabilidad", "Avisos de AWS y Azure Monitor observados en Gmail."],
    ],
    4: [
        ["Necesidad", "Modelo", "Servicio", "Proveedor", "Justificación"],
        ["Portal y ERP", "IaaS", "EC2 / ASG", "AWS", "Runtime configurable y escala horizontal."],
        ["Balanceo/perímetro", "PaaS", "ALB + WAF", "AWS", "Distribuye tráfico y filtra solicitudes."],
        ["Transacciones", "PaaS", "RDS PostgreSQL", "AWS", "Motor administrado; aquí Single-AZ."],
        ["WMS privado", "PaaS", "Functions Flex + PE", "Azure", "Procesamiento administrado en red privada."],
        ["Eventos/objetos", "PaaS", "Queue + Blob + Insights", "Azure", "Asíncrono, persistencia y diagnóstico."],
    ],
    6: [
        ["Red/Subred", "CIDR", "Tipo", "Zona", "Propósito"],
        ["AWS VPC", "10.10.0.0/16", "VPC", "us-east-2", "Portal, ALB, app y RDS."],
        ["AWS Public A/B", "10.10.0.0/24; 10.10.1.0/24", "Pública", "2 AZ", "ALB y salida NAT."],
        ["AWS App A/B", "10.10.10.0/24; 10.10.11.0/24", "Privada", "2 AZ", "ASG de aplicación."],
        ["AWS DB A/B", "10.10.20.0/24; 10.10.21.0/24", "Privada", "2 AZ", "Subnets del DB subnet group."],
        ["Azure VNet", "10.20.0.0/16", "VNet", "West US", "Function, PE y routers."],
        ["Azure PE/workloads", "10.20.1.0/24; 10.20.0.0/24", "Privada", "West US", "Private Endpoint y VM Tailscale."],
        ["Azure Flex/Gateway", "10.20.2.0/27; 10.20.255.0/27", "Delegada/GatewaySubnet", "West US", "Flex environment y subnet reservada."],
    ],
    7: [
        ["Nombre", "Función", "Proveedor", "SO", "vCPU / RAM", "IP / Subred"],
        ["EC2 ASG A y B", "Portal ERP", "AWS us-east-2a/b", "Amazon Linux 2023", "2 / 1 GiB c/u", "App-A y App-B"],
        ["Routers AWS piloto y respaldo", "Ruta WMS privada", "AWS us-east-2", "Amazon Linux 2023", "2 / 1 GiB c/u", "Subredes app"],
        ["vm-tangama-ts-pilot", "Router Tailscale Azure", "Azure West US", "Linux", "Standard_B2pts_v2", "10.20.0.4"],
        ["vm-tangama-ts-backup", "Router Tailscale Azure", "Azure West US", "Linux", "Standard_B2pts_v2", "10.20.0.5"],
    ],
    11: [
        ["Origen", "Destino", "Puerto", "Protocolo", "Acción", "Justificación"],
        ["Internet", "WAF / ALB", "443; 80 redirige", "HTTPS; HTTP redirect", "Permitir", "HTTPS público comprobado y ACM ISSUED."],
        ["SG ALB", "SG app", "8080", "HTTP", "Permitir", "Tráfico solo desde balanceador."],
        ["SG app", "SG RDS", "5432", "PostgreSQL/TLS", "Permitir", "Acceso de aplicación a base privada."],
        ["AWS app", "Azure PE 10.20.1.4", "443", "HTTPS", "Activo", "Ruta /32 por Tailscale y TLS verificado."],
    ],
    17: [
        ["Servicio", "Cantidad / uso", "Costo de referencia"],
        ["Compute AWS", "2 t3.micro × 504 h", "≈ USD 10,48 (referencia On-Demand; antes de créditos)."],
        ["Storage", "S3, EBS, Blob", "Por medir; capacidad/transferencia no consolidada."],
        ["Database", "RDS db.t3.micro × 504 h + 20 GiB", "Pendiente de calculadora regional; Multi-AZ no activo."],
        ["Networking", "1 NAT × 504 h + ALB base × 504 h", "≈ USD 34,02; excluye NAT bytes/LCU y tráfico."],
        ["Monitoring/WAF/Azure", "5 alarmas + WAF + 2 VMs Azure", "Coste total pendiente; consultar calculadoras y factura."],
    ],
    24: [
        ["ID", "Prueba", "Resultado esperado", "Resultado obtenido", "Estado"],
        ["T01", "Portal health", "200 en `/health`", "200 reportado en corte vivo", "Aprobada"],
        ["T02", "ASG 2→5→2", "Capacidad automática y destinos sanos", "Llegó a 5 y bajó a 2; 1,47% errores en carga larga", "Parcial"],
        ["T03", "Postcheck 3k requests", "0 errores, p95 <5 s", "3.000/3.000 HTTP 200; p95 263,86 ms", "Aprobada"],
        ["T04", "Pedido privado AWS→Azure", "Function, Queue, Blob, Insights", "Pedido y resultado correlacionados. Seguimiento por rol.", "Aprobada"],
        ["T05", "Restauración desde Blob", "Huellas íntegras y base aislada", "20 tablas recuperadas en 35,108 s.", "Aprobada"],
    ],
    5: [["MODELOS CLOUD · EC2 es IaaS; RDS, Functions Flex, Queue, Blob y Application Insights son PaaS. La consola de administración es una herramienta SaaS del proveedor, no una aplicación empresarial contratada para el caso."]],
    8: [["CÓMPUTO · Dos instancias t3.micro en zonas distintas sostienen el portal. El ASG demostró scale-out hasta cinco y scale-in automático; no se ha probado reemplazo tras caída ni 3.000 usuarios concurrentes."]],
    9: [["BASE DE DATOS · Se eligió RDS PostgreSQL para delegar operación del motor. El estado vivo es Single-AZ, cifrado, privado, 20 GiB y retención de un día; no ofrece la misma disponibilidad que Multi-AZ."]],
    10: [["SEGURIDAD · Los roles y reglas de red limitan el acceso entre capas. No se incluyen claves, contraseñas, tokens ni valores de secretos en este informe. Rotar cualquier credencial que haya aparecido en capturas o chats."]],
    12: [["EVIDENCIA DE DISPONIBILIDAD · El 16/11 el ASG cambió automáticamente 2→4→5 y luego 5→4→3→2 bajo carga. Esto prueba escalado, no recuperación ante la caída de una instancia; el RTO de cinco segundos sigue sin comprobar."]],
    13: [["EVIDENCIA FUNCIONAL · ALB activo, dos destinos saludables, RDS disponible y CloudFormation en UPDATE_COMPLETE. El pedido sintético se verificó desde el ERP hasta Azure."]],
    14: [["OBSERVABILIDAD · Gmail recibió avisos AWS y un aviso de Azure Monitor. UPeU figura pendiente de confirmación."]],
    15: [["REPRODUCIBILIDAD · CloudFormation y Terraform pasaron validación. Moto comprobó red y S3. El ciclo completo en cuentas vacías sigue pendiente."]],
    16: [["MULTINUBE · AWS y Azure procesaron un pedido por ruta privada. La rúbrica nombra OCI y la presentación con Azure requiere autorización escrita."]],
    18: [["PRUEBA DE ACCESO · El ALB y los destinos aparecen activos/saludables en el último corte. No se documentó una prueba nueva de acceso externo a RDS; el diseño mantiene la base en subred privada y sin endpoint público."]],
    19: [["PRUEBA DE FLUJO · Pendiente → en cola → procesado. AWS y Azure registraron el mismo identificador de evento."]],
    20: [["PRUEBA DE SEGURIDAD · RDS está configurada como privada y cifrada. La matriz registra la postura configurada; no se ejecutó un intento externo nuevo de conexión a PostgreSQL en este corte."]],
    21: [["PRUEBA DE ALTA DISPONIBILIDAD · La ruta cambió al respaldo y regresó al principal. El primer HTTPS 200 llegó entre 4,59 y 9,92 s tras el ajuste."]],
    22: [["PRUEBA DE RESTAURACIÓN · Una copia diaria cifrada de Blob recuperó 20 tablas en 35,108 s en PostgreSQL aislado. Falta medir el RPO."]],
    23: [["PRUEBA DE ALARMA · Gmail recibió SNS, eventos del ASG, cambios de router y un aviso de Azure Monitor. UPeU sigue pendiente."]],
    25: [["EVIDENCIA · Para cada afirmación se cita la fecha, el archivo y el resultado observado. Los elementos sin registro reciente se marcan como pendientes; no se sustituyen con capturas antiguas ni resultados de laboratorio."]],
    26: [["REFERENCIAS · Se usa un formato autor-fecha simplificado con documentación oficial del proveedor y rutas a evidencia del repositorio. Completar las referencias del curso y los datos bibliográficos exigidos por el docente antes de entregar."]],
    27: [["Proyecto_Final_Tangamandapio/\n├── deliverables/\n│   ├── Proyecto_Final_Tangamandapio_2026-11-19.docx\n│   └── Manual_Tecnico_Tangamandapio_2026-11-19.docx\n├── iac/\n│   ├── README.md · topología y reconstrucción\n│   ├── cloudformation/ · aws-lab.yaml\n│   ├── environments/ · Terraform y OneDeploy\n│   └── scripts/ · operación y recuperación\n├── evidence/current/ · resultados fechados AWS/Azure\n└── core/ · registro maestro y matriz de rúbrica"]],
    28: [["PENDIENTES PARA LA DEFENSA\n1. Adjuntar la constancia docente para AWS–Azure y las fotografías autorizadas.\n2. Medir RPO, verificar recuperación regional y repetir la carga sostenida con registros.\n3. Confirmar recepción en UPeU y verificar WebRTC entre redes restrictivas.\n4. Renovar a tiempo la autorización de respaldo y revisar el consumo antes de la defensa."]],
}


def create_report() -> None:
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Official template not found: {TEMPLATE}")
    template_hash = sha256(TEMPLATE.read_bytes()).hexdigest()
    if template_hash != EXPECTED_TEMPLATE_SHA256:
        raise ValueError(f"Official template changed: {template_hash}")
    document = Document(TEMPLATE)
    if len(document.paragraphs) != 374 or len(document.tables) != 29:
        raise ValueError(f"Unexpected template structure: {len(document.paragraphs)} paragraphs, {len(document.tables)} tables")
    for index, value in PARAGRAPHS.items():
        set_paragraph(document.paragraphs[index], value)
    for index, rows in REPORT_TABLES.items():
        set_table(document.tables[index], rows)
    # The template reserves fixed-height panels for architecture/code samples.
    # The actual tree and closeout list are shorter, so let these two rows size
    # to their content instead of leaving a mostly empty continuation page.
    for table_index in (27, 28):
        for row in document.tables[table_index].rows:
            tr_pr = row._tr.get_or_add_trPr()
            for height in list(tr_pr.findall(qn("w:trHeight"))):
                tr_pr.remove(height)
    for paragraph in document.paragraphs:
        if paragraph.text == "22.6 Pruebas de monitoreo":
            paragraph.paragraph_format.keep_with_next = True
    insert_current_verification(document, "2. Resumen ejecutivo")
    document.save(REPORT)


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def configure_manual(document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.72)
    section.left_margin = Inches(0.82)
    section.right_margin = Inches(0.82)
    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(32, 47, 62)
    normal.paragraph_format.space_after = Pt(3)
    for style_name, size, color in (("Heading 1", 17, "153D5B"), ("Heading 2", 13, "126B89"), ("Heading 3", 11, "34495E")):
        style = document.styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(4)
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.add_run("TANGAMANDAPIO · MANUAL TÉCNICO · 19/11/2026").font.size = Pt(8)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Estado de trabajo · no contiene secretos · página ").font.size = Pt(8)
    add_field(footer, "PAGE")


def add_table(document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1" if "Light Shading Accent 1" in [s.name for s in document.styles] else "Table Grid"
    header_properties = table.rows[0]._tr.get_or_add_trPr()
    header_marker = OxmlElement("w:tblHeader")
    header_marker.set(qn("w:val"), "true")
    header_properties.append(header_marker)
    header_no_split = OxmlElement("w:cantSplit")
    header_properties.append(header_no_split)
    for i, value in enumerate(headers):
        set_cell(table.rows[0].cells[i], value)
        paragraph = table.rows[0].cells[i].paragraphs[0]
        paragraph.paragraph_format.keep_with_next = True
        for run in paragraph.runs:
            run.bold = True
    for row in rows:
        table_row = table.add_row()
        row_properties = table_row._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))
        cells = table_row.cells
        for i, value in enumerate(row):
            set_cell(cells[i], value)
    document.add_paragraph()


def add_bullets(document, items: list[str]) -> None:
    for item in items:
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.add_run(item)


def add_numbered(document, items: list[str]) -> None:
    for index, item in enumerate(items, start=1):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.28)
        paragraph.paragraph_format.first_line_indent = Inches(-0.28)
        paragraph.add_run(f"{index}. ").bold = True
        paragraph.add_run(item)


def create_manual() -> None:
    document = Document()
    configure_manual(document)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(95)
    run = p.add_run("MANUAL TÉCNICO\nTANGAMANDAPIO")
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(30)
    run.font.color.rgb = RGBColor(21, 61, 91)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("AWS us-east-2 · Azure West US · validación del 19 de noviembre de 2026").font.size = Pt(14)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(30)
    p.add_run("Operación, seguridad, pruebas y cierre de observaciones\nVersión académica basada en evidencia consultada\n\nJose Dario Zuñiga Medina · Docente: Fernando Manuel Asin Gomez · Ciclo 8").font.size = Pt(11)
    document.add_page_break()

    document.add_heading("0. Cómo leer este manual", level=1)
    document.add_paragraph("El inventario y las pruebas de este manual tienen corte al 19/11/2026. Cada prueba fechada indica qué se verificó, con qué alcance y qué queda por medir.")
    document.add_heading("Prioridad ejecutiva", level=2)
    add_numbered(document, [
        "Repetir un pedido sintético por el dominio HTTPS y seguir su identificador de AWS a Azure.",
        "Volver a medir el primer HTTPS 200 en ambas EC2 tras conmutar los routers y al regresar al principal.",
        "Renovar el permiso de Blob antes de vencer y medir el RPO mediante transacciones marcadas.",
        "Confirmar la segunda suscripción SNS de UPeU. Gmail ya recibió avisos de AWS y uno de Azure Monitor.",
        "Investigar el 1,47% de errores de la carga larga; repetir prueba antes de declarar capacidad aprobada.",
        "Adjuntar la aprobación escrita del docente para AWS–Azure como reemplazo del requisito AWS–OCI; OCI no existe en el despliegue.",
    ])

    document.add_heading("1. Inventario vivo", level=1)
    add_table(document, ["Componente", "Estado confirmado", "Brecha"], [
        ["AWS / CloudFormation", "Cuenta 481056890449, us-east-2; stack UPDATE_COMPLETE; parámetros RDS false/1.", "EC2 fuera de us-east-2 bloqueada por SCP p-4lylrj0n; el contenido de la política no es visible desde esta cuenta."],
        ["Portal / ALB / WAF", "HTTPS público, sesión y WAF comprobados.", "Guardar capturas para la defensa."],
        ["ASG", "Min 2, deseado 2, máximo 5; dos EC2 sanas en 2 AZ.", "La carga larga tuvo 1,47% de errores."],
        ["RDS", "PostgreSQL 18.3 privado y cifrado, Single-AZ, 20 GiB y retención de un día.", "Medir RPO y evaluar Multi-AZ."],
        ["Azure", "Function Flex privada, endpoint 10.20.1.4, Queue, Blob, Insights y Key Vault.", "Verificar recuperación regional."],
        ["Ruta entre nubes", "Dos routers en cada nube. Ruta /32 verificada desde ambas EC2.", "Lograr recuperación HTTPS de 3 s en ambas EC2."],
        ["Alertas", "Gmail recibió AWS SNS, eventos ASG, conmutación y un aviso Azure Monitor.", "Confirmar recepción UPeU."],
        ["Costo", "AWS USD 10,47 de USD 200. Azure USD 8,80 de USD 25 al corte.", "Los presupuestos notifican. Reconsultar antes de repetir cargas."],
    ])

    document.add_heading("2. Arquitectura y flujo desplegados", level=1)
    document.add_paragraph("Navegador → Cloudflare → WAF/ALB HTTPS en AWS → ASG en dos zonas → PostgreSQL privado. El ERP guarda el pedido y el outbox. El evento sale por la ruta Tailscale hacia el Private Endpoint 10.20.1.4. Function valida y publica en Queue, el consumidor guarda el resultado en Blob y Application Insights registra el evento.")
    document.add_page_break()
    add_table(document, ["Red", "Rango", "Subredes", "Uso"], [
        ["AWS VPC", "10.10.0.0/16", "public 10.10.0.0/24, 10.10.1.0/24; app 10.10.10.0/24, 10.10.11.0/24; DB 10.10.20.0/24, 10.10.21.0/24", "ALB, ASG, RDS."],
        ["Azure VNet", "10.20.0.0/16", "workloads 10.20.0.0/24; PE 10.20.1.0/24; Flex 10.20.2.0/27; GatewaySubnet 10.20.255.0/27", "Routers, Function Flex, Private Endpoint."],
    ])
    document.add_paragraph("El ALB recibe TCP/443 y redirige TCP/80 a HTTPS. El ALB entrega a EC2 por 8080. RDS recibe 5432 solo desde aplicación. Ambas EC2 llegaron a la Function por TCP/443 y la ruta /32. AWS tiene un NAT Gateway compartido. Azure opera sin NAT Gateway.")
    document.add_paragraph("La topología comprobada y el orden de reconstrucción están en iac/README.md.")

    document.add_heading("3. Portal, TLS y DNS", level=1)
    document.add_paragraph("Al 19/11, el portal público respondió por HTTPS y permitió iniciar y cerrar sesión. El listener del ALB usó el certificado ACM. Cloudflare aplicó Full (strict) al hostname del portal.")
    document.add_paragraph("CNAME de validación ACM ya aplicado en modo DNS-only (referencia; no volver a crearlo):")
    add_table(document, ["Tipo", "Nombre", "Destino"], [["CNAME", "_7408575772140ac4b6bcd8e3ab10a8ca.tangamandapio", "_694a9f814a3985f9576fb181841dc9d3.wzccmgtwzk.acm-validations.aws"]])
    add_numbered(document, [
        "Confirmar en ACM, región us-east-2, que el certificado siga `ISSUED`.",
        "Comprobar que el ALB mantenga el listener 443 con el certificado y que el listener 80 solo redirija a HTTPS.",
        "Abrir `https://tangamandapio.kendellnm.me/health` y validar código 200 y cadena TLS desde fuera de AWS.",
        "En Cloudflare, verificar que la Configuration Rule aplique `Full (strict)` solo con Hostname equals `tangamandapio.kendellnm.me`; no cambiar el modo global ni el DNS del portal.",
    ])
    document.add_paragraph("La comprobación posterior al cambio está en evidence/current/aws/AWS-PUBLIC-PORTAL-ADMIN-2026-11-18.json.")

    document.add_heading("4. Ruta privada AWS–Azure y conmutación", level=1)
    document.add_paragraph("Azure usa vm-tangama-ts-pilot (10.20.0.4) y vm-tangama-ts-backup (10.20.0.5). Dos routers AWS sostienen la salida hacia 10.20.1.4/32. Ambas EC2 alcanzaron la Function en esa dirección y validaron TLS. Repite los pasos de alta si reconstruyes los routers.")
    add_numbered(document, [
        "En Tailscale Admin → Settings → Keys, crear dos auth keys de un solo uso, no efímeras, con tag `tag:tangama-aws-router`; nunca pegarlas en el chat, terminal con historial o Git.",
        "Guardar cada valor directamente en AWS Secrets Manager, región us-east-2: `tangamandapio/tailscale/aws-pilot` y `tangamandapio/tailscale/aws-backup`. No incluir valores en informes ni enviarlos por chat.",
        "Empaquetar y desplegar `iac/cloudformation/aws-azure-tailscale-ha.yaml` con `package_tailscale_ha.sh` y `deploy_tailscale_ha.sh`; la ruta se mantiene apagada hasta que ambos routers pasen health check.",
        "Enrolar los routers con `iac/scripts/enrol_tailscale_router.py` usando archivo root-only temporal en `/run`; verificar tag esperado, approval de ruta y DNS privado.",
        "Habilitar forwarding y NAT acotados desde 10.10.10.0/23 hacia 10.20.1.4 TCP/443; añadir ruta /32 a la tabla app solo después de confirmar router/ENI correctos. El helper `ensure_private_wms_route.py` se niega a reemplazar un destino desconocido.",
        "Desde EC2 app, resolver `tangama-flex-261104.azurewebsites.net` a 10.20.1.4 y hacer HTTPS `/api/health`; verificar certificado y código 200. No usar URL pública como prueba privada.",
        "Registra un pedido sintético desde el portal y comprueba el mismo event_id en Function, Queue, Blob e Insights. La clave autorizada se obtiene de Secrets Manager.",
        "Solo tras demostrar ambas rutas, probar failover en ventana: captura estado/ruta; detener un router AWS de forma reversible; observar recuperación; medir RTO con timestamps; restaurar router principal y confirmar ruta final. No declarar 5 s antes de medir.",
    ])
    document.add_paragraph("El controlador `iac/scripts/tailscale_ha_controller.py` opera con los dos routers AWS enrolados y la ruta 10.20.1.4/32 habilitada. Antes de reemplazar la ENI comprueba en paralelo la ruta actual y un HTTPS fresco del destino. Para medir la recuperación, captura el primer HTTP 200 completo de cada EC2 y confirma el retorno al principal. El objetivo de tres segundos queda pendiente.")

    document.add_heading("4.1 Seguimiento de pedidos por rol", level=2)
    document.add_paragraph("Abre Seguimiento de pedidos y elige un pedido. El ERP guarda líneas y outbox en una transacción. El envío asíncrono reintenta entregas elegibles cada 60 segundos. Azure deduplica por identificador de evento. Si el pedido carece de líneas aparece Requiere líneas. Las colas muestran conteos aproximados y distinguen un dato desconocido de una cola vacía.")
    add_table(document, ["Rol", "Actividad en el flujo"], [
        ["Cliente B2B", "Registra SKU y cantidad y consulta el avance de los pedidos de su empresa."],
        ["Ventas", "Registra pedidos y revisa sus resultados operativos permitidos."],
        ["Almacén", "Consulta las líneas y el resultado del WMS."],
        ["Operaciones TI", "Lee el outbox y las colas. Puede reintentar con auditoría."],
        ["Auditoría", "Consulta el historial técnico y las marcas de tiempo."],
        ["Administración", "Registra, supervisa y reintenta pedidos. Gestiona usuarios y permisos."],
    ])
    document.add_paragraph("Evidencia de la prueba SEGUIMIENTO-DEMO-20261119-151352 en AWS-PORTAL-ORDER-TRACKING-2026-11-19.json y AZURE-WMS-ORDER-TRACKING-2026-11-19.json. El resultado corresponde al inventario sintético.")

    document.add_heading("5. Backup y restauración PostgreSQL→Azure Blob", level=1)
    document.add_paragraph("RDS conserva un día de recuperación automática. Systems Manager ejecuta la copia día a día a las 03:00 de Lima. La copia vigente se guarda en Blob y se verificó al restaurarla en PostgreSQL aislado. El cifrado usa AES-256-GCM con una clave envuelta mediante RSA-OAEP-SHA256. El descifrado requiere permiso sobre la clave de Key Vault.")
    add_bullets(document, [
        "Precondición de red: job debe alcanzar RDS privado por TLS verify-full y Blob por HTTPS; usar egress existente con costo medido.",
        "Autenticación de escritura: identidad de workload de mínimo privilegio para Blob y permiso de uso de clave pública de Key Vault. No usar SAS perpetuo ni account key en texto plano.",
        "Backup: `pg_dump --format=custom --no-owner --no-privileges`; validar versión y cluster identity; generar manifiesto y hashes; cifrar antes de subir; subir a contenedor privado con versioning/retención.",
        "Programación: la asociación de Systems Manager reutiliza las EC2 de aplicación y registra el manifiesto diario en S3. La escritura a Blob usa una autorización de creación que se rota por separado.",
        "Restore: descargar una copia concreta, validar hash autenticado, descifrar vía Key Vault, restaurar a RDS aislada distinta a producción, verificar tablas y consultas; registrar tiempo de recuperación y punto de datos.",
        "Retención: Blob lifecycle de 30 días existe para la ruta postgres; asegurar que no elimine la última copia válida y almacenar hashes/manifest independiente.",
    ])
    document.add_paragraph("En Administración → Respaldos, descarga la copia cifrada de Azure o pulsa Ejecutar respaldo para exportar pedidos, líneas y outbox a S3. La copia de S3 se cifra, conserva durante 30 días y no despacha eventos. Para una restauración completa, usa la copia de Blob y un PostgreSQL aislado. Mide RPO con transacciones marcadas; el RTO de la restauración ya se observó en 35,108 s.")

    document.add_heading("6. Auto Scaling, alarmas y prueba", level=1)
    document.add_paragraph("Configuración comprobada: ASG min 2 / desired 2 / max 5, CPU objetivo 60%, solicitudes por destino 2.500/min. El 16/11, 300.000 solicitudes con concurrencia 50 duraron 1.645,443 s; p95 315,47 ms; 1,47% errores (8 respuestas 502 y 4.399 errores de red). Auto Scaling llegó 2→4→5 y bajó automáticamente 5→4→3→2. Postcheck 3.000 solicitudes, concurrencia 30: cero errores, p95 263,86 ms. No es prueba de 3.000 usuarios concurrentes.")
    add_bullets(document, [
        "Administración → Prueba de escalado permite elegir 3, 4 o 5 instancias. AWS programa primero el regreso a la capacidad anterior. Durante la ventana de unos diez minutos comprueba los destinos sanos, registra la latencia y espera el retorno al nivel base.",
        "Antes de repetir: limitar tasa y duración, revisar acceso logs del ALB/WAF y métricas TargetResponseTime/HTTPCode_Target_5XX, CPU, RDS connections/CPU, cliente de carga y errores URLError detallados.",
        "Ejecutar escalones conservadores, no saltar directamente a 300.000; conservar hora UTC, p50/p95/p99, HTTP 2xx/4xx/5xx, errores cliente, DesiredCapacity y scaling activities.",
        "Dejar que scaling policies reduzcan capacidad; no cambiar DesiredCapacity durante la fase de medición.",
        "Las cinco alarmas custom actuales son high CPU, in-service capacity, RDS high CPU, target 5xx y unhealthy targets; todas estaban OK. Eventos ASG publican en SNS.",
        "Gmail recibió la prueba SNS, eventos ASG y mensajes de cambio y retorno del router. UPeU sigue pendiente.",
        "Se observó un aviso de Azure Monitor. Las reglas pueden repetirse de forma controlada para la demostración.",
    ])

    document.add_heading("7. Terraform, CloudFormation y emulación", level=1)
    document.add_paragraph("CloudFormation es la fuente actual de verdad para AWS. La pila viva quedó IN_SYNC. Terraform se organiza en varias raíces independientes; `azure-rebuild` pasó `init -backend=false` y `validate` y las raíces se formatearon, pero no se aplicaron. Importar recursos Azure existentes a la raíz correcta antes de plan/apply. No ejecutar `iac/environments/demo` sobre esta cuenta: puede duplicar la VPC/CIDR.")
    document.add_paragraph("aws-lab.yaml y rebuild.sh usan RDS Single-AZ y un día de retención por defecto. Define ADMIN_AZURE_BACKUP_ACCOUNT y, al usar un nombre distinto, ADMIN_AZURE_BACKUP_CONTAINER para recuperar el catálogo de copias. Pasa el permiso de lectura por SSM. La raíz azure-flex-private publica las URL privadas de pedidos y colas. ARM OneDeploy instala el ZIP con acceso público deshabilitado y una URL de lectura temporal fuera del estado Terraform.")
    document.add_paragraph("En Moto 5.2.5, Terraform creó y retiró 17 recursos de red con seis subredes y sus asociaciones. CloudFormation levantó un subconjunto de la plantilla real con 21 recursos identificados; algunas propiedades y el orden de eliminación dependen de la implementación del emulador. También se verificó la programación de regreso para las opciones 3, 4 y 5. Las pruebas no simulan precios, EC2 real, WAF, RDS Multi-AZ ni conectividad privada entre nubes.")

    document.add_heading("8. Costos y control del crédito", level=1)
    document.add_paragraph("El 19/11 el presupuesto AWS registró USD 10,47 de USD 200. Azure Cost Management registró USD 8,80 en noviembre frente al presupuesto mensual de USD 25. El consumo facturado y el saldo del crédito se informan por separado. Los presupuestos notifican y la escala temporal vuelve a su capacidad anterior por una acción programada del ASG.")
    add_table(document, ["Recurso", "Supuesto 21 días", "Referencia parcial"], [
        ["EC2", "2 × t3.micro × 504 h", "USD 10,48 a USD 0,0104/h de referencia; validar región/Free Tier."],
        ["NAT Gateway", "1 × 504 h", "USD 22,68 a USD 0,045/h en ejemplo oficial Ohio; más GB procesados y transferencia."],
        ["Application Load Balancer", "1 × 504 h", "USD 11,34 por hora base de ejemplo; más LCU."],
        ["Subtotal parcial AWS", "No incluye otros servicios", "≈ USD 44,50 antes de créditos, RDS, WAF, EBS, IPv4, logs, tráfico ni Azure."],
        ["Azure routers", "2 × Standard_B2pts_v2 × 504 h", "Precio pendiente de Azure Pricing Calculator/Cost Management."],
    ])
    document.add_paragraph("La suma no es una cotización ni una factura. AWS publica cobro por hora y datos de NAT, precio por hora/LCU para ALB y por ACL/reglas/solicitudes para WAF; RDS debe calcularse por región, motor, clase, almacenamiento y deployment. Revisar a diario Cost Explorer, Azure Cost Management, créditos y Budget; detener temporalmente pruebas no necesarias, no borrar componentes sin revisar dependencias.")

    document.add_heading("9. Matriz de pruebas", level=1)
    add_table(document, ["Prueba", "Último resultado", "Criterio de aceptación/cierre"], [
        ["Portal", "HTTPS 200 y sesión de Administración comprobados.", "Abrir dominio público y verificar los dos destinos sanos."],
        ["Scale-out/in", "2→4→5→4→3→2; 1,47% error larga.", "Investigar errores; repetir bajo 1% y guardar evidencia."],
        ["Postcheck", "3.000 req, 0 errores, p95 263,86 ms.", "No equivale a 3.000 usuarios."],
        ["Ruta privada AWS→Azure", "Pedido correlacionado en Function, Queue, Blob e Insights.", "Mostrar HTTPS privado y seguir el identificador de evento."],
        ["Failover routers", "Ambos ensayos retornaron al principal. El primer HTTP 200 fue mayor a 3 s.", "Medir HTTP completo desde las dos EC2."],
        ["Backup/restore", "Copia diaria de Blob restaurada en 35,108 s. Copia manual en S3 con descarga comprobada.", "Medir RPO con transacciones marcadas."],
        ["Alarmas", "Gmail mostró eventos de AWS y un aviso de Azure.", "Confirmar UPeU y guardar evidencia."],
        ["TLS", "El dominio y la sesión funcionaron por HTTPS.", "Adjuntar captura para la defensa."],
    ])

    document.add_heading("10. Anexos y fuentes", level=1)
    add_bullets(document, [
        "Estado e inventario vigente en iac/ESTADO_REAL_2026-11-19.md.",
        "Matriz por criterio: `core/04_matriz_rubrica.md`.",
        "Pruebas ASG: `evidence/current/aws/AWS-ASG-SCALE-2-5-2026-11-16-http.json`, `AWS-ASG-SCALE-POSTCHECK-2026-11-16-http.json` y evidencia cloud consolidada.",
        "Programación diaria en iac/cloudformation/aws-azure-postgres-backup.yaml. Restauración aislada descrita en iac/README.md.",
        "Documentación oficial de precios, TLS y VPN en la sección 26 del entregable final.",
    ])
    document.core_properties.title = "Manual técnico de Tangamandapio"
    document.core_properties.subject = "Runbook de arquitectura, observabilidad, backup y cierre"
    document.core_properties.author = "Jose Dario Zuñiga Medina"
    set_update_fields(document)
    insert_current_verification(document, "0. Cómo leer este manual")
    document.save(MANUAL)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    create_report()
    create_manual()
    print(f"Created {REPORT.name} and {MANUAL.name}")
