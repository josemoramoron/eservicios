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

import re
from decimal import Decimal
from urllib.parse import quote

from sqlalchemy import func

from app.extensions import db
from app.models import ReservedSlug, Vendor, VendorLink, VendorProduct

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")

MAX_FOTOS_PRODUCTO = 5


class SlugInvalidoError(Exception):
    """El slug no cumple el formato permitido (letras minúsculas, números y guiones)."""


class SlugReservadoError(Exception):
    """El slug pedido está en la lista de palabras reservadas."""


class SlugDuplicadoError(Exception):
    """Ya existe otra tienda con ese slug."""


class EmailInvalidoError(Exception):
    """El correo no tiene un formato válido."""


class EmailDuplicadoError(Exception):
    """Ya existe una tienda registrada con ese correo."""


class PerfilInvalidoError(Exception):
    """Los datos de personalización de la tienda no son válidos."""


class PasswordActualIncorrectaError(Exception):
    """La contraseña actual ingresada no coincide con la guardada."""


class PasswordNuevaInvalidaError(Exception):
    """La contraseña nueva no cumple los requisitos mínimos."""


class LinkInvalidoError(Exception):
    """El título o la URL del enlace no son válidos."""


def validar_formato_slug(slug: str) -> str:
    """Normaliza y valida el formato de un slug de subdominio.

    Reglas: 3 a 63 caracteres (límite de un label DNS), solo minúsculas,
    números y guiones, sin guion al inicio ni al final.

    Args:
        slug: Slug tal como lo escribió el vendedor.

    Returns:
        El slug normalizado (minúsculas, sin espacios).

    Raises:
        SlugInvalidoError: Si no cumple el formato.
    """
    normalizado = slug.strip().lower()
    if len(normalizado) < 3 or len(normalizado) > 63 or not _SLUG_RE.match(normalizado):
        raise SlugInvalidoError(
            "El subdominio debe tener entre 3 y 63 caracteres: solo minúsculas, "
            "números y guiones, sin empezar ni terminar en guion."
        )
    return normalizado


def slug_disponible(slug: str) -> bool:
    """Indica si un slug ya normalizado está libre para usarse.

    Args:
        slug: Slug ya normalizado (ver `validar_formato_slug`).

    Returns:
        True si no está reservado ni en uso por otra tienda.
    """
    if ReservedSlug.query.filter_by(palabra=slug).first() is not None:
        return False
    return Vendor.query.filter_by(slug=slug).first() is None


def registrar_vendor(
    *,
    email: str,
    password: str,
    slug: str,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str | None = None,
) -> Vendor:
    """Valida y crea una tienda de vendedor nueva.

    Args:
        email: Correo del vendedor (login).
        password: Contraseña en texto plano a hashear.
        slug: Subdominio elegido, sin normalizar todavía.
        nombre_negocio: Nombre visible de la tienda.
        whatsapp_numero: Número de WhatsApp con código de país (solo dígitos).
        bio: Descripción corta opcional de la tienda.

    Returns:
        El `Vendor` recién creado (ya guardado en la base de datos).

    Raises:
        EmailInvalidoError: Si el correo no tiene formato válido.
        EmailDuplicadoError: Si ya existe una tienda con ese correo.
        SlugInvalidoError: Si el slug no cumple el formato.
        SlugReservadoError: Si el slug está reservado.
        SlugDuplicadoError: Si el slug ya está en uso.
    """
    email_normalizado = email.strip().lower()
    if "@" not in email_normalizado or "." not in email_normalizado.split("@")[-1]:
        raise EmailInvalidoError("El correo no tiene un formato válido.")
    if Vendor.query.filter_by(email=email_normalizado).first() is not None:
        raise EmailDuplicadoError("Ya existe una tienda registrada con ese correo.")

    slug_normalizado = validar_formato_slug(slug)
    if ReservedSlug.query.filter_by(palabra=slug_normalizado).first() is not None:
        raise SlugReservadoError("Ese subdominio no está disponible.")
    if Vendor.query.filter_by(slug=slug_normalizado).first() is not None:
        raise SlugDuplicadoError("Ese subdominio ya está en uso por otra tienda.")

    vendor = Vendor(
        email=email_normalizado,
        slug=slug_normalizado,
        nombre_negocio=nombre_negocio.strip(),
        whatsapp_numero=whatsapp_numero.strip(),
        bio=(bio or "").strip() or None,
    )
    vendor.set_password(password)
    db.session.add(vendor)
    db.session.commit()
    return vendor


