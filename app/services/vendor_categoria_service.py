"""CRUD de las categorías propias del vendedor (`VendorCategoria`).

Sacado de `vendor_service.py` (2026-09-24, primer bloque del split de
los god-files — ver `.clinerules` y
`claude/auditoria-deuda-tecnica-2026-09.md`) sin cambiar comportamiento
alguno, solo ubicación. Distinto de `catalogo_service.py`
(`crear_categoria`/`actualizar_categoria`/`eliminar_categoria` sobre
`Category`, el catálogo maestro curado por eServicios) — mismos
nombres de función por coincidencia, sin ninguna relación entre los
dos módulos.

Cada `Vendor` define sus propias categorías, libres, para organizar y
filtrar los productos de SU tienda pública. Ver
`claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from sqlalchemy import func

from app.extensions import db
from app.models import Vendor, VendorCategoria, VendorProduct


class CategoriaInvalidaError(Exception):
    """El nombre de la categoría no es válido (vacío, o duplicado dentro de la misma tienda)."""


def listar_categorias_de_vendor(vendor: Vendor) -> list[VendorCategoria]:
    """Devuelve todas las categorías de una tienda, para el panel y el filtro público.

    Args:
        vendor: Tienda dueña de las categorías.

    Returns:
        Lista de `VendorCategoria` ordenada por el campo `orden`.
    """
    return VendorCategoria.query.filter_by(vendor_id=vendor.id).order_by(VendorCategoria.orden).all()


def obtener_categoria_de_vendor(vendor: Vendor, categoria_id: int) -> VendorCategoria | None:
    """Busca una categoría por id, verificando que pertenezca a la tienda dada.

    Evita que un vendedor edite o borre categorías de otra tienda
    adivinando ids en la URL — mismo criterio que `obtener_link_de_vendor`.

    Args:
        vendor: Tienda que debería ser dueña de la categoría.
        categoria_id: Id de la categoría buscada.

    Returns:
        La `VendorCategoria` si existe y pertenece a `vendor`, o None.
    """
    return VendorCategoria.query.filter_by(id=categoria_id, vendor_id=vendor.id).first()


def crear_categoria(vendor: Vendor, *, nombre: str) -> VendorCategoria:
    """Crea una categoría nueva para una tienda.

    Se agrega al final del orden actual, mismo criterio que `crear_link`.

    Args:
        vendor: Tienda dueña de la categoría nueva.
        nombre: Nombre visible de la categoría (ej. "Electrodomésticos").

    Returns:
        La `VendorCategoria` recién creada.

    Raises:
        CategoriaInvalidaError: Si el nombre queda vacío, o ya existe
            otra categoría con el mismo nombre (sin distinguir mayúsculas)
            en esta misma tienda.
    """
    nombre = nombre.strip()
    if not nombre:
        raise CategoriaInvalidaError("El nombre de la categoría es obligatorio.")
    ya_existe = VendorCategoria.query.filter(
        VendorCategoria.vendor_id == vendor.id, func.lower(VendorCategoria.nombre) == nombre.lower()
    ).first()
    if ya_existe is not None:
        raise CategoriaInvalidaError("Ya existe una categoría con ese nombre.")

    orden_maximo = (
        db.session.query(func.max(VendorCategoria.orden))
        .filter(VendorCategoria.vendor_id == vendor.id)
        .scalar()
    )
    siguiente_orden = (orden_maximo + 1) if orden_maximo is not None else 0

    categoria = VendorCategoria(vendor_id=vendor.id, nombre=nombre, orden=siguiente_orden)
    db.session.add(categoria)
    db.session.commit()
    return categoria


def actualizar_categoria(categoria: VendorCategoria, *, nombre: str) -> None:
    """Renombra una categoría existente.

    Args:
        categoria: Categoría a actualizar.
        nombre: Nuevo nombre visible.

    Raises:
        CategoriaInvalidaError: Si el nombre queda vacío, o ya existe
            otra categoría con el mismo nombre (sin distinguir mayúsculas)
            en la misma tienda.
    """
    nombre = nombre.strip()
    if not nombre:
        raise CategoriaInvalidaError("El nombre de la categoría es obligatorio.")
    ya_existe = VendorCategoria.query.filter(
        VendorCategoria.vendor_id == categoria.vendor_id,
        VendorCategoria.id != categoria.id,
        func.lower(VendorCategoria.nombre) == nombre.lower(),
    ).first()
    if ya_existe is not None:
        raise CategoriaInvalidaError("Ya existe una categoría con ese nombre.")
    categoria.nombre = nombre
    db.session.commit()


def eliminar_categoria(categoria: VendorCategoria) -> None:
    """Elimina una categoría de forma permanente.

    Antes de borrar la fila, pone `categoria_id` en None a mano en cada
    producto que la tuviera asignada — limpieza manual explícita en vez
    de depender de un `ON DELETE` a nivel de base de datos, mismo
    criterio que `vendor_admin_service.eliminar_vendor_permanente` usa
    para `VendorEvento`/`VendorReporte`. Los productos en sí NO se
    borran, solo quedan sin categoría.

    Args:
        categoria: Categoría a eliminar.
    """
    VendorProduct.query.filter_by(categoria_id=categoria.id).update({"categoria_id": None})
    db.session.delete(categoria)
    db.session.commit()
