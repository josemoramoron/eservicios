"""Rutas públicas del catálogo de servicios (una página por categoría)."""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from app.services.catalogo_service import (
    listar_categorias,
    listar_ofertas_activas,
    obtener_categoria_por_slug,
)

servicios_bp = Blueprint("servicios", __name__, url_prefix="/servicios")


@servicios_bp.route("/")
def index() -> str:
    """Lista todas las categorías del catálogo.

    Returns:
        HTML con la grilla de categorías.
    """
    categorias = listar_categorias()
    return render_template("servicios/index.html", categorias=categorias)


@servicios_bp.route("/<slug>")
def categoria(slug: str) -> str:
    """Muestra una categoría del catálogo y sus ofertas activas.

    Args:
        slug: Identificador url-friendly de la categoría.

    Returns:
        HTML de la página de la categoría.
    """
    cat = obtener_categoria_por_slug(slug)
    if cat is None:
        abort(404)
    ofertas = listar_ofertas_activas(cat)
    return render_template("servicios/categoria.html", categoria=cat, ofertas=ofertas)
