"""Application factory de eServicios."""
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from app.extensions import db, migrate
from config import Config


def _check_secret_key_or_fail(app: Flask, is_production: bool) -> None:
    """Fail-fast: en producción, un SECRET_KEY ausente o en su valor de
    desarrollo comprometería la firma de las cookies de sesión — el login
    de /admin y /e-link depende enteramente de eso (ver
    app/services/auth_service.py, que usa la cookie de sesión de Flask, no
    una tabla de sesiones en la base de datos). Mejor que el proceso no
    arranque a que arranque firmando sesiones con un secreto público o
    predecible. Mismo patrón que Ceiba21
    (app/__init__.py::_check_secret_key_or_fail, proyecto hermano) —
    cubre tanto el default de Config ("dev-secret-change-me") como el
    placeholder literal de .env.example ("change-me"), por si alguien
    copia ese archivo a .env sin editarlo.

    Args:
        app: Instancia de Flask ya con la config cargada.
        is_production: True si FLASK_ENV=production.

    Raises:
        RuntimeError: Si is_production es True y SECRET_KEY sigue vacío o
            en un valor de desarrollo conocido.
    """
    if is_production and app.config["SECRET_KEY"] in (
        None,
        "",
        "dev-secret-change-me",
        "change-me",
    ):
        raise RuntimeError(
            "SECRET_KEY no está configurado (o sigue en un valor de "
            "desarrollo) con FLASK_ENV=production. Define un SECRET_KEY "
            "real en el .env del servidor antes de arrancar."
        )


