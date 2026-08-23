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

    # Límite de tamaño de request completo (Flask lo rechaza con 413 antes de
    # leer el body si se supera) — cubre con margen los casos con logo +
    # portada + foto de producto en un mismo formulario (5 MB cada una).
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024