def obtener_vendor_por_slug_activo(slug: str) -> Vendor | None:
    """Busca una tienda activa por su slug, para la página pública.

    Args:
        slug: Slug del subdominio.

    Returns:
        El `Vendor` si existe y está activo, o None.
    """
    return Vendor.query.filter_by(slug=slug.lower(), activo=True).first()


def obtener_vendor_por_email(email: str) -> Vendor | None:
    """Busca una tienda por el correo de su dueño.

    Args:
        email: Correo del vendedor.

    Returns:
        El `Vendor` encontrado, o None.
    """
    return Vendor.query.filter_by(email=email.strip().lower()).first()


def actualizar_perfil(
    vendor: Vendor,
    *,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str,
    logo_url: str | None,
    banner_url: str | None,
) -> None:
    """Actualiza los datos de personalización de la tienda del vendedor.

    El slug y el correo NO se editan aquí a propósito: el slug es el
    subdominio público (cambiarlo rompería enlaces ya compartidos) y el
    correo es la credencial de acceso — ambos quedan fuera de alcance
    de esta primera versión del perfil.

    Args:
        vendor: Tienda a actualizar.
        nombre_negocio: Nuevo nombre visible de la tienda.
        whatsapp_numero: Nuevo número de WhatsApp (con código de país).
        bio: Nueva descripción corta (puede quedar vacía).
        logo_url: URL del logo ya subido a R2, o None para quitarlo.
        banner_url: URL del banner ya subido a R2, o None para quitarlo.

    Raises:
        PerfilInvalidoError: Si el nombre o el WhatsApp quedan vacíos.
    """
    nombre_negocio = nombre_negocio.strip()
    whatsapp_numero = whatsapp_numero.strip()
    if not nombre_negocio:
        raise PerfilInvalidoError("El nombre de la tienda es obligatorio.")
    if not whatsapp_numero:
        raise PerfilInvalidoError("El número de WhatsApp es obligatorio.")

    vendor.nombre_negocio = nombre_negocio
    vendor.whatsapp_numero = whatsapp_numero
    vendor.bio = bio.strip() or None
    vendor.logo_url = logo_url
    vendor.banner_url = banner_url
    db.session.commit()


def cambiar_password(vendor: Vendor, *, password_actual: str, password_nueva: str) -> None:
    """Cambia la contraseña del vendedor, verificando la actual primero.

    Args:
        vendor: Tienda cuya contraseña se va a cambiar.
        password_actual: Contraseña actual, para confirmar la identidad.
        password_nueva: Contraseña nueva en texto plano.

    Raises:
        PasswordActualIncorrectaError: Si `password_actual` no coincide con la guardada.
        PasswordNuevaInvalidaError: Si `password_nueva` tiene menos de 8 caracteres.
    """
    if not vendor.check_password(password_actual):
        raise PasswordActualIncorrectaError("La contraseña actual no es correcta.")
    if len(password_nueva) < 8:
        raise PasswordNuevaInvalidaError("La nueva contraseña debe tener al menos 8 caracteres.")
    vendor.set_password(password_nueva)
    db.session.commit()


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


