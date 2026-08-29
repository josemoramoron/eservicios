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
