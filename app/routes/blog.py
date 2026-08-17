"""Rutas públicas del blog de noticias."""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from app.services.blog_service import (
    listar_posts_publicados,
    obtener_post_publicado_por_slug,
    render_markdown,
)

blog_bp = Blueprint("blog", __name__, url_prefix="/blog")


@blog_bp.route("/")
def index() -> str:
    """Lista los artículos publicados, más recientes primero.

    Returns:
        HTML con el listado de artículos.
    """
    posts = listar_posts_publicados()
    return render_template("blog/lista.html", posts=posts)


@blog_bp.route("/<slug>")
def detalle(slug: str) -> str:
    """Muestra un artículo publicado.

    Args:
        slug: Identificador url-friendly del artículo.

    Returns:
        HTML del artículo.
    """
    post = obtener_post_publicado_por_slug(slug)
    if post is None:
        abort(404)
    contenido_html = render_markdown(post.contenido_markdown)
    return render_template("blog/detalle.html", post=post, contenido_html=contenido_html)
