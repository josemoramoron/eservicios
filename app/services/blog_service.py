"""Lógica de negocio del blog de noticias.

Incluye tanto las consultas del sitio público (publicados/por slug) como
el CRUD que usa el panel de administración (`app/routes/admin.py`), y la
conversión de Markdown a HTML para renderizar los artículos.
"""
from __future__ import annotations

from datetime import datetime, timezone

import markdown

from app.extensions import db
from app.models import BlogPost, EstadoBlogPost


class SlugDuplicadoBlogError(Exception):
    """Ya existe otro artículo con ese slug."""


def listar_posts_publicados() -> list[BlogPost]:
    """Devuelve los artículos publicados para el sitio público, más recientes primero.

    Returns:
        Lista de `BlogPost` con estado publicado, ordenados por fecha de
        publicación descendente.
    """
    return (
        BlogPost.query.filter_by(estado=EstadoBlogPost.PUBLICADO)
        .order_by(BlogPost.publicado_en.desc())
        .all()
    )


def obtener_post_publicado_por_slug(slug: str) -> BlogPost | None:
    """Busca un artículo publicado por su slug (para la página pública).

    Args:
        slug: Identificador url-friendly del artículo.

    Returns:
        El artículo encontrado, o None si no existe o no está publicado.
    """
    return BlogPost.query.filter_by(slug=slug, estado=EstadoBlogPost.PUBLICADO).first()


def listar_todos_los_posts() -> list[BlogPost]:
    """Devuelve todos los artículos (borradores y publicados) para el panel de admin.

    Returns:
        Lista de `BlogPost`, más recientes primero.
    """
    return BlogPost.query.order_by(BlogPost.creado_en.desc()).all()


def obtener_post_por_id(post_id: int) -> BlogPost | None:
    """Busca un artículo por su id (para el panel de administración).

    Args:
        post_id: Id numérico del artículo.

    Returns:
        El artículo encontrado, o None si no existe.
    """
    return db.session.get(BlogPost, post_id)


def render_markdown(texto: str) -> str:
    """Convierte el contenido en Markdown de un artículo a HTML.

    Args:
        texto: Contenido en Markdown tal como se guardó desde el panel.

    Returns:
        HTML listo para insertar en la plantilla con `| safe`.
    """
    return markdown.markdown(texto, extensions=["fenced_code", "tables", "nl2br"])


def crear_post(datos: dict) -> BlogPost:
    """Crea un artículo nuevo desde el panel de administración.

    Args:
        datos: Diccionario con titulo, slug, resumen, contenido_markdown,
            imagen_url y estado ("borrador" o "publicado").

    Returns:
        El artículo creado.

    Raises:
        SlugDuplicadoBlogError: Si ya existe un artículo con ese slug.
    """
    if BlogPost.query.filter_by(slug=datos["slug"]).first() is not None:
        raise SlugDuplicadoBlogError(f"Ya existe un artículo con el slug \"{datos['slug']}\".")
    estado = EstadoBlogPost(datos["estado"])
    post = BlogPost(
        titulo=datos["titulo"],
        slug=datos["slug"],
        resumen=datos.get("resumen") or None,
        contenido_markdown=datos["contenido_markdown"],
        imagen_url=datos.get("imagen_url") or None,
        estado=estado,
        publicado_en=datetime.now(timezone.utc) if estado == EstadoBlogPost.PUBLICADO else None,
    )
    db.session.add(post)
    db.session.commit()
    return post


def actualizar_post(post: BlogPost, datos: dict) -> BlogPost:
    """Actualiza un artículo existente con los datos del formulario de admin.

    Si el artículo pasa a "publicado" por primera vez, fija `publicado_en`
    a la fecha actual; si ya tenía fecha de publicación, la conserva
    (para no perder el orden cronológico al editar un artículo publicado).

    Args:
        post: Artículo a actualizar.
        datos: Diccionario con los campos nuevos (misma forma que `crear_post`).

    Returns:
        El artículo actualizado.

    Raises:
        SlugDuplicadoBlogError: Si otro artículo ya usa ese slug.
    """
    conflicto = BlogPost.query.filter(BlogPost.slug == datos["slug"], BlogPost.id != post.id).first()
    if conflicto is not None:
        raise SlugDuplicadoBlogError(f"Ya existe otro artículo con el slug \"{datos['slug']}\".")
    nuevo_estado = EstadoBlogPost(datos["estado"])
    post.titulo = datos["titulo"]
    post.slug = datos["slug"]
    post.resumen = datos.get("resumen") or None
    post.contenido_markdown = datos["contenido_markdown"]
    post.imagen_url = datos.get("imagen_url") or None
    if nuevo_estado == EstadoBlogPost.PUBLICADO and post.publicado_en is None:
        post.publicado_en = datetime.now(timezone.utc)
    post.estado = nuevo_estado
    db.session.commit()
    return post


def eliminar_post(post: BlogPost) -> None:
    """Elimina un artículo del blog.

    Args:
        post: Artículo a eliminar.
    """
    db.session.delete(post)
    db.session.commit()
