"""Lógica de negocio de las tiendas de vendedor (registro, slug, productos, perfil).

Incluye la validación y disponibilidad del subdominio elegido por el
vendedor, el CRUD que usa el panel `/vendedor`, la actualización del
perfil (personalización + seguridad) y los helpers para armar los
links `wa.me` (WhatsApp) que se muestran en la tienda pública. La
subida de imágenes a Cloudflare R2 vive en `r2_service.py` — este
módulo solo recibe URLs ya resueltas y las guarda en el modelo. Ver
`claude/spec-tiendas-vendedor.md` en el proyecto para el diseño completo.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models import (
    Vendor,
    VendorCategoria,
    VendorProduct,
)
from app.services.badges_producto_service import BADGES_PRODUCTO
from app.services.estados_stock_service import ESTADOS_STOCK

MAX_FOTOS_PRODUCTO = 5


def listar_productos_de_vendor(vendor: Vendor) -> list[VendorProduct]:
    """Devuelve todos los productos de una tienda (activos e inactivos), para el panel.

    Args:
        vendor: Tienda dueña de los productos.

    Returns:
        Lista de `VendorProduct`, más recientes primero.
    """
    return VendorProduct.query.filter_by(vendor_id=vendor.id).order_by(VendorProduct.id.desc()).all()


def listar_productos_activos(vendor: Vendor) -> list[VendorProduct]:
    """Devuelve los productos activos de una tienda, para la página pública.

    Args:
        vendor: Tienda dueña de los productos.

    Returns:
        Lista de `VendorProduct` activos, más recientes primero.
    """
    return (
        VendorProduct.query.filter_by(vendor_id=vendor.id, activo=True)
        .order_by(VendorProduct.id.desc())
        .all()
    )


def obtener_producto_de_vendor(vendor: Vendor, producto_id: int) -> VendorProduct | None:
    """Busca un producto por id, verificando que pertenezca a la tienda dada.

    Evita que un vendedor edite o borre productos de otra tienda
    adivinando ids en la URL.

    Args:
        vendor: Tienda que debería ser dueña del producto.
        producto_id: Id del producto buscado.

    Returns:
        El `VendorProduct` si existe y pertenece a `vendor`, o None.
    """
    return VendorProduct.query.filter_by(id=producto_id, vendor_id=vendor.id).first()


def _establecer_fotos_producto(producto: VendorProduct, urls: list[str]) -> None:
    """Reemplaza la galería de fotos de un producto y sincroniza la portada.

    `VendorProduct.foto_url` (la portada, usada en la tarjeta de la
    grilla y como imagen inicial del modal) se mantiene siempre igual a
    la primera foto de `urls` — así no hay dos fuentes de verdad que se
    puedan desincronizar. Igual que `catalogo_service._establecer_fotos_oferta`,
    se reemplaza la colección completa de golpe (`cascade="all, delete-orphan"`
    en `VendorProduct.fotos`) en vez de diffear fila por fila.

    Args:
        producto: Producto dueño de la galería (nuevo o existente).
        urls: URLs ya resueltas (subidas a R2), en el orden final, sin
            huecos ni duplicados de posición vacía. Máximo `MAX_FOTOS_PRODUCTO`.
    """
    from app.models import VendorProductFoto  # import local para evitar ciclo con VendorProduct

    urls = urls[:MAX_FOTOS_PRODUCTO]
    producto.fotos = [VendorProductFoto(url=url, orden=indice) for indice, url in enumerate(urls)]
    producto.foto_url = urls[0] if urls else None


def _categoria_id_valida(vendor: Vendor, categoria_id: int | None) -> int | None:
    """Verifica que un `categoria_id` pertenezca a la tienda dada antes de guardarlo.

    Mismo trato de "silenciosamente inválido" que `badge`/`estado_stock`
    en `crear_producto`/`actualizar_producto`: evita guardar un id de
    categoría de otra tienda (formulario manipulado) sin tener que
    lanzar un error — el producto simplemente queda sin categoría.

    Args:
        vendor: Tienda dueña del producto.
        categoria_id: Id propuesto, o None.

    Returns:
        `categoria_id` si corresponde a una categoría de `vendor`, o None.
    """
    if categoria_id is None:
        return None
    if VendorCategoria.query.filter_by(id=categoria_id, vendor_id=vendor.id).first() is None:
        return None
    return categoria_id


def crear_producto(
    vendor: Vendor,
    *,
    titulo: str,
    descripcion: str,
    precio: Decimal,
    fotos_urls: list[str] | None = None,
    badge: str | None = None,
    estado_stock: str | None = None,
    categoria_id: int | None = None,
) -> VendorProduct:
    """Crea un producto nuevo para una tienda. Sin moderación: queda activo de inmediato.

    Args:
        vendor: Tienda dueña del producto nuevo.
        titulo: Nombre del producto.
        descripcion: Descripción del producto.
        precio: Precio en la moneda de la tienda (`vendor.moneda`) — sin
            conversión, se muestra tal cual (ver `monedas_service`).
        fotos_urls: URLs de las fotos del producto ya subidas a R2 (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada).
        badge: Clave de un badge de `badges_producto_service` (ej.
            "oferta"), o vacío/None para no mostrar ninguno. Un valor que
            no exista en `BADGES_PRODUCTO` se ignora en silencio (queda
            en None) — mismo trato que `plantilla` en `Vendor`. No
            valida el plan Plus aquí — esa función se gatea
            en tiempo de render (ver `resolver_badge_producto`).
        estado_stock: Clave de un estado de `estados_stock_service` (ej.
            "agotado"), o vacío/None para "Normal". Mismo trato que
            `badge`: una clave inválida se ignora en silencio, y el plan
            Plus se gatea en tiempo de render (ver
            `resolver_estado_stock_producto`).
        categoria_id: Id de una `VendorCategoria` de esta misma tienda, o
            None para dejar el producto sin categorizar. Un id que no
            pertenezca a `vendor` se ignora en silencio (queda en None)
            — mismo trato que `badge`/`estado_stock`, para no depender
            de que el formulario haya sido manipulado con un id ajeno.

    Returns:
        El `VendorProduct` recién creado.
    """
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        precio=precio,
        badge=badge if badge in BADGES_PRODUCTO else None,
        estado_stock=estado_stock if estado_stock in ESTADOS_STOCK else None,
        categoria_id=_categoria_id_valida(vendor, categoria_id),
    )
    _establecer_fotos_producto(producto, fotos_urls or [])
    db.session.add(producto)
    db.session.commit()
    return producto


def actualizar_producto(
    producto: VendorProduct,
    *,
    titulo: str,
    descripcion: str,
    precio: Decimal,
    fotos_urls: list[str] | None,
    activo: bool,
    badge: str | None = None,
    estado_stock: str | None = None,
    categoria_id: int | None = None,
) -> None:
    """Actualiza los datos de un producto existente.

    Args:
        producto: Producto a actualizar.
        titulo: Nuevo nombre del producto.
        descripcion: Nueva descripción.
        precio: Nuevo precio en la moneda de la tienda (`vendor.moneda`).
        fotos_urls: URLs finales de las fotos del producto (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada;
            lista vacía si se quitaron todas).
        activo: Si el producto debe seguir visible en la tienda pública.
        badge: Clave de un badge de `badges_producto_service`, o
            vacío/None para quitarlo. Mismo trato que en `crear_producto`.
        estado_stock: Clave de un estado de `estados_stock_service`, o
            vacío/None para volver a "Normal". Mismo trato que en `crear_producto`.
        categoria_id: Id de una `VendorCategoria` de la misma tienda que
            el producto, o None para quitarle la categoría. Mismo trato
            que en `crear_producto`.
    """
    producto.titulo = titulo.strip()
    producto.descripcion = descripcion.strip()
    producto.precio = precio
    _establecer_fotos_producto(producto, fotos_urls or [])
    producto.activo = activo
    producto.badge = badge if badge in BADGES_PRODUCTO else None
    producto.estado_stock = estado_stock if estado_stock in ESTADOS_STOCK else None
    producto.categoria_id = _categoria_id_valida(producto.vendor, categoria_id)
    db.session.commit()


def eliminar_producto(producto: VendorProduct) -> None:
    """Elimina un producto de forma permanente.

    Args:
        producto: Producto a eliminar.
    """
    db.session.delete(producto)
    db.session.commit()

