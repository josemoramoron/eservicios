"""Endpoints de salud/diagnóstico y página de inicio."""
from flask import Blueprint, Response, jsonify, render_template

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
        HTML de la landing principal.
    """
    return render_template("home.html")
