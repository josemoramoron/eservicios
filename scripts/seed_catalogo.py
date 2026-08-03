"""Carga inicial (seed) del catálogo de eServicios.

Uso (desde la raíz del proyecto, con el venv activo):
    python scripts/seed_catalogo.py

Idempotente: usa el `slug` como clave. Si la categoría u oferta ya
existe, actualiza sus campos en vez de duplicarla — se puede correr
tantas veces como haga falta (ej. después de editar este archivo).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

# Al correr este archivo directamente (`python scripts/seed_catalogo.py`),
# Python solo agrega la carpeta `scripts/` a sys.path, no la raíz del
# proyecto — por eso `from app import ...` fallaba con ModuleNotFoundError.
# Se agrega la raíz (un nivel arriba de este archivo) a mano.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Category, Offering, TipoOffering  # noqa: E402

CATEGORIAS: list[dict] = [
    {
        "slug": "domotica",
        "nombre": "Domótica y Hogar Inteligente",
        "descripcion": "Automatización residencial y control inteligente del hogar.",
        "orden": 1,
        "ofertas": [
            dict(
                slug="casa-domotica",
                nombre="Instalación de Casa Domótica / Smart Home",
                tipo=TipoOffering.SERVICIO,
                descripcion="Automatización de iluminación, seguridad, climatización, cerraduras y dispositivos del hogar.",
                vendible=False,
                destacado=True,
            ),
            dict(
                slug="iot-home-assistant",
                nombre="Ecosistema IoT y Home Assistant (Zigbee, Z-Wave)",
                tipo=TipoOffering.SERVICIO,
                descripcion="Integración de sensores y protocolos IoT bajo una plataforma centralizada de código abierto.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "infraestructura-servidores",
        "nombre": "Infraestructura y Servidores",
        "descripcion": "Construcción y administración de servidores propios, locales y en la nube.",
        "orden": 2,
        "ofertas": [
            dict(
                slug="servidores-locales-web",
                nombre="Construcción de Servidores Locales y Web",
                tipo=TipoOffering.SERVICIO,
                descripcion="NAS, Nextcloud, sitios web y plataformas a medida, alojadas en casa o en la nube.",
                vendible=False,
                destacado=True,
            ),
            dict(
                slug="servidores-correo",
                nombre="Servidores de Correo Electrónico",
                tipo=TipoOffering.SERVICIO,
                descripcion="Implementación, migración y administración de correo corporativo propio.",
                vendible=False,
            ),
            dict(
                slug="soluciones-raspberry-pi",
                nombre="Soluciones con Raspberry Pi",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Proyectos, equipos armados y configuraciones a medida sobre Raspberry Pi.",
                vendible=True,
                precio=Decimal("120.00"),
            ),
            dict(
                slug="servidor-sms",
                nombre="Servidor SMS (Twilio, eSIM)",
                tipo=TipoOffering.SERVICIO,
                descripcion="Mensajería SMS programable con proveedores como Twilio y tecnología eSIM.",
                vendible=False,
            ),
            dict(
                slug="backup-recuperacion-datos",
                nombre="Backup y Recuperación de Datos",
                tipo=TipoOffering.SERVICIO,
                descripcion="Respaldo automatizado y recuperación de discos o archivos borrados.",
                vendible=False,
            ),
            dict(
                slug="ia-autoalojada",
                nombre="Servidores de IA Autoalojada",
                tipo=TipoOffering.SERVICIO,
                descripcion="Modelos de IA locales (Ollama, LLMs propios) y asistentes personalizados sin depender de la nube.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "redes-seguridad-privacidad",
        "nombre": "Redes, Seguridad y Privacidad",
        "descripcion": "Protección de redes, dispositivos e identidad digital.",
        "orden": 3,
        "ofertas": [
            dict(
                slug="wireguard",
                nombre="WireGuard",
                tipo=TipoOffering.SERVICIO,
                descripcion="Configuración de redes privadas virtuales (VPN) seguras y de bajo consumo.",
                vendible=False,
                destacado=True,
            ),
            dict(
                slug="auditorias-flipper-zero",
                nombre="Auditorías de Red con Flipper Zero",
                tipo=TipoOffering.SERVICIO,
                descripcion="Pruebas de penetración y análisis de vulnerabilidades en redes y dispositivos.",
                vendible=False,
            ),
            dict(
                slug="privacidad-moviles",
                nombre="Privacidad en Dispositivos Móviles y Portátiles",
                tipo=TipoOffering.SERVICIO,
                descripcion="Hardening e instalación de sistemas enfocados en privacidad: GrapheneOS, ParrotOS.",
                vendible=False,
            ),
            dict(
                slug="ciberseguridad-ofensiva",
                nombre="Ciberseguridad Ofensiva y Respuesta a Incidentes",
                tipo=TipoOffering.SERVICIO,
                descripcion="Pentesting de aplicaciones y sitios web, y atención a incidentes de seguridad.",
                vendible=False,
            ),
            dict(
                slug="redes-cableadas-wifi",
                nombre="Redes Cableadas y WiFi Empresarial / Mesh",
                tipo=TipoOffering.SERVICIO,
                descripcion="Cableado estructurado, puntos de acceso y redes mesh para hogar u oficina.",
                vendible=False,
            ),
            dict(
                slug="firmware-routers",
                nombre="Firmware Personalizado para Routers (OpenWrt/DD-WRT)",
                tipo=TipoOffering.SERVICIO,
                descripcion="Flasheo y configuración avanzada de routers con firmware libre.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "desarrollo-automatizacion-datos",
        "nombre": "Desarrollo, Automatización y Datos",
        "descripcion": "Software a medida, automatización de procesos y gestión de información.",
        "orden": 4,
        "ofertas": [
            dict(
                slug="automatizaciones-web-telegram-whatsapp",
                nombre="Automatizaciones (Sitios Web, Telegram, WhatsApp)",
                tipo=TipoOffering.SERVICIO,
                descripcion="Bots y flujos automatizados de atención, ventas y procesos internos.",
                vendible=False,
                destacado=True,
            ),
            dict(
                slug="crud-crm-erp",
                nombre="Sistemas CRUD / CRM / ERP",
                tipo=TipoOffering.SERVICIO,
                descripcion="Sistemas administrativos a medida para gestión comercial y operativa.",
                vendible=False,
            ),
            dict(
                slug="bbdd-analisis-datos",
                nombre="Bases de Datos y Análisis de Datos",
                tipo=TipoOffering.SERVICIO,
                descripcion="Diseño de bases de datos, reportería y análisis de datos para negocio.",
                vendible=False,
            ),
            dict(
                slug="obsidian-note",
                nombre="Obsidian Note — Gestión del Conocimiento",
                tipo=TipoOffering.CURSO,
                descripcion="Implementación y capacitación en sistemas de notas y segundo cerebro digital.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "blockchain-criptoactivos",
        "nombre": "Blockchain y Criptoactivos",
        "descripcion": "Acompañamiento estratégico en el ecosistema cripto.",
        "orden": 5,
        "ofertas": [
            dict(
                slug="consultoria-cripto",
                nombre="Consultoría del Ecosistema Cripto",
                tipo=TipoOffering.CONSULTORIA,
                descripcion="Proyectos, inversión, wallets, contratos inteligentes, Dapps y validadores (ej. Akash Network).",
                vendible=False,
                destacado=True,
            ),
        ],
    },
    {
        "slug": "diseno-impresion-3d",
        "nombre": "Diseño e Impresión 3D",
        "descripcion": "Fabricación digital y experiencias inmersivas.",
        "orden": 6,
        "ofertas": [
            dict(
                slug="impresiones-3d",
                nombre="Impresiones 3D",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Fabricación de piezas, prototipos y modelos a pedido.",
                vendible=True,
                precio=Decimal("15.00"),
                destacado=True,
            ),
            dict(
                slug="diseno-3d-inmersivo-inmuebles",
                nombre="Diseño 3D Inmersivo para Inmuebles",
                tipo=TipoOffering.SERVICIO,
                descripcion="Recorridos virtuales estilo Minecraft para visitas y presentación de propiedades.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "redes-sociales-monetizacion",
        "nombre": "Redes Sociales y Monetización Digital",
        "descripcion": "Escalado de cuentas y contenido en plataformas sociales.",
        "orden": 7,
        "ofertas": [
            dict(
                slug="vmos-cloud",
                nombre="VMOS Cloud",
                tipo=TipoOffering.SERVICIO,
                descripcion="Clonación y gestión en la nube para monetización en TikTok, Clapper y otras plataformas.",
                vendible=False,
                destacado=True,
            ),
            dict(
                slug="marketing-digital-rrss",
                nombre="Gestión de Contenido y Marketing Digital en RRSS",
                tipo=TipoOffering.SERVICIO,
                descripcion="Manejo de cuentas, creación de contenido y crecimiento orgánico en redes sociales.",
                vendible=False,
            ),
        ],
    },
    {
        "slug": "hardware",
        "nombre": "Compra y Venta de Equipos (Hardware)",
        "descripcion": "Intermediación y comercialización de tecnología.",
        "orden": 8,
        "ofertas": [
            dict(
                slug="laptops-placas-madre",
                nombre="Laptops y Placas Madre",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de equipos y componentes.",
                vendible=True,
                precio=Decimal("350.00"),
            ),
            dict(
                slug="telefonos-moviles",
                nombre="Teléfonos Móviles",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de dispositivos móviles.",
                vendible=True,
                precio=Decimal("200.00"),
            ),
            dict(
                slug="drones",
                nombre="Drones",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de drones.",
                vendible=True,
                precio=Decimal("150.00"),
            ),
            dict(
                slug="cascos-realidad-virtual",
                nombre="Cascos de Realidad Virtual",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de equipos de RV.",
                vendible=True,
                precio=Decimal("250.00"),
            ),
            dict(
                slug="lentes-ia",
                nombre="Lentes con IA",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de lentes inteligentes con IA.",
                vendible=True,
                precio=Decimal("300.00"),
                destacado=True,
            ),
            dict(
                slug="raspberry-pi",
                nombre="Raspberry Pi",
                tipo=TipoOffering.PRODUCTO,
                descripcion="Compra, venta e intermediación de placas Raspberry Pi.",
                vendible=True,
                precio=Decimal("60.00"),
            ),
        ],
    },
    {
        "slug": "consultoria-soporte",
        "nombre": "Consultoría y Soporte Técnico",
        "descripcion": "Acompañamiento transversal a todas las áreas anteriores.",
        "orden": 9,
        "ofertas": [
            dict(
                slug="consultoria-soporte-presencial-remoto",
                nombre="Consultoría y Soporte Presencial / Remoto",
                tipo=TipoOffering.CONSULTORIA,
                descripcion="Atención personalizada, presencial o remota, para cualquiera de las áreas del catálogo.",
                vendible=False,
                destacado=True,
            ),
        ],
    },
    {
        "slug": "educacion-formacion",
        "nombre": "Educación y Formación (Academia)",
        "descripcion": "Rutas de aprendizaje sobre cualquier área del catálogo.",
        "orden": 10,
        "ofertas": [
            dict(
                slug="cursos-certificaciones",
                nombre="Cursos y Certificaciones por Área Técnica",
                tipo=TipoOffering.CURSO,
                descripcion="Rutas de aprendizaje básico, intermedio y avanzado, individuales o grupales, sobre cualquiera de las áreas de este catálogo.",
                vendible=False,
                destacado=True,
            ),
        ],
    },
]


def upsert_categoria(datos: dict) -> Category:
    """Crea o actualiza una categoría por su slug.

    El ícono se deriva del slug (`app/static/img/categorias/<slug>.svg`),
    así que no hace falta declararlo a mano en cada entrada de `CATEGORIAS`.

    Args:
        datos: Diccionario con nombre, slug, descripcion y orden.

    Returns:
        La instancia de `Category` creada o actualizada.
    """
    categoria = Category.query.filter_by(slug=datos["slug"]).first()
    if categoria is None:
        categoria = Category(slug=datos["slug"])
        db.session.add(categoria)
    categoria.nombre = datos["nombre"]
    categoria.descripcion = datos["descripcion"]
    categoria.orden = datos["orden"]
    categoria.imagen_url = f"/static/img/categorias/{datos['slug']}.svg"
    return categoria


def upsert_oferta(categoria: Category, datos: dict) -> Offering:
    """Crea o actualiza una oferta por su slug.

    Args:
        categoria: Categoría a la que pertenece la oferta.
        datos: Diccionario con los campos del `Offering`.

    Returns:
        La instancia de `Offering` creada o actualizada.
    """
    oferta = Offering.query.filter_by(slug=datos["slug"]).first()
    if oferta is None:
        oferta = Offering(slug=datos["slug"])
        db.session.add(oferta)
    oferta.category = categoria
    oferta.nombre = datos["nombre"]
    oferta.tipo = datos["tipo"]
    oferta.descripcion = datos["descripcion"]
    oferta.precio = datos.get("precio")
    oferta.vendible = datos.get("vendible", False)
    oferta.destacado = datos.get("destacado", False)
    oferta.activo = True
    return oferta


def seed() -> None:
    """Carga (o actualiza) todas las categorías y ofertas del catálogo."""
    total_ofertas = 0
    for datos_categoria in CATEGORIAS:
        categoria = upsert_categoria(datos_categoria)
        for datos_oferta in datos_categoria["ofertas"]:
            upsert_oferta(categoria, datos_oferta)
            total_ofertas += 1
    db.session.commit()
    print(f"Listo: {len(CATEGORIAS)} categorías, {total_ofertas} ofertas.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