def create_app(config_class: type[Config] = Config) -> Flask:
    """Crea y configura la instancia de la aplicación Flask.

    Args:
        config_class: Clase de configuración a usar.

    Returns:
        Instancia de Flask lista para correr.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    _is_production = os.environ.get("FLASK_ENV", "").lower() == "production"
    _check_secret_key_or_fail(app, _is_production)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  (registra los modelos para Flask-Migrate)
    from app.routes.admin import admin_bp
    from app.routes.avisos import avisos_bp
    from app.routes.blog import blog_bp
    from app.routes.clicks import clicks_bp
    from app.routes.health import health_bp
    from app.routes.legal import legal_bp
    from app.routes.producto import producto_bp
    from app.routes.reportes import reportes_bp
    from app.routes.servicios import servicios_bp
    from app.routes.tienda import renderizar_tienda
    from app.routes.vendedor import login as vendedor_login
    from app.routes.vendedor import registro as vendedor_registro
    from app.routes.vendedor import vendedor_bp
    from app.services.google_auth_service import configurar_oauth_google
    from app.services.iconos_service import obtener_icono_categoria, obtener_icono_red
    from app.services.monedas_service import formatear_precio, obtener_moneda
    from app.services.site_info_service import obtener_info_sitio
    from app.services.subdominio_service import (
        resolver_redireccion_slug_antiguo,
        resolver_vendor_inactivo_por_host,
        resolver_vendor_por_host,
    )
    from app.services.vendor_service import obtener_vendor_por_slug_activo

    app.register_blueprint(health_bp)
    app.register_blueprint(servicios_bp)
    app.register_blueprint(producto_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(vendedor_bp)
    app.register_blueprint(clicks_bp)
    app.register_blueprint(legal_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(avisos_bp)

    # Alias público "/e-link" para el registro de vendedores: mismo
    # formulario que "/vendedor/registro" (misma función de vista), pero
    # con la URL de marca que se muestra en el navbar y en material de
    # difusión — coherente con los prefijos "/e-link-click", "/e-link-reporte"
    # y "/e-link-aviso" que ya usa el proyecto para esta misma función.
    # Como el <form> de registro.html no fija un `action`, el POST también
    # se envía a "/e-link", así que la URL se mantiene durante todo el flujo.
    app.add_url_rule(
        "/e-link",
        endpoint="vendedor.landing_e_link",
        view_func=vendedor_registro,
        methods=["GET", "POST"],
    )

    # URLs canónicas de registro/login de e-link, en "/e-link/..." en vez de
    # "/vendedor/..." (pedido de Jose, 2026-09-11): la URL pública que ve
    # cualquier visitante no debería depender del prefijo interno del panel
    # ("/vendedor"), que es un detalle de implementación. Registradas
    # directamente sobre `app` (no vía `@vendedor_bp.route`, que siempre
    # antepone "/vendedor") con el MISMO nombre de endpoint que usaban antes
    # (`vendedor.registro` / `vendedor.login`), así que cada `url_for(...)`
    # existente en el resto del código (redirecciones, enlaces "Inicia
    # sesión"/"Regístrate", el correo de verificación, etc.) sigue
    # funcionando sin tocar una sola plantilla más. La URL vieja
    # "/vendedor/registro"/"/vendedor/login" se conserva funcionando con un
    # 301 (ver `registro_url_antigua`/`login_url_antigua` en vendedor.py),
    # para no romper marcadores o enlaces ya compartidos.
    app.add_url_rule(
        "/e-link/registro",
        endpoint="vendedor.registro",
        view_func=vendedor_registro,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/e-link/login",
        endpoint="vendedor.login",
        view_func=vendedor_login,
        methods=["GET", "POST"],
    )

    configurar_oauth_google(app)
    app.jinja_env.globals["icono_categoria"] = obtener_icono_categoria
    app.jinja_env.globals["icono_red"] = obtener_icono_red
    app.jinja_env.globals["formatear_precio"] = formatear_precio
    app.jinja_env.globals["moneda_de"] = obtener_moneda

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

        Si el host no corresponde a ninguna tienda activa pero sí a un
        slug que un vendedor cambió recientemente (ver
        `vendor_service.cambiar_slug`), redirige automáticamente al
        subdominio nuevo en vez de dejar el enlace roto — la redirección
        dura `vendor_service.DIAS_REDIRECCION_SLUG_ANTERIOR` días. Si el
        slug existe pero la tienda está desactivada
        (`Vendor.activo=False`), se muestra un aviso claro en vez de
        dejar caer la petición al sitio principal como si el
        subdominio nunca hubiera existido.

        Returns:
            El HTML de la tienda si el host corresponde a un vendedor
            activo, una redirección al subdominio nuevo si el host es un
            slug anterior todavía vigente, un aviso 503 si la tienda
            existe pero está inactiva, o None para seguir el
            enrutamiento normal de Flask.
        """
        if (
            request.path.startswith("/static/")
            or request.path.startswith("/e-link-click/")
            or request.path.startswith("/e-link-reporte/")
            or request.path.startswith("/e-link-aviso/")
        ):
            return None

        slug_preview = request.args.get("preview_vendor")
        if slug_preview:
            vendor = obtener_vendor_por_slug_activo(slug_preview)
            if vendor is None:
                return None
            g.vendor = vendor
            return renderizar_tienda(vendor)

        vendor = resolver_vendor_por_host(request.host, app.config["SITE_DOMAIN"])
        if vendor is not None:
            g.vendor = vendor
            return renderizar_tienda(vendor)

        slug_nuevo = resolver_redireccion_slug_antiguo(request.host, app.config["SITE_DOMAIN"])
        if slug_nuevo is not None:
            puerto = f":{request.host.split(':', 1)[1]}" if ":" in request.host else ""
            ruta = request.full_path if request.query_string else request.path
            destino = f"{request.scheme}://{slug_nuevo}.{app.config['SITE_DOMAIN']}{puerto}{ruta}"
            return redirect(destino, code=302)

        vendor_inactivo = resolver_vendor_inactivo_por_host(request.host, app.config["SITE_DOMAIN"])
        if vendor_inactivo is not None:
            # URL absoluta al dominio principal a propósito: un `url_for`
            # normal generaría una ruta relativa que, al hacer clic,
            # seguiría resolviendo contra este mismo subdominio inactivo
            # (el before_request la volvería a interceptar acá mismo).
            puerto = f":{request.host.split(':', 1)[1]}" if ":" in request.host else ""
            url_login = f"{request.scheme}://{app.config['SITE_DOMAIN']}{puerto}{url_for('vendedor.login')}"
            return render_template("tienda/no_disponible.html", vendor=vendor_inactivo, url_login=url_login), 503

        return None

    return app
