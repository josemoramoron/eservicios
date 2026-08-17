"""Endpoints de salud/diagnóstico y página de inicio."""
from flask import Blueprint, Response, jsonify, render_template

from app.services.catalogo_service import listar_destacados_con_imagen

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health() -> Response:
    """Reporta que la aplicación está corriendo.

    Returns:
        Respuesta JSON con estado "ok".
    """
    return jsonify(status="ok", service="eservicios")


@health_bp.route("/")
def index() -> str:
    """Página de inicio del sitio de productos y servicios.

    Returns:
        HTML de la landing principal, con el slider de destacados
        (ofertas marcadas como destacado y con foto) si hay alguna.
    """
    return render_template("home.html", destacados=listar_destacados_con_imagen())
