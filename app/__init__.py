"""Application factory de eServicios."""
from flask import Flask

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

    from app.routes.health import health_bp

    app.register_blueprint(health_bp)

    return app