def crear_producto(
    vendor: Vendor, *, titulo: str, descripcion: str, precio: Decimal, fotos_urls: list[str] | None = None
) -> VendorProduct:
    """Crea un producto nuevo para una tienda. Sin moderación: queda activo de inmediato.

    Args:
        vendor: Tienda dueña del producto nuevo.
        titulo: Nombre del producto.
        descripcion: Descripción del producto.
        precio: Precio en USD.
        fotos_urls: URLs de las fotos del producto ya subidas a R2 (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada).

    Returns:
        El `VendorProduct` recién creado.
    """
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        precio=precio,
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
) -> None:
    """Actualiza los datos de un producto existente.

    Args:
        producto: Producto a actualizar.
        titulo: Nuevo nombre del producto.
        descripcion: Nueva descripción.
        precio: Nuevo precio en USD.
        fotos_urls: URLs finales de las fotos del producto (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada;
            lista vacía si se quitaron todas).
        activo: Si el producto debe seguir visible en la tienda pública.
    """
    producto.titulo = titulo.strip()
    producto.descripcion = descripcion.strip()
    producto.precio = precio
    _establecer_fotos_producto(producto, fotos_urls or [])
    producto.activo = activo
    db.session.commit()


def eliminar_producto(producto: VendorProduct) -> None:
    """Elimina un producto de forma permanente.

    Args:
        producto: Producto a eliminar.
    """
    db.session.delete(producto)
    db.session.commit()


def construir_whatsapp_href(numero: str, mensaje: str) -> str:
    """Arma un link `wa.me` con mensaje prellenado.

    Toda la lógica de codificación de URL vive aquí a propósito — los
    templates de eServicios no llevan lógica Python, solo la muestran.

    Args:
        numero: Número de WhatsApp del vendedor (con código de país).
        mensaje: Texto a prellenar en el chat.

    Returns:
        URL lista para usar en un `<a href>`.
    """
    return f"https://wa.me/{numero}?text={quote(mensaje)}"


def href_whatsapp_tienda(vendor: Vendor) -> str:
    """Link de WhatsApp general de la tienda (botón del encabezado).

    Args:
        vendor: Tienda para la que se arma el link.

    Returns:
        URL `wa.me` con un mensaje genérico.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero, f"Hola, tengo una consulta sobre {vendor.nombre_negocio}."
    )


def href_whatsapp_producto(vendor: Vendor, producto: VendorProduct) -> str:
    """Link de WhatsApp de un producto puntual (botón del detalle).

    Args:
        vendor: Tienda dueña del producto.
        producto: Producto sobre el que se pregunta.

    Returns:
        URL `wa.me` con el nombre del producto en el mensaje.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero,
        f'Hola, quiero info sobre "{producto.titulo}" en {vendor.nombre_negocio}.',
    )


# --- Enlaces personalizados (estilo Linktree) ---


def _validar_url_link(url: str) -> str:
    """Valida y normaliza la URL de un enlace personalizado.

    Solo exige que empiece con `http://` o `https://` — no se valida
    contra una lista de dominios permitidos a propósito, para que el
    vendedor pueda enlazar cualquier red o sitio (Instagram, TikTok,
    su propio sitio web, etc.), igual que en Linktree/Beacons.

    Args:
        url: URL tal como la escribió el vendedor.

    Returns:
        La URL con espacios recortados.

    Raises:
        LinkInvalidoError: Si no empieza con `http://` o `https://`.
    """
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise LinkInvalidoError("El enlace debe empezar con http:// o https://.")
    return url


def listar_links_de_vendor(vendor: Vendor) -> list[VendorLink]:
    """Devuelve todos los enlaces de una tienda (activos e inactivos), para el panel.

    Args:
        vendor: Tienda dueña de los enlaces.

    Returns:
        Lista de `VendorLink` ordenada por el campo `orden`.
    """
    return VendorLink.query.filter_by(vendor_id=vendor.id).order_by(VendorLink.orden).all()


