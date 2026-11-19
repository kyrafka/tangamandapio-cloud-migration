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
        ("Pedido privado. ", "Las dos EC2 de aplicación llegaron a la Function en 10.20.1.4 con TLS verificado. Un pedido ficticio se procesó en Function y Queue. Azure conservó y cifró ambos objetos en Blob. Application Insights permitió seguir el mismo identificador de evento."),
        ("Conmutación. ", "El respaldo AWS tomó la ruta en 4,598 s. Los dos clientes recibieron HTTP 200 en 4,68 y 5,57 s. El principal recuperó la ruta automáticamente. Gmail recibió ambos avisos y el aviso de prueba de Azure Monitor."),
        ("Recuperación. ", "Systems Manager programa un respaldo cifrado diario a las 03:00 de Lima. La restauración de la copia actual en PostgreSQL aislado recuperó 20 tablas, un pedido y un evento en 35,108 s. La autorización de Blob debe renovarse al vencimiento."),
        ("Telefonía. ", "Dos clientes locales intercambiaron audio WebRTC sintético en ambos sentidos. Falta validar el audio entre redes restrictivas. TURN aún no está configurado."),
        ("Costos y defensa. ", "AWS reportó USD 150,59 de crédito restante. Azure registró USD 8,50 en el mes frente al presupuesto de USD 25. RDS permanece en Single-AZ. Queda medir RPO, demostrar recuperación regional y presentar las fotos y la constancia docente para AWS–Azure."),
    ):
        paragraph = document.add_paragraph()
        paragraph.add_run(lead).bold = True
        paragraph.add_run(body)
        following._p.addprevious(paragraph._p)
    sources = document.add_paragraph("Las secciones siguientes conservan el diseño y el inventario de referencia del 16/11. El registro iac/ESTADO_REAL_2026-11-19.md enlaza la evidencia vigente y la matriz de la rúbrica.")
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
    10: "FECHA: 19 de noviembre de 2026 · versión técnica de trabajo",
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
    27: "Beneficio: se demuestra una base desplegada y escalable; la ruta privada AWS–Azure, el respaldo PostgreSQL externo y la recuperación regional siguen siendo brechas reales.",
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
    55: "Flujos de ventas, compras, devoluciones e inventario sintético.",
    56: "ERP integrado en el portal; persistencia PostgreSQL administrada.",
    57: "Maestros sintéticos de clientes, proveedores y productos.",
    58: "Amazon RDS for PostgreSQL en red privada.",
    59: "Panel administrativo y permisos de aplicación con control servidor.",
    60: "S3 para artefactos y archivos del portal; Azure Blob para almacenamiento y destino planificado de respaldo.",
    61: "RDS conserva un día de respaldo automatizado; no existe aún copia PostgreSQL reciente automática hacia Blob.",
    62: "WMS implementado en Azure Functions Flex con Queue, Blob y Application Insights.",
    65: "La situación anterior es un supuesto académico de infraestructura centralizada y con poca resiliencia. La implementación cloud no migra datos reales de una empresa; usa maestros y transacciones sintéticas.",
    66: "Estado del despliegue al 16/11/2026:",
    67: "AWS: dos instancias EC2 actuales en un ASG, con min 2 y max 5.",
    68: "Amazon Linux 2023 en EC2; las dos VM-router de Azure usan Linux.",
    69: "Portal ERP B2B en AWS; WMS HTTP API en Azure Functions Flex.",
    70: "PostgreSQL 18.3 administrado por RDS; db.t3.micro, 20 GiB, privada, cifrada, Single-AZ.",
    71: "S3 cifrado/versionado en AWS; Azure Storage privado con Blob y colas.",
    72: "VPC AWS 10.10.0.0/16, VNet Azure 10.20.0.0/16. No hay ruta AWS a 10.20.1.4/32; el inventario us-east-2 muestra las dos EC2 de app, no routers AWS.",
    73: "El portal público llega al ALB AWS por HTTPS/443; HTTP/80 redirige a HTTPS. La ruta pública a la Function está deshabilitada.",
    74: "WAF asociado al ALB, security groups, roles de aplicación y almacenamiento sin acceso público. ACM está ISSUED; Cloudflare reporta Full (strict) por hostname; falta revalidar el flujo HTTPS público de extremo a extremo.",
    75: "RDS: retención automática de un día. Azure Blob tiene una copia manual vieja del 05/11, no un backup RDS actual.",
    76: "CloudWatch tiene cinco alarmas propias; Azure Application Insights/Log Analytics y dos alertas están habilitadas. SNS Gmail está confirmado; UPeU aparece dos veces PendingConfirmation y ninguna alerta de prueba tiene recepción documentada.",
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
    99: "RF03. Preparar una integración segura con el WMS privado de Azure; la ruta AWS actual está pendiente.",
    100: "RF04. Conservar respaldo recuperable y probar restauración aislada; el backup cross-cloud aún no está automatizado.",
    101: "Requisitos no funcionales medibles:",
    102: "Objetivos y condición de evidencia:",
    103: "Disponibilidad: dos AZ para aplicación; RDS Single-AZ es punto pendiente.",
    104: "Rendimiento: latencia p95 y tasa de errores registradas por prueba.",
    105: "Escalabilidad: ASG entre 2 y 5 nodos; 3.000 usuarios simultáneos no medidos.",
    106: "Seguridad: WAF, cifrado y acceso mínimo. ACM está ISSUED y el ALB sirve HTTPS/443; Cloudflare Full (strict) por hostname fue reportado, pero falta revalidar el TLS público.",
    107: "Recuperación: restauración separada con RTO/RPO medidos aún pendiente.",
    108: "Mantenibilidad: infraestructura repetible y parámetros no secretos.",
    109: "Observabilidad: métricas, logs, alarmas y seguimiento de identificador de evento.",
    110: "Costos: presupuesto de USD 200 con alarmas; no es tope que detenga servicios.",
    114: "Restricciones conocidas:",
    115: "Créditos verificados en vivo el 16/11/2026: AWS tiene USD 158,62 disponibles de USD 200; Azure for Students tiene saldo cerrado de USD 92,95 de USD 100. El detalle y el costo facturado usan cortes diferentes.",
    116: "Servicios desplegados: AWS y Azure. La rúbrica base exige AWS–OCI; falta aprobación escrita para la alternativa Azure.",
    117: "AWS us-east-2; Azure West US. No existe región secundaria lista para restaurar.",
    118: "Amazon Linux 2023 en EC2; Linux en routers Azure; PostgreSQL 18.3.",
    119: "CloudFormation, Terraform, Python, portal ERP y Azure Functions Flex.",
    120: "AWS budget USD 200 solo alerta y no detiene recursos; no se encontró presupuesto Azure. Las consultas de costo tienen retraso y no son un hard cap.",
    121: "La fecha académica de entrega debe completar el equipo; esta versión refleja corte técnico 16/11/2026.",
    123: "La aplicación se ejecuta en EC2 (IaaS). RDS PostgreSQL, Functions Flex, Storage y Application Insights son servicios administrados (PaaS). No se inventa una aplicación SaaS de terceros.",
    124: "La selección reduce administración de sistema operativo para base/funciones y conserva control del portal donde hay requisitos de red y runtime.",
    127: "Modelo de despliegue: nube pública en dos proveedores, con integración privada prevista mediante Tailscale; al corte no existe túnel AWS operativo.",
    128: "AWS: nube pública regional us-east-2.",
    129: "No hay nube privada propiedad del proyecto.",
    130: "No es híbrida con centro de datos propio.",
    131: "Multicloud AWS–Azure parcial; no cumple por sí sola el requisito nominal AWS–OCI hasta aceptación docente escrita.",
    133: "La figura separa entrada pública del portal y flujo privado WMS aún no conectado desde AWS.",
    135: "Diagrama lógico textual de la solución real y su brecha principal:",
    136: "Usuarios → Cloudflare Full (strict) por hostname → AWS WAF → ALB HTTPS/443 → ASG EC2 (2–5) → RDS PostgreSQL privada. El flujo AWS → Tailscale → Private Endpoint Azure sigue pendiente.",
    137: "┌ Usuarios ─ Cloudflare ─ WAF ─ ALB HTTP ─ ASG EC2 ─ RDS privada ┐\n└                    ruta VPN AWS → Azure aún no conectada          ┘\nAzure: Private Endpoint → Functions Flex → Queue → Blob / Insights",
    139: "Inventario cloud observado:",
    140: "AWS (cuenta 481056890449) y Azure for Students.",
    141: "AWS us-east-2; Azure West US.",
    142: "AWS us-east-2a y us-east-2b para EC2; RDS en us-east-2b. Azure West US.",
    143: "VPC 10.10.0.0/16 y VNet 10.20.0.0/16.",
    144: "AWS: públicas 10.10.0.0/24 y 10.10.1.0/24; app 10.10.10.0/24 y 10.10.11.0/24; DB 10.10.20.0/24 y 10.10.21.0/24. Azure: cuatro subredes, ver sección de direccionamiento.",
    145: "AWS IGW y un NAT Gateway. Azure VNet y Private Endpoint; no hay Azure VPN Gateway Site-to-Site.",
    146: "Dos EC2 de aplicación en ASG; dos VM Tailscale solo en el lado Azure.",
    147: "RDS PostgreSQL 18.3 Single-AZ; Azure Key Vault existe, no es base de datos.",
    148: "Buckets S3 y Azure Blob/Queues.",
    149: "ALB público en AWS.",
    150: "AWS WAF, security groups, IAM role, Secrets Manager, Azure Private Endpoint/Key Vault y alertas.",
    152: "Diagrama AWS actual en formato lógico; la ruta al router AWS se muestra como pendiente.",
    153: "Internet → WAF/ALB: HTTPS/443 (HTTP/80 redirige) → ASG privado (2 AZ) → RDS (Single-AZ). No se encontraron routers AWS en us-east-2 ni ruta 10.20.1.4/32; no se pudo verificar el flujo privado.",
    155: "No hay OCI en la infraestructura desplegada; no existe diagrama de recursos OCI reales.",
    156: "No se dibuja una topología OCI ficticia. Si el docente exige OCI, debe aprobarse el alcance y desplegarse/probarse antes de la defensa.",
    157: "8.5 Arquitectura híbrida y multinube AWS–Azure",
    158: "La relación esperada es portal AWS → evento con identificador → ruta privada → Azure Function → Queue/Blob → telemetría. Solo se han verificado lados aislados, no el recorrido desde AWS.",
    159: "AWS (WAF, ALB, ASG, RDS) ··· ruta privada aún pendiente ··· Azure (Private Endpoint, Function Flex, Queue, Blob, Insights).",
    162: "La tabla usa CIDR declarados en IaC y la VNet consultada; confirmar subnet exacta si cambia el estado cloud.",
    166: "Direcciones y conectividad relevantes:",
    167: "VPC AWS tangamandapio: 10.10.0.0/16.",
    168: "Subredes públicas 10.10.0.0/24 y 10.10.1.0/24; app 10.10.10.0/24 y 10.10.11.0/24; DB 10.10.20.0/24 y 10.10.21.0/24.",
    169: "Tablas separadas para subredes públicas, aplicación y base; no hay destino 10.20.1.4/32 en la tabla de app.",
    170: "Internet Gateway asociado al ALB público.",
    171: "Un NAT Gateway; genera cargo horario y por datos procesados.",
    172: "ALB 80→8080; app 8080 solo desde ALB; PostgreSQL 5432 desde grupo de aplicación.",
    173: "NACL no es el control principal documentado; revisar reglas por defecto antes de cambios.",
    175: "Azure usa VNet, no OCI VCN. CIDR actual consultado: 10.20.0.0/16.",
    176: "VNet `vnet-tangama-private`, 10.20.0.0/16.",
    177: "`snet-private-workloads` 10.20.0.0/24; `snet-private-endpoints` 10.20.1.0/24; `snet-flex-functions` 10.20.2.0/27; `GatewaySubnet` 10.20.255.0/27.",
    178: "La ruta a 10.20.1.4 funciona dentro de Azure; no se ha creado la ruta de retorno desde AWS.",
    179: "Las VM usan IP pública para salida/administración según la configuración existente; no equivale a un gateway VPN administrado.",
    180: "NAT Gateway Azure: no desplegado/confirmado en esta red.",
    181: "NSG gobierna subredes/VM; revisar directamente si se modifican rutas.",
    182: "OCI Security Lists: no aplican porque OCI no se ha desplegado.",
    184: "La topología debe leerse junto con el SVG actual y distinguir las líneas discontinuas pendientes.",
    185: "VPC AWS → (falta router/route 10.20.1.4/32) → Private Endpoint 10.20.1.4 → Function. Azure tiene dos routers Tailscale que anuncian 10.20.1.0/24.",
    187: "Inventario conocido en el corte 16/11/2026:",
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
    206: "RDS mantiene backups automáticos un día; no hay backup reciente PostgreSQL en Azure Blob.",
    207: "Azure Blob es almacenamiento objeto equivalente; el contenedor de respaldo tiene ciclo de vida de 30 días, pero solo hay un archivo manual antiguo documentado.",
    209: "Ficha de base de datos observada:",
    210: "PostgreSQL 18.3.",
    211: "Amazon RDS PostgreSQL.",
    212: "Instancia administrada Single-AZ; no Multi-AZ.",
    213: "AWS us-east-2, zona us-east-2b.",
    214: "Subredes privadas del DB subnet group, CIDR 10.10.20.0/24 y 10.10.21.0/24.",
    215: "20 GiB; cifrado en reposo; no públicamente accesible; puerto TCP/5432 restringido al grupo de app.",
    216: "Portal ERP AWS y módulos de inventario/ventas/compras.",
    217: "Backups automatizados RDS 1 día. Exportación cifrada a Blob y restore aislado pendientes.",
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
    245: "Navegador→Cloudflare y Cloudflare→ALB usan TLS para el hostname del portal. ACM está ISSUED, ALB tiene listener HTTPS/443 y regla de redirección desde 80; falta un nuevo smoke test público que confirme la cadena completa.",
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
    267: "ACM está ISSUED y el usuario desplegó Full (strict) solo para el hostname del portal; repetir comprobación pública después del cambio.",
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
    295: "CloudFormation terminó UPDATE_COMPLETE y drift IN_SYNC; Terraform fmt/validate se ejecutó localmente sin apply.",
    296: "El inventario actual y las limitaciones se detallan en `iac/ESTADO_REAL_2026-11-16.md`.",
    297: "Continuidad del negocio y recuperación:",
    299: "Portal y RDS son críticos; el WMS y los eventos de inventario afectan la exactitud de stock.",
    301: "Objetivo solicitado para router: ≤5 s. No medido ni garantizado. El reemplazo EC2/ASG puede tomar minutos; no prometer que una VM nueva arranque en 5 s.",
    303: "RDS conserva un día de recuperación automatizada como máximo de retención; RPO de la copia externa no está establecido ni medido.",
    305: "Estado de respaldo:",
    306: "RDS PostgreSQL y objetos críticos de negocio (cuando se configure el job).",
    307: "RDS ofrece recuperación en ventana de 1 día; periodicidad hacia Azure Blob aún no existe.",
    308: "Contenedor Azure privado `tangama-postgres-backups` como destino propuesto.",
    309: "Blob lifecycle: 30 días para ruta postgres; RDS automation: 1 día.",
    311: "Recuperación propuesta: validar hashes y firma del manifiesto; descifrar con Key Vault; restaurar en clúster/instancia aislada distinta; comprobar versión, identidad, tablas y consultas; registrar RTO/RPO; borrar entorno de prueba solo tras revisión. Este procedimiento no se ha completado con copia actual.",
    312: "Integración multicloud desplegada por partes:",
    313: "La guía del proyecto menciona AWS y OCI; la descripción permite otros proveedores opcionales. Este equipo desplegó AWS y Azure y necesita constancia del docente para cerrar el criterio nominal.",
    314: "Inventario y prueba de integración:",
    315: "AWS: portal ERP, ASG y RDS.",
    316: "Azure: Function Flex privada, Queue, Blob, Application Insights y dos routers Tailscale.",
    317: "Transporte deseado: overlay Tailscale; el lado AWS, ruta y DNS privado no existen hoy.",
    318: "Flujo esperado: pedido `event_id` → Function autenticada → Queue/consumidor → Blob/ledger → Insights.",
    319: "TLS, clave específica del handler, idempotencia, redes privadas y secretos en almacenes administrados.",
    320: "HTTP 200 de un hostname público no es prueba de ruta privada ni del procesamiento completo del pedido. La prueba E2E desde AWS está pendiente.",
    322: "Costo al corte 16/11/2026 21:00 UTC: AWS conserva USD 158,62 de crédito de USD 200; Cost Explorer dio USD 0 y GetCredits fue denegado por una SCP, por lo que no hay desglose de cargos. Azure for Students conserva USD 92,95 de USD 100 en el último cierre; Cost Management registró USD 6,842993 MTD en noviembre. El budget AWS USD 200 solo notifica y Azure no tiene budget. Revisar el saldo antes de la defensa; no usar USD 0 como prueba de gasto nulo.",
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
    345: "Seguridad: RDS y storage están cifrados y privados; ACM está ISSUED y el ALB sirve HTTPS/443. Cloudflare Full (strict) por hostname fue reportado por el equipo; falta una verificación externa actual.",
    346: "Disponibilidad: el ASG opera en dos AZ, pero RDS Single-AZ es punto único de fallo.",
    347: "Escalabilidad: el ASG llegó y volvió a cinco/dos automáticamente; 1,47% errores impide aprobar la carga larga.",
    348: "Continuidad: hay retención RDS de un día; no existe restore externo reciente demostrado ni RTO/RPO medidos.",
    349: "Costos: créditos y gasto facturado requieren revisión continua; budget USD 200 es aviso, no techo.",
    350: "Multicloud: AWS/Azure está desplegado parcialmente; la ruta privada desde AWS y la aprobación escrita frente a OCI continúan pendientes.",
    352: "Prioridad de cierre: ruta Tailscale AWS→Azure y evento E2E; backup cifrado/restore; probar entrega de alarmas UPeU/Azure; investigar errores de carga; valorar RDS Multi-AZ y DR regional con costos.",
    354: "Fuentes oficiales y de evidencia:",
    355: "AWS RDS PostgreSQL pricing: https://aws.amazon.com/rds/postgresql/pricing/ · RDS on-demand: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_OnDemandDBInstances.html · VPC/NAT pricing: https://aws.amazon.com/vpc/pricing/ · ALB: https://aws.amazon.com/elasticloadbalancing/pricing/ · WAF: https://aws.amazon.com/waf/pricing/.",
    356: "Azure Functions pricing: https://azure.microsoft.com/en-us/pricing/details/functions/ · Azure VNet: https://learn.microsoft.com/azure/virtual-network/virtual-networks-overview.",
    357: "Caso y evaluación: descripción del proyecto y rúbrica entregadas por el curso; no se agregan fuentes académicas no consultadas.",
    358: "Tailscale subnet routers: https://tailscale.com/docs/features/subnet-routers · Cloudflare Full (strict): https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/.",
    359: "Evidencia técnica incluida en el repositorio:",
    360: "Anexo A: `iac/architecture/cambios-esperados.svg` (actualizado al inventario 16/11/2026).",
    361: "Anexo B: direccionamiento y estado de rutas en `iac/ESTADO_REAL_2026-11-16.md`.",
    362: "Anexo C: tabla de direcciones en esta sección 9.1.",
    363: "Anexo D: reglas principales en sección 13.2 y template CloudFormation.",
    364: "Anexo E: policies/redes se administran en IAM; no se publican credenciales.",
    365: "Anexo F: `iac/cloudformation/` y `iac/environments/`.",
    366: "Anexo G: JSON `evidence/current/aws/` y `evidence/current/azure/`.",
    367: "Anexo H: evidencia de carga, despliegue, health checks y CloudFormation.",
    368: "Anexo I: recuperación cross-cloud aún no comprobada; no hay evidencia de restore actual.",
    369: "Anexo J: saldos y costos consultados el 16/11/2026; Cost Explorer no concuerda con la reducción del crédito AWS. Referencias de precio en sección 21, no son factura.",
    371: "Informe DOCX, manual técnico DOCX, diagramas SVG/Draw.io, IaC CloudFormation/Terraform y evidencias JSON. Integrante, docente y ciclo están completados; faltan capturas autorizadas y aprobación escrita para AWS–Azure.",
    297: "19. Continuidad del negocio y recuperación",
    312: "20. Integración multinube AWS–Azure y cumplimiento de proveedores",
    373: "Estado del cierre técnico",
}


