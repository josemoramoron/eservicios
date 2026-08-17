"""Application factory de eServicios."""
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, url_for

from app.extensions import db, migrate
from config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    """Crea y configura la instancia de la aplicación Flask.

    Args:
        config_class: Clase de configuración a usar.

    Returns:
        Instancia de Flask lista para correr.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  (registra los modelos para Flask-Migrate)
    from app.routes.admin import admin_bp
    from app.routes.health import health_bp
    from app.routes.servicios import servicios_bp
    from app.services.iconos_service import obtener_icono_categoria, obtener_icono_red
    from app.services.site_info_service import obtener_info_sitio

    app.register_blueprint(health_bp)
    app.register_blueprint(servicios_bp)
    app.register_blueprint(admin_bp)
    app.jinja_env.globals["icono_categoria"] = obtener_icono_categoria
    app.jinja_env.globals["icono_red"] = obtener_icono_red

    def estatico_v(nombre_archivo: str) -> str:
        """URL de un archivo estático con un parámetro `?v=` de cache-busting.

        El valor de `v` es la fecha de modificación del archivo, así que
        cambia solo cuando el archivo cambia — cada deploy invalida el
        caché del navegador y de Cloudflare para ese archivo automáticamente,
        sin depender de una purga manual.

        Args:
            nombre_archivo: Ruta relativa a `app/static/`, ej. "css/style.css".

        Returns:
            URL del archivo estático con `?v=<timestamp>` si el archivo
            existe, o la URL simple si no se pudo leer la fecha de modificación.
        """
        ruta = Path(app.static_folder) / nombre_archivo
        try:
            version = int(ruta.stat().st_mtime)
        except OSError:
            return url_for("static", filename=nombre_archivo)
        return url_for("static", filename=nombre_archivo, v=version)

    app.jinja_env.globals["estatico_v"] = estatico_v

    @app.context_processor
    def inyectar_info_sitio() -> dict:
        """Expone `sitio` (contacto/redes) y el año actual a las plantillas.

        Returns:
            Diccionario con las claves `sitio` y `anio_actual` para Jinja.
        """
        return {"sitio": obtener_info_sitio(), "anio_actual": datetime.now(timezone.utc).year}

    return app
