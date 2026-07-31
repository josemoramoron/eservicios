"""Lógica de negocio del catálogo (categorías y ofertas)."""
from __future__ import annotations

from app.models import Category, Offering


def listar_categorias() -> list[Category]:
    """Devuelve las categorías del catálogo ordenadas para mostrar en el sitio.

    Returns:
        Lista de categorías ordenadas por el campo `orden`.
    """
    return Category.query.order_by(Category.orden).all()


def obtener_categoria_por_slug(slug: str) -> Category | None:
    """Busca una categoría por su slug.

    Args:
        slug: Identificador url-friendly de la categoría.

    Returns:
        La categoría encontrada, o None si no existe.
    """
    return Category.query.filter_by(slug=slug).first()


def listar_ofertas_activas(category: Category) -> list[Offering]:
    """Devuelve las ofertas activas de una categoría, destacadas primero.

    Args:
        category: Categoría de la cual listar ofertas.

    Returns:
        Lista de `Offering` activos, con los destacados al inicio.
    """
    return (
        Offering.query.filter_by(category_id=category.id, activo=True)
        .order_by(Offering.destacado.desc(), Offering.nombre)
        .all()
    )
