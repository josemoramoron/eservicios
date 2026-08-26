"""Páginas legales del sitio (`/terminos`)."""
from __future__ import annotations

from flask import Blueprint, render_template

legal_bp = Blueprint("legal", __name__)


@legal_bp.route("/terminos")
def terminos():
    """Página de términos y condiciones / política de uso.

    Cubre tanto el sitio principal de eServicios como las tiendas de
    vendedor (e-link) que corren sobre subdominios propios.

    Returns:
        HTML de la página de términos y condiciones.
    """
    return render_template("legal/terminos.html")
