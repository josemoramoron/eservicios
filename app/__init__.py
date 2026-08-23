"""Application factory de eServicios."""
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, g, redirect, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

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
    from app.routes.blog import blog_bp
    from app.routes.health import health_bp
    from app.routes.producto import producto_bp
    from app.routes.servicios import servicios_bp
    from app.routes.tienda import renderizar_tienda
    from app.routes.vendedor import vendedor_bp
    from app.services.iconos_service import obtener_icono_categoria, obtener_icono_red
    from app.services.site_info_service import obtener_info_sitio
    from app.services.subdominio_service import resolver_vendor_por_host
    from app.services.vendor_service import obtener_vendor_por_slug_activo

    app.register_blueprint(health_bp)
    app.register_blueprint(servicios_bp)
    app.register_blueprint(producto_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(vendedor_bp)
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

    def url_absoluta(ruta: str) -> str:
        """Convierte una ruta de imagen (`/static/...`) en una URL absoluta.

        Las miniaturas de WhatsApp, Facebook, etc. (metaetiquetas Open Graph)
        exigen una URL completa (`https://eservicios.org/static/...`), no
        una ruta relativa — de lo contrario el scraper de la red social no
        encuentra la imagen. Si `ruta` ya es una URL absoluta (empieza con
        `http`, ej. una imagen servida desde Cloudflare R2), se devuelve tal
        cual.

        Args:
            ruta: Ruta o URL guardada en `imagen_url` de un modelo.

        Returns:
            URL absoluta lista para usar en una metaetiqueta.
        """
        if ruta.startswith(("http://", "https://")):
            return ruta
        return request.url_root.rstrip("/") + ruta

    app.jinja_env.globals["url_absoluta"] = url_absoluta

    @app.context_processor
    def inyectar_info_sitio() -> dict:
        """Expone `sitio` (contacto/redes) y el año actual a las plantillas.

        Returns:
            Diccionario con las claves `sitio` y `anio_actual` para Jinja.
        """
        return {"sitio": obtener_info_sitio(), "anio_actual": datetime.now(timezone.utc).year}

    @app.errorhandler(RequestEntityTooLarge)
    def _archivo_demasiado_grande(_error):
        """Convierte el 413 de Flask (request más grande que `MAX_CONTENT_LENGTH`) en un flash amigable.

        Se dispara, por ejemplo, si alguien intenta subir una foto de
        producto o un logo muy pesado desde el panel de vendedor.

        Returns:
            Redirección a la página anterior con un mensaje flash de error.
        """
        flash("El archivo es demasiado grande. El máximo por imagen es 5 MB.", "error")
        return redirect(request.referrer or url_for("vendedor.dashboard"))

    @app.before_request
    def enrutar_subdominio_vendedor():
        """Sirve la tienda pública de un vendedor si el host es su subdominio.

        Cualquier ruta dentro del subdominio de una tienda (incluida `/`)
        muestra esa misma tienda — es una página única por vendedor, no
        un sitio con varias rutas propias. Los archivos estáticos
        (`/static/...`) se excluyen explícitamente para que el CSS/JS de
        la tienda (y del resto del sitio) sigan cargando con normalidad
        aunque el host sea un subdominio de vendedor.

        En desarrollo local, como no hay subdominios reales en
        `localhost`, se puede simular con `?preview_vendor=<slug>`.

        Returns:
            El HTML de la tienda si el host corresponde a un vendedor
            activo, o None para seguir el enrutamiento normal de Flask.
        """
        if request.path.startswith("/static/"):
            return None

        slug_preview = request.args.get("preview_vendor")
        vendor = (
            obtener_vendor_por_slug_activo(slug_preview)
            if slug_preview
            else resolver_vendor_por_host(request.host, app.config["SITE_DOMAIN"])
        )
        if vendor is None:
            return None
        g.vendor = vendor
        return renderizar_tienda(vendor)

    return app