def listar_links_activos(vendor: Vendor) -> list[VendorLink]:
    """Devuelve los enlaces activos de una tienda, para la página pública.

    Args:
        vendor: Tienda dueña de los enlaces.

    Returns:
        Lista de `VendorLink` activos, ordenada por el campo `orden`.
    """
    return (
        VendorLink.query.filter_by(vendor_id=vendor.id, activo=True)
        .order_by(VendorLink.orden)
        .all()
    )


def obtener_link_de_vendor(vendor: Vendor, link_id: int) -> VendorLink | None:
    """Busca un enlace por id, verificando que pertenezca a la tienda dada.

    Evita que un vendedor edite o borre enlaces de otra tienda
    adivinando ids en la URL.

    Args:
        vendor: Tienda que debería ser dueña del enlace.
        link_id: Id del enlace buscado.

    Returns:
        El `VendorLink` si existe y pertenece a `vendor`, o None.
    """
    return VendorLink.query.filter_by(id=link_id, vendor_id=vendor.id).first()


def crear_link(vendor: Vendor, *, titulo: str, url: str) -> VendorLink:
    """Crea un enlace personalizado nuevo para una tienda.

    Se agrega al final del orden actual (no hay límite de cantidad —
    el plan gratis no restringe cuántos enlaces puede tener una tienda).

    Args:
        vendor: Tienda dueña del enlace nuevo.
        titulo: Texto visible del botón (ej. "Mi Instagram").
        url: Destino del enlace.

    Returns:
        El `VendorLink` recién creado.

    Raises:
        LinkInvalidoError: Si el título queda vacío o la URL no es válida.
    """
    titulo = titulo.strip()
    if not titulo:
        raise LinkInvalidoError("El título del enlace es obligatorio.")
    url_valida = _validar_url_link(url)

    orden_maximo = (
        db.session.query(func.max(VendorLink.orden)).filter(VendorLink.vendor_id == vendor.id).scalar()
    )
    siguiente_orden = (orden_maximo + 1) if orden_maximo is not None else 0

    link = VendorLink(vendor_id=vendor.id, titulo=titulo, url=url_valida, orden=siguiente_orden)
    db.session.add(link)
    db.session.commit()
    return link


def actualizar_link(link: VendorLink, *, titulo: str, url: str, activo: bool) -> None:
    """Actualiza los datos de un enlace existente.

    Args:
        link: Enlace a actualizar.
        titulo: Nuevo texto visible del botón.
        url: Nuevo destino del enlace.
        activo: Si el enlace debe seguir visible en la tienda pública.

    Raises:
        LinkInvalidoError: Si el título queda vacío o la URL no es válida.
    """
    titulo = titulo.strip()
    if not titulo:
        raise LinkInvalidoError("El título del enlace es obligatorio.")
    link.titulo = titulo
    link.url = _validar_url_link(url)
    link.activo = activo
    db.session.commit()


def eliminar_link(link: VendorLink) -> None:
    """Elimina un enlace de forma permanente.

    Args:
        link: Enlace a eliminar.
    """
    db.session.delete(link)
    db.session.commit()


def mover_link(vendor: Vendor, link: VendorLink, *, direccion: str) -> None:
    """Sube o baja un enlace un puesto, intercambiando `orden` con su vecino.

    Se busca el vecino inmediato en la lista completa (activos e
    inactivos) de la tienda, ordenada por `orden`, y se intercambian los
    valores — así no hace falta renumerar toda la lista ni usar
    drag-and-drop en el front.

    Args:
        vendor: Tienda dueña del enlace (para acotar la búsqueda del vecino).
        link: Enlace a mover.
        direccion: `"arriba"` o `"abajo"`.
    """
    links = listar_links_de_vendor(vendor)
    posicion = next((i for i, l in enumerate(links) if l.id == link.id), None)
    if posicion is None:
        return

    if direccion == "arriba" and posicion > 0:
        vecino = links[posicion - 1]
    elif direccion == "abajo" and posicion < len(links) - 1:
        vecino = links[posicion + 1]
    else:
        return

    link.orden, vecino.orden = vecino.orden, link.orden
    db.session.commit()
