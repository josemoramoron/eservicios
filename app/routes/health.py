"""Endpoints de salud/diagnóstico y página de inicio temporal."""
from flask import Blueprint, Response, jsonify

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
    """Página de inicio temporal mientras se construye el marketplace.

    Returns:
        HTML simple de confirmación.
    """
    return "<h1>eServicios — en construcción</h1><p>Esqueleto técnico activo.</p>"
