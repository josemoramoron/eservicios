"""Lógica de negocio del catálogo (categorías y ofertas).

Incluye tanto las consultas del sitio público (activas/por slug) como el
CRUD que usa el panel de administración (`app/routes/admin.py`).
"""
from __future__ import annotations

from app.extensions import db
from app.models import Category, Offering, TipoOffering


class SlugDuplicadoError(Exception):
    """Ya existe otra categoría/oferta con ese slug."""


class CategoriaConOfertasError(Exception):
    """Se intentó borrar una categoría que todavía tiene ofertas asociadas."""


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


def obtener_categoria_por_id(categoria_id: int) -> Category | None:
    """Busca una categoría por su id (para el panel de administración).

    Args:
        categoria_id: Id numérico de la categoría.

    Returns:
        La categoría encontrada, o None si no existe.
    """
    return db.session.get(Category, categoria_id)


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


def listar_todas_las_ofertas(category_id: int | None = None) -> list[Offering]:
    """Devuelve todas las ofertas (activas e inactivas) para el panel de admin.

    Args:
        category_id: Si se pasa, filtra solo las ofertas de esa categoría.

    Returns:
        Lista de `Offering`, ordenadas por categoría y nombre.
    """
    consulta = Offering.query
    if category_id is not None:
        consulta = consulta.filter_by(category_id=category_id)
    return consulta.order_by(Offering.category_id, Offering.nombre).all()


def obtener_oferta_por_id(oferta_id: int) -> Offering | None:
    """Busca una oferta por su id (para el panel de administración).

    Args:
        oferta_id: Id numérico de la oferta.

    Returns:
        La oferta encontrada, o None si no existe.
    """
    return db.session.get(Offering, oferta_id)


def crear_categoria(datos: dict) -> Category:
    """Crea una categoría nueva desde el panel de administración.

    Args:
        datos: Diccionario con nombre, slug, descripcion, orden e imagen_url.

    Returns:
        La categoría creada.

    Raises:
        SlugDuplicadoError: Si ya existe una categoría con ese slug.
    """
    if Category.query.filter_by(slug=datos["slug"]).first() is not None:
        raise SlugDuplicadoError(f"Ya existe una categoría con el slug \"{datos['slug']}\".")
    categoria = Category(
        nombre=datos["nombre"],
        slug=datos["slug"],
        descripcion=datos.get("descripcion") or None,
        orden=datos.get("orden", 0),
        imagen_url=datos.get("imagen_url") or None,
    )
    db.session.add(categoria)
    db.session.commit()
    return categoria


def actualizar_categoria(categoria: Category, datos: dict) -> Category:
    """Actualiza una categoría existente con los datos del formulario de admin.

    Args:
        categoria: Categoría a actualizar.
        datos: Diccionario con nombre, slug, descripcion, orden e imagen_url.

    Returns:
        La categoría actualizada.

    Raises:
        SlugDuplicadoError: Si otra categoría ya usa ese slug.
    """
    conflicto = Category.query.filter(
        Category.slug == datos["slug"], Category.id != categoria.id
    ).first()
    if conflicto is not None:
        raise SlugDuplicadoError(f"Ya existe otra categoría con el slug \"{datos['slug']}\".")
    categoria.nombre = datos["nombre"]
    categoria.slug = datos["slug"]
    categoria.descripcion = datos.get("descripcion") or None
    categoria.orden = datos.get("orden", 0)
    categoria.imagen_url = datos.get("imagen_url") or None
    db.session.commit()
    return categoria


def eliminar_categoria(categoria: Category) -> None:
    """Elimina una categoría, si no tiene ofertas asociadas.

    Args:
        categoria: Categoría a eliminar.

    Raises:
        CategoriaConOfertasError: Si la categoría todavía tiene ofertas.
    """
    if categoria.offerings:
        raise CategoriaConOfertasError(
            f"\"{categoria.nombre}\" tiene {len(categoria.offerings)} oferta(s) asociada(s). "
            "Muévelas a otra categoría o bórralas primero."
        )
    db.session.delete(categoria)
    db.session.commit()


def crear_oferta(datos: dict) -> Offering:
    """Crea una oferta nueva desde el panel de administración.

    Args:
        datos: Diccionario con los campos de `Offering` (ver `_leer_datos_oferta`
            en `app/routes/admin.py` para la forma exacta).

    Returns:
        La oferta creada.

    Raises:
        SlugDuplicadoError: Si ya existe una oferta con ese slug.
    """
    if Offering.query.filter_by(slug=datos["slug"]).first() is not None:
        raise SlugDuplicadoError(f"Ya existe una oferta con el slug \"{datos['slug']}\".")
    oferta = Offering(
        category_id=datos["category_id"],
        nombre=datos["nombre"],
        slug=datos["slug"],
        tipo=TipoOffering(datos["tipo"]),
        descripcion=datos["descripcion"],
        imagen_url=datos.get("imagen_url") or None,
        precio=datos.get("precio") or None,
        vendible=datos.get("vendible", False),
        stock=datos.get("stock") or None,
        destacado=datos.get("destacado", False),
        activo=datos.get("activo", True),
    )
    db.session.add(oferta)
    db.session.commit()
    return oferta


def actualizar_oferta(oferta: Offering, datos: dict) -> Offering:
    """Actualiza una oferta existente con los datos del formulario de admin.

    Args:
        oferta: Oferta a actualizar.
        datos: Diccionario con los campos nuevos.

    Returns:
        La oferta actualizada.

    Raises:
        SlugDuplicadoError: Si otra oferta ya usa ese slug.
    """
    conflicto = Offering.query.filter(
        Offering.slug == datos["slug"], Offering.id != oferta.id
    ).first()
    if conflicto is not None:
        raise SlugDuplicadoError(f"Ya existe otra oferta con el slug \"{datos['slug']}\".")
    oferta.category_id = datos["category_id"]
    oferta.nombre = datos["nombre"]
    oferta.slug = datos["slug"]
    oferta.tipo = TipoOffering(datos["tipo"])
    oferta.descripcion = datos["descripcion"]
    oferta.imagen_url = datos.get("imagen_url") or None
    oferta.precio = datos.get("precio") or None
    oferta.vendible = datos.get("vendible", False)
    oferta.stock = datos.get("stock") or None
    oferta.destacado = datos.get("destacado", False)
    oferta.activo = datos.get("activo", True)
    db.session.commit()
    return oferta


def eliminar_oferta(oferta: Offering) -> None:
    """Elimina una oferta del catálogo.

    Args:
        oferta: Oferta a eliminar.
    """
    db.session.delete(oferta)
    db.session.commit()