REPORT_TABLES = {
    0: [["PROYECTO INTEGRADOR · TANGAMANDAPIO"]],
    1: [["ALCANCE · Informe técnico basado en el despliegue comprobado. Se distinguen recursos activos, resultados medidos y observaciones que siguen abiertas."]],
    2: [["PROBLEMA TÉCNICO · El escenario académico requiere disponibilidad, crecimiento, conectividad privada entre el portal y el WMS, respaldos recuperables y monitoreo. La arquitectura reduce parte de estas brechas, pero no se declara cerrada mientras falten la ruta privada, la restauración externa y la aprobación del proveedor alternativo."]],
    3: [
        ["Código", "Requisito", "Indicador"],
        ["RF01", "Portal ERP web", "Portal y health checks responden; RBAC en aplicación."],
        ["RF02", "Base centralizada", "RDS PostgreSQL privada, cifrada, Single-AZ."],
        ["RF03", "WMS integrado", "Azure Function privada existe; ruta AWS y pedido E2E pendientes."],
        ["RF04", "Copia recuperable", "RDS 1 día; Blob no tiene backup RDS actual automatizado."],
        ["RNF05", "Observabilidad", "Alarmas AWS/Azure configuradas; Gmail SNS confirmado, entrega de prueba pendiente."],
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
        ["ASG instancia A", "Portal ERP", "AWS us-east-2a", "Amazon Linux 2023", "2 / 1 GiB", "10.10.10.x / App-A"],
        ["ASG instancia B", "Portal ERP", "AWS us-east-2b", "Amazon Linux 2023", "2 / 1 GiB", "10.10.11.x / App-B"],
        ["vm-tangama-ts-pilot", "Router Tailscale Azure", "Azure West US", "Linux", "Standard_B2pts_v2", "10.20.0.4"],
        ["vm-tangama-ts-backup", "Router Tailscale Azure", "Azure West US", "Linux", "Standard_B2pts_v2", "10.20.0.5"],
    ],
    11: [
        ["Origen", "Destino", "Puerto", "Protocolo", "Acción", "Justificación"],
        ["Internet", "WAF / ALB", "443; 80 redirige", "HTTPS; HTTP redirect", "Permitir", "ACM ISSUED; origen HTTPS desplegado; verificar TLS externo."],
        ["SG ALB", "SG app", "8080", "HTTP", "Permitir", "Tráfico solo desde balanceador."],
        ["SG app", "SG RDS", "5432", "PostgreSQL/TLS", "Permitir", "Acceso de aplicación a base privada."],
        ["AWS app", "Azure PE 10.20.1.4", "443", "HTTPS", "Pendiente", "No existe ruta AWS 10.20.1.4/32."],
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
        ["T04", "Pedido privado AWS→Azure", "Function, Queue, Blob, Insights", "Sin ruta /32; sin router AWS encontrado en us-east-2; no probado", "Pendiente"],
        ["T05", "Restore RDS desde Blob", "Hash íntegro y clúster aislado", "No hay copia RDS reciente automatizada", "Pendiente"],
    ],
    5: [["MODELOS CLOUD · EC2 es IaaS; RDS, Functions Flex, Queue, Blob y Application Insights son PaaS. La consola de administración es una herramienta SaaS del proveedor, no una aplicación empresarial contratada para el caso."]],
    8: [["CÓMPUTO · Dos instancias t3.micro en zonas distintas sostienen el portal. El ASG demostró scale-out hasta cinco y scale-in automático; no se ha probado reemplazo tras caída ni 3.000 usuarios concurrentes."]],
    9: [["BASE DE DATOS · Se eligió RDS PostgreSQL para delegar operación del motor. El estado vivo es Single-AZ, cifrado, privado, 20 GiB y retención de un día; no ofrece la misma disponibilidad que Multi-AZ."]],
    10: [["SEGURIDAD · Los roles y reglas de red limitan el acceso entre capas. No se incluyen claves, contraseñas, tokens ni valores de secretos en este informe. Rotar cualquier credencial que haya aparecido en capturas o chats."]],
    12: [["EVIDENCIA DE DISPONIBILIDAD · El 16/11 el ASG cambió automáticamente 2→4→5 y luego 5→4→3→2 bajo carga. Esto prueba escalado, no recuperación ante la caída de una instancia; el RTO de cinco segundos sigue sin comprobar."]],
    13: [["EVIDENCIA FUNCIONAL · La revisión vigente confirmó ALB activo, dos destinos saludables, RDS available y CloudFormation IN_SYNC. Consultar la bitácora fechada y los JSON enlazados; un health check no representa todas las transacciones del ERP."]],
    14: [["OBSERVABILIDAD · Hay cinco alarmas CloudWatch propias y dos reglas Azure habilitadas. Gmail SNS está confirmado; UPeU aparece dos veces PendingConfirmation; falta probar recepción AWS y Azure de extremo a extremo."]],
    15: [["REPRODUCIBILIDAD · CloudFormation reconstruye la pila AWS. Terraform tiene raíces separadas; fmt/validate no equivale a plan ni apply. Los defaults locales de RDS se alinearon al estado vivo, pero no se aplicaron a la nube."]],
    16: [["MULTINUBE · Existen recursos en AWS y Azure; todavía no hay recorrido privado verificado desde la aplicación AWS hasta Function, Queue, Blob y Application Insights. La rúbrica nombra OCI: anexar la aprobación escrita para Azure o desplegar el proveedor solicitado."]],
    18: [["PRUEBA DE ACCESO · El ALB y los destinos aparecen activos/saludables en el último corte. No se documentó una prueba nueva de acceso externo a RDS; el diseño mantiene la base en subred privada y sin endpoint público."]],
    19: [["PRUEBA DE FLUJO · La aplicación y la base están desplegadas. En esta pasada no se usó una consulta transaccional desde el portal como evidencia de ruta AWS→Azure; no afirmar un flujo WMS privado hasta correlacionar su event_id en Azure."]],
    20: [["PRUEBA DE SEGURIDAD · RDS está configurada como privada y cifrada. La matriz registra la postura configurada; no se ejecutó un intento externo nuevo de conexión a PostgreSQL en este corte."]],
    21: [["PRUEBA DE ALTA DISPONIBILIDAD · La prueba registrada cambió capacidad del ASG por demanda y mantuvo dos destinos sanos al cierre. No se detuvo una EC2 ni un router para medir recuperación; el RTO de cinco segundos sigue pendiente."]],
    22: [["PRUEBA DE RESTAURACIÓN · Hay evidencia histórica de un restore aislado, pero no existe una copia actual de esta RDS exportada y cifrada en Blob para restaurarla y medir su RTO/RPO. El objeto manual antiguo no se presenta como backup de la base actual."]],
    23: [["PRUEBA DE ALARMA · Las alarmas AWS estaban en estado OK y Azure tiene reglas habilitadas. Gmail SNS está confirmado, pero no se provocó una alarma controlada ni se probó la recepción humana de AWS/Azure."]],
    25: [["EVIDENCIA · Para cada afirmación se cita la fecha, el archivo y el resultado observado. Los elementos sin registro reciente se marcan como pendientes; no se sustituyen con capturas antiguas ni resultados de laboratorio."]],
    26: [["REFERENCIAS · Se usa un formato autor-fecha simplificado con documentación oficial del proveedor y rutas a evidencia del repositorio. Completar las referencias del curso y los datos bibliográficos exigidos por el docente antes de entregar."]],
    27: [["Proyecto_Final_Tangamandapio/\n├── deliverables/\n│   ├── Proyecto_Final_Tangamandapio_2026-11-16.docx\n│   └── Manual_Tecnico_Tangamandapio_2026-11-16.docx\n├── iac/\n│   ├── cloudformation/ · aws-lab.yaml\n│   ├── environments/ · Terraform por proveedor\n│   ├── architecture/ · SVG y Draw.io actualizados\n│   └── scripts/ · operación y recuperación\n├── evidence/current/ · JSON fechado AWS/Azure\n└── core/ · bitácora y matriz de rúbrica\nNo almacenar claves, tokens ni valores de secretos en el repositorio."]],
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
        for run in table.rows[0].cells[i].paragraphs[0].runs:
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
    document.add_paragraph("La etiqueta CONFIRMADO indica una consulta de nube o evidencia fechada. PENDIENTE indica que no se debe presentar como realizado. Las pruebas históricas del 05/11 no sustituyen el estado actual del 16/11. Los valores de claves, contraseñas, tokens y endpoints secretos se omiten deliberadamente.")
    document.add_heading("Prioridad ejecutiva", level=2)
    add_numbered(document, [
        "ACM ya está ISSUED, el listener HTTPS/443 está desplegado y el usuario informó que Full (strict) está limitado al hostname del portal. Revalidar el HTTPS público de extremo a extremo y guardar evidencia fechada.",
        "Crear y guardar de forma segura las claves de alta Tailscale; desplegar dos routers AWS, forwarding/NAT, ruta 10.20.1.4/32 y DNS privado; ejecutar pedido sintético completo.",
        "Automatizar backup RDS cifrado hacia Azure Blob; restaurar en instancia aislada y medir RPO/RTO.",
        "Gmail SNS está confirmado; revisar las dos suscripciones UPeU pendientes y recibir una alarma de prueba controlada. Comprobar también entrega de Azure.",
        "Investigar el 1,47% de errores de la carga larga; repetir prueba antes de declarar capacidad aprobada.",
        "Adjuntar la aprobación escrita del docente para AWS–Azure como reemplazo del requisito AWS–OCI; OCI no existe en el despliegue.",
    ])

    document.add_heading("1. Inventario vivo", level=1)
    add_table(document, ["Componente", "Estado confirmado", "Brecha"], [
        ["AWS / CloudFormation", "Cuenta 481056890449, us-east-2; stack UPDATE_COMPLETE; parámetros RDS false/1.", "EC2 fuera de us-east-2 bloqueada por SCP p-4lylrj0n; el contenido de la política no es visible desde esta cuenta."],
        ["Portal / ALB / WAF", "ALB y WAF activos; HTTPS/443 y redirección HTTP/80; ACM ISSUED.", "Revalidar HTTPS público con Cloudflare Full (strict) hostname-only."],
        ["ASG", "Min 2, deseado 2, máximo 5; dos EC2 sanas en 2 AZ.", "La carga larga tuvo 1,47% de errores."],
        ["RDS", "PostgreSQL 18.3, db.t3.micro, 20 GiB, privada, cifrada, Single-AZ, retención 1 día.", "No Multi-AZ; no backup reciente hacia Azure ni restore aislado."],
        ["Azure", "Function Flex privada, PE 10.20.1.4, Queue, Blob, Insights, Key Vault, dos routers Tailscale en ejecución.", "No se ve pedido privado reciente originado desde AWS."],
        ["Ruta entre nubes", "Azure anuncia 10.20.1.0/24; las EC2 de app están en us-east-2.", "No existe pila/router AWS ni ruta 10.20.1.4/32; faltan las dos claves Tailscale."],
        ["Alertas", "5 alarmas CloudWatch OK; dos reglas Azure habilitadas; Gmail SNS confirmado.", "UPeU figura dos veces PendingConfirmation; entrega de prueba y Azure no demostradas."],
        ["Costo", "AWS: USD 158,62 de crédito disponible; Azure Students: USD 92,95 de saldo cerrado y USD 6,842993 MTD.", "AWS GetCredits denegado por SCP y Cost Explorer devolvió cero; AWS budget solo avisa. No hay budget Azure."],
    ])

    document.add_heading("2. Arquitectura desplegada y flujo deseado", level=1)
    document.add_paragraph("Entrada actual: navegador → Cloudflare (Full (strict) por hostname, según el cambio reportado) → WAF/ALB AWS (HTTPS/443; HTTP/80 redirige) → ASG EC2 en dos AZ → RDS privada. El flujo WMS deseado añade una ruta privada Tailscale AWS→Azure PE→Function→Queue/consumidor→Blob/Insights, pero el VPC actual no tiene ruta hacia 10.20.1.4/32 y no existe router AWS. En us-east-2 solo aparecen las dos EC2 de app; fuera de esa región una SCP deniega DescribeInstances, por lo que no se concluye inventario global.")
    document.add_page_break()
    add_table(document, ["Red", "Rango", "Subredes", "Uso"], [
        ["AWS VPC", "10.10.0.0/16", "public 10.10.0.0/24, 10.10.1.0/24; app 10.10.10.0/24, 10.10.11.0/24; DB 10.10.20.0/24, 10.10.21.0/24", "ALB, ASG, RDS."],
        ["Azure VNet", "10.20.0.0/16", "workloads 10.20.0.0/24; PE 10.20.1.0/24; Flex 10.20.2.0/27; GatewaySubnet 10.20.255.0/27", "Routers, Function Flex, Private Endpoint."],
    ])
    document.add_paragraph("Puertos actuales: Internet→ALB TCP/443 HTTPS; TCP/80 redirige a 443; ALB→EC2 TCP/8080; EC2→RDS TCP/5432. El acceso privado aplicación→Function TCP/443 sigue pendiente porque no hay router AWS ni ruta /32. No abrir RDS a Internet ni añadir reglas amplias para probar conectividad.")
    document.add_paragraph("Diagrama editable/actualizado: `iac/architecture/cambios-esperados.drawio`; vista SVG: `iac/architecture/cambios-esperados.svg`. El ámbar discontinuo es pendiente, no infraestructura activa.")

    document.add_heading("3. Portal, TLS y DNS", level=1)
    document.add_paragraph("Estado actual: ACM está ISSUED, el ALB ofrece HTTPS/443 y HTTP/80 redirige. El usuario confirmó el despliegue de una regla Cloudflare Full (strict) limitada al hostname `tangamandapio.kendellnm.me`. Falta repetir una comprobación pública que confirme TLS de navegador a Cloudflare y de Cloudflare al ALB.")
    document.add_paragraph("CNAME de validación ACM ya aplicado en modo DNS-only (referencia; no volver a crearlo):")
    add_table(document, ["Tipo", "Nombre", "Destino"], [["CNAME", "_7408575772140ac4b6bcd8e3ab10a8ca.tangamandapio", "_694a9f814a3985f9576fb181841dc9d3.wzccmgtwzk.acm-validations.aws"]])
    add_numbered(document, [
        "Confirmar en ACM, región us-east-2, que el certificado siga `ISSUED`.",
        "Comprobar que el ALB mantenga el listener 443 con el certificado y que el listener 80 solo redirija a HTTPS.",
        "Abrir `https://tangamandapio.kendellnm.me/health` y validar código 200 y cadena TLS desde fuera de AWS.",
        "En Cloudflare, verificar que la Configuration Rule aplique `Full (strict)` solo con Hostname equals `tangamandapio.kendellnm.me`; no cambiar el modo global ni el DNS del portal.",
    ])
    document.add_paragraph("El CNAME y ACM ya se completaron. La comprobación pública HTTPS posterior al cambio queda como evidencia pendiente.")

    document.add_heading("4. Ruta privada AWS–Azure y conmutación", level=1)
    document.add_paragraph("Dependencias verificadas: Azure tiene dos VM `vm-tangama-ts-pilot` (10.20.0.4) y `vm-tangama-ts-backup` (10.20.0.5), ambas Running en Standard_B2pts_v2; anuncian 10.20.1.0/24. El Private Endpoint de Function es 10.20.1.4. El inventario completo de EC2 en us-east-2 solo devolvió las dos instancias de app y no hay ruta /32. Secrets Manager no tiene un secreto cuyo nombre contenga `tailscale`. El cliente local Tailscale muestra `NoState`, mapa de pares vacío y error de sincronización; los nombres de router que imprime su caché no prueban que sigan conectados ni que pertenezcan a esta cuenta.")
    add_numbered(document, [
        "En Tailscale Admin → Settings → Keys, crear dos auth keys de un solo uso, no efímeras, con tag `tag:tangama-aws-router`; nunca pegarlas en el chat, terminal con historial o Git.",
        "Guardar cada valor directamente en AWS Secrets Manager, región us-east-2: `tangamandapio/tailscale/aws-pilot` y `tangamandapio/tailscale/aws-backup`. No incluir valores en informes ni enviarlos por chat.",
        "Empaquetar y desplegar `iac/cloudformation/aws-azure-tailscale-ha.yaml` con `package_tailscale_ha.sh` y `deploy_tailscale_ha.sh`; la ruta se mantiene apagada hasta que ambos routers pasen health check.",
        "Enrolar los routers con `iac/scripts/enrol_tailscale_router.py` usando archivo root-only temporal en `/run`; verificar tag esperado, approval de ruta y DNS privado.",
        "Habilitar forwarding y NAT acotados desde 10.10.10.0/23 hacia 10.20.1.4 TCP/443; añadir ruta /32 a la tabla app solo después de confirmar router/ENI correctos. El helper `ensure_private_wms_route.py` se niega a reemplazar un destino desconocido.",
        "Desde EC2 app, resolver `tangama-flex-261104.azurewebsites.net` a 10.20.1.4 y hacer HTTPS `/api/health`; verificar certificado y código 200. No usar URL pública como prueba privada.",
        "Enviar evento sintético autenticado a `/api/fulfillment/events` con event_id único y clave específica `receive_fulfillment_event`; comprobar Function, mensaje de Queue, Blob/ledger e Insights. No usar la clave de Function para `/api/wms/inventory`.",
        "Solo tras demostrar ambas rutas, probar failover en ventana: captura estado/ruta; detener un router AWS de forma reversible; observar recuperación; medir RTO con timestamps; restaurar router principal y confirmar ruta final. No declarar 5 s antes de medir.",
    ])
    document.add_paragraph("El controlador nuevo `iac/scripts/tailscale_ha_controller.py` requiere los dos routers enrolados y sanos y que se habilite la ruta /32 protegida. El RTO objetivo de 5 s no se puede afirmar hasta medir caída y recuperación; los routers AWS aún no existen.")

    document.add_heading("5. Backup y restauración PostgreSQL→Azure Blob", level=1)
    document.add_paragraph("Estado: RDS tiene recuperación automática de un día. Azure Blob contiene un artefacto manual del 05/11, no un dump actual de la RDS de esta cuenta. `postgres_dr_pilot.py` crea dump custom, manifiesto SHA-256 y restauración aislada; por diseño no cifra, no sube ni agenda. `postgres_backup_crypto.py` protege un payload AES-256-GCM y envuelve la clave de datos con RSA-OAEP-SHA256 usando una clave pública versionada de Key Vault; descifrar requiere acceso autorizado a la clave privada de Key Vault. No usar estos scripts para producción sin cerrar el job y los controles.")
    add_bullets(document, [
        "Precondición de red: job debe alcanzar RDS privado por TLS verify-full y Blob por HTTPS; usar egress existente con costo medido.",
        "Autenticación de escritura: identidad de workload de mínimo privilegio para Blob y permiso de uso de clave pública de Key Vault. No usar SAS perpetuo ni account key en texto plano.",
        "Backup: `pg_dump --format=custom --no-owner --no-privileges`; validar versión y cluster identity; generar manifiesto y hashes; cifrar antes de subir; subir a contenedor privado con versioning/retención.",
        "Programación: EventBridge Scheduler + tarea contenedorizada en subred app o mecanismo equivalente. CloudWatch alarmará fallo de job, antigüedad de backup y objeto ausente. Requiere diseño/estimación y no está desplegado.",
        "Restore: descargar una copia concreta, validar hash autenticado, descifrar vía Key Vault, restaurar a RDS aislada distinta a producción, verificar tablas y consultas; registrar tiempo de recuperación y punto de datos.",
        "Retención: Blob lifecycle de 30 días existe para la ruta postgres; asegurar que no elimine la última copia válida y almacenar hashes/manifest independiente.",
    ])
    document.add_paragraph("RPO y RTO deben medirse con timestamps del backup y restore. Retención de 1 día no prueba que exista un restore de Blob. No ejecutar restore sobre producción.")

    document.add_heading("6. Auto Scaling, alarmas y prueba", level=1)
    document.add_paragraph("Configuración comprobada: ASG min 2 / desired 2 / max 5, CPU objetivo 60%, solicitudes por destino 2.500/min. El 16/11, 300.000 solicitudes con concurrencia 50 duraron 1.645,443 s; p95 315,47 ms; 1,47% errores (8 respuestas 502 y 4.399 errores de red). Auto Scaling llegó 2→4→5 y bajó automáticamente 5→4→3→2. Postcheck 3.000 solicitudes, concurrencia 30: cero errores, p95 263,86 ms. No es prueba de 3.000 usuarios concurrentes.")
    add_bullets(document, [
        "Antes de repetir: limitar tasa y duración, revisar acceso logs del ALB/WAF y métricas TargetResponseTime/HTTPCode_Target_5XX, CPU, RDS connections/CPU, cliente de carga y errores URLError detallados.",
        "Ejecutar escalones conservadores, no saltar directamente a 300.000; conservar hora UTC, p50/p95/p99, HTTP 2xx/4xx/5xx, errores cliente, DesiredCapacity y scaling activities.",
        "Dejar que scaling policies reduzcan capacidad; no cambiar DesiredCapacity durante la fase de medición.",
        "Las cinco alarmas custom actuales son high CPU, in-service capacity, RDS high CPU, target 5xx y unhealthy targets; todas estaban OK. Eventos ASG publican en SNS.",
        "SNS Gmail está confirmado; UPeU aparece dos veces PendingConfirmation. Hace falta una alarma controlada no productiva con recepción comprobada y revisar el duplicado UPeU.",
        "Las dos alertas de Azure están habilitadas, pero su disparo y entrega humana no están demostrados; usar una señal controlada de laboratorio.",
    ])

    document.add_heading("7. Terraform, CloudFormation y emulación", level=1)
    document.add_paragraph("CloudFormation es la fuente actual de verdad para AWS. La pila viva quedó IN_SYNC. Terraform se organiza en varias raíces independientes; `azure-rebuild` pasó `init -backend=false` y `validate` y las raíces se formatearon, pero no se aplicaron. Importar recursos Azure existentes a la raíz correcta antes de plan/apply. No ejecutar `iac/environments/demo` sobre esta cuenta: puede duplicar la VPC/CIDR.")
    document.add_paragraph("En este cambio local, `aws-lab.yaml` y `rebuild.sh` alinean por defecto RDS Multi-AZ=false y retención=1 con el estado vivo. CloudFormation linter pasó; cinco pruebas locales pasan. Esto no altera la pila AWS. Multi-AZ y retención mayor se deben habilitar explícitamente solo después de revisar costo, cuotas y change set.")
    document.add_paragraph("Moto/emulador valida lógica compatible de APIs y no simula precios, límites reales, RDS Multi-AZ, WAF gestionado, Tailscale, DNS/ACM ni latencia del servicio en vivo.")

    document.add_heading("8. Costos y control del crédito", level=1)
    document.add_paragraph("Corte 16/11/2026 21:00 UTC: AWS Free Plan ACTIVE, USD 158,62 restantes de USD 200; la diferencia consumida de crédito es USD 41,38. Cost Explorer devolvió USD 0 en octubre y noviembre, pero el saldo del plan bajó; GetCredits fue denegado por SCP, sin desglose por servicio. El budget AWS de USD 200 solo notifica. Azure for Students: USD 92,95 de saldo cerrado de USD 100 y USD 6,842993 de costo MTD en noviembre; los cortes difieren y Cost Management puede retrasarse. No hay budget Azure. Evidencia: `evidence/current/COST-CREDIT-RECHECK-2026-11-16-2100.json`.")
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
        ["Portal", "`/`, `/health`, `/ready` HTTP 200 en corte anterior.", "Revalidar tras listener TLS."],
        ["Scale-out/in", "2→4→5→4→3→2; 1,47% error larga.", "Investigar errores; repetir bajo 1% y guardar evidencia."],
        ["Postcheck", "3.000 req, 0 errores, p95 263,86 ms.", "No equivale a 3.000 usuarios."],
        ["Ruta privada AWS→Azure", "No existe pila/router AWS ni route /32 a 10.20.1.4; faltan las dos claves Tailscale.", "Enrolar los routers, activar ruta segura y verificar pedido en Function, Queue, Blob e Insights."],
        ["Failover routers", "No se ejecutó en AWS nuevo.", "Prueba reversible; medir con timestamps; no suponer 5 s."],
        ["Backup/restore", "No automatizado; archivo manual antiguo.", "Copia reciente cifrada en Blob y restore aislado."],
        ["Alarmas", "5 AWS OK; 2 Azure habilitadas; Gmail SNS confirmado.", "Confirmar UPeU, disparar alarma controlada y comprobar recepción Azure."],
        ["TLS", "ACM ISSUED; ALB 443 y redirect 80; regla Full strict reportada.", "Repetir HTTPS público y adjuntar captura/cadena TLS."],
    ])

    document.add_heading("10. Anexos y fuentes", level=1)
    add_bullets(document, [
        "Estado e inventario: `iac/ESTADO_REAL_2026-11-16.md`.",
        "Matriz por criterio: `core/04_matriz_rubrica.md`.",
        "Pruebas ASG: `evidence/current/aws/AWS-ASG-SCALE-2-5-2026-11-16-http.json`, `AWS-ASG-SCALE-POSTCHECK-2026-11-16-http.json` y evidencia cloud consolidada.",
        "Código DR local: `iac/scripts/postgres_dr_pilot.py` y `iac/scripts/postgres_backup_crypto.py`; no son aún un scheduler/cloud deployment.",
        "AWS pricing: https://aws.amazon.com/ec2/instance-types/t3/ ; https://aws.amazon.com/vpc/pricing/ ; https://aws.amazon.com/elasticloadbalancing/pricing/ ; https://aws.amazon.com/waf/pricing/ ; https://aws.amazon.com/rds/postgresql/pricing/.",
        "Tailscale subnet routers: https://tailscale.com/docs/features/subnet-routers. Cloudflare strict: https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/.",
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
