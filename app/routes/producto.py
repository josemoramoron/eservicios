"""Rutas públicas de la ficha individual de producto (`/producto/<slug>`)."""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from app.services.catalogo_service import obtener_oferta_activa_por_slug

producto_bp = Blueprint("producto", __name__, url_prefix="/producto")


@producto_bp.route("/<slug>")
def detalle(slug: str) -> str:
    """Muestra la ficha individual de una oferta (producto, servicio, curso o consultoría).

    Args:
        slug: Identificador url-friendly de la oferta.

    Returns:
        HTML de la ficha de producto.
    """
    oferta = obtener_oferta_activa_por_slug(slug)
    if oferta is None:
        abort(404)
    return render_template("producto/detalle.html", oferta=oferta, categoria=oferta.category)
