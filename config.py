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
