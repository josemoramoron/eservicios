"""Configuración de la aplicación, cargada desde variables de entorno."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuración base de Flask para eServicios."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eservicios_dev"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    SITE_DOMAIN: str = os.environ.get("SITE_DOMAIN", "eservicios.org")

    # Cloudflare R2 (fotos de perfil, portada y productos de las tiendas de
    # vendedor — ver app/services/r2_service.py). R2_PUBLIC_BASE_URL es el
    # dominio público conectado al bucket (ej. "https://cdn.eservicios.org"),
    # distinto del endpoint S3 privado que arma r2_service con R2_ACCOUNT_ID.
    R2_ACCOUNT_ID: str = os.environ.get("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET: str = os.environ.get("R2_BUCKET", "eservicios-vendor-photos")
    R2_PUBLIC_BASE_URL: str = os.environ.get("R2_PUBLIC_BASE_URL", "")

    # Brevo (envío del código de verificación de correo del vendedor — ver
    # app/services/email_service.py). Se usa el relay SMTP de Brevo en vez
    # de su API HTTP para no añadir una dependencia nueva a requirements.txt
    # (smtplib es de la librería estándar). BREVO_SMTP_LOGIN es el correo
    # de tu cuenta Brevo; BREVO_SMTP_PASSWORD es la "SMTP key" que genera
    # Brevo (Settings → SMTP & API), no la contraseña de la cuenta.
    BREVO_SMTP_HOST: str = os.environ.get("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
    BREVO_SMTP_PORT: int = int(os.environ.get("BREVO_SMTP_PORT", "587"))
    BREVO_SMTP_LOGIN: str = os.environ.get("BREVO_SMTP_LOGIN", "")
    BREVO_SMTP_PASSWORD: str = os.environ.get("BREVO_SMTP_PASSWORD", "")
    BREVO_REMITENTE: str = os.environ.get("BREVO_REMITENTE", "no-responder@eservicios.org")

    # Límite de tamaño de request completo (Flask lo rechaza con 413 antes de
    # leer el body si se supera) — cubre con margen los casos con logo +
    # portada + foto de producto en un mismo formulario (5 MB cada una).
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024

    # "Iniciar sesión con Google" del vendedor (ver app/services/google_auth_service.py
    # y las rutas /vendedor/auth/google*). Se generan en Google Cloud Console
    # (APIs & Services → Credentials → Create Credentials → OAuth client ID,
    # tipo "Web application"), con esta URL exacta como "Authorized redirect URI":
    # https://eservicios.org/vendedor/auth/google/callback (y la variante con
    # localhost:5000 para probar en local). Vacíos por defecto: el botón de
    # Google queda ahí pero fallará hasta que se configuren estas dos claves.
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Verificación de WhatsApp del vendedor vía Meta WhatsApp Business
    # Platform / Cloud API (roadmap Fase 0, punto 1 — ver
    # claude/spec-tiendas-vendedor.md, sección 11, y el futuro
    # app/services/whatsapp_business_service.py). Mismo criterio que
    # BREVO_*: nunca hardcodear estos valores ni pegarlos en el chat —
    # van directo al .env del servidor (y al .env local mientras se
    # prueba con el número de prueba gratuito de Meta).
    #
    # WHATSAPP_PHONE_NUMBER_ID es el ID interno del número (ej.
    # "1313508931841287"), NO el número de teléfono en sí (ej.
    # "+1 555 203 2276") — Meta los trata como dos cosas distintas; el
    # endpoint de envío siempre usa este ID, nunca el número visible.
    # Ambos valores se ven en el panel de WhatsApp Manager, dentro de la
    # App de Meta (API Setup → "From" phone number).
    WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    # ID de la WhatsApp Business Account (WABA) — no hace falta para
    # mandar mensajes (eso solo usa WHATSAPP_PHONE_NUMBER_ID), pero se
    # guarda para futuras tareas de administración (ej. un script propio
    # que cree/liste plantillas por API en vez de hacerlo a mano desde
    # WhatsApp Manager).
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    # Token de acceso — durante las pruebas con el número gratuito de
    # Meta es el token temporal (vence en ~24 horas, hay que regenerarlo
    # seguido desde el panel); antes de pasar a producción con el número
    # real hay que reemplazarlo por un token permanente (System User,
    # generado una sola vez desde Business Settings → System Users).
    WHATSAPP_CLOUD_API_TOKEN: str = os.environ.get("WHATSAPP_CLOUD_API_TOKEN", "")
    # Versión de la Graph API que usa el endpoint de envío (ej. "v25.0",
    # la que te dio Meta en el ejemplo de curl) — Meta va sacando
    # versiones nuevas con el tiempo, así que queda configurable en vez
    # de hardcodeada en el servicio.
    WHATSAPP_API_VERSION: str = os.environ.get("WHATSAPP_API_VERSION", "v25.0")
    # Nombre de la plantilla de categoría "Authentication" (código +
    # botón "Copiar código") que hay que crear y que Meta tiene que
    # aprobar — NO la plantilla de ejemplo "jaspers_market_order_..."
    # que trae la cuenta por defecto, esa es solo la demo genérica de
    # Meta para probar la conexión, no sirve para el código de
    # verificación real. Vacío por defecto: el servicio de envío falla
    # con un error claro si se intenta usar antes de tener una plantilla
    # real aprobada y configurada acá.
    WHATSAPP_TEMPLATE_NAME: str = os.environ.get("WHATSAPP_TEMPLATE_NAME", "")
    # Código de idioma de esa plantilla, tal como quede registrado al
    # crearla en WhatsApp Manager (ej. "es_MX", "es_LA" o "en_US" según
    # cuál elijas) — tiene que coincidir exacto con el idioma aprobado,
    # si no la API rechaza el envío.
    WHATSAPP_TEMPLATE_IDIOMA: str = os.environ.get("WHATSAPP_TEMPLATE_IDIOMA", "es_MX")
