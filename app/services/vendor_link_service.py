"""CRUD de los enlaces personalizados del vendedor (`VendorLink`, estilo Linktree).

Sacado de `vendor_service.py` (2026-09-25, segundo bloque del split de
los god-files — ver `.clinerules` y
`claude/auditoria-deuda-tecnica-2026-09.md`) sin cambiar comportamiento
alguno, solo ubicación. Incluye el selector rápido de red social
(2026-09-15/16, pedido de Jose) para armar la URL a partir de solo el
usuario, en vez de exigir siempre la URL completa.
"""
from __future__ import annotations

from app.extensions import db
from app.models import Vendor, VendorLink
from sqlalchemy import func


class LinkInvalidoError(Exception):
    """El título o la URL del enlace no son válidos."""


# Selector rápido de red social para "Nuevo enlace" (2026-09-15, pedido de
# Jose): a mucha gente le cuesta encontrar y pegar la URL completa de su
# perfil — esto le permite elegir el ícono de su red y escribir solo su
# usuario (ver `construir_url_red_social`, que también acepta que pegue el
# enlace completo si ya lo tiene a mano). Las claves coinciden a propósito
# con `iconos_service._DOMINIOS_REDES_SOCIALES`, así el ícono elegido acá
# es el mismo que `detectar_red_social` reconoce después en la tienda
# pública. No están TODAS las redes de ese diccionario: WhatsApp ya tiene
# su propio campo de teléfono en el perfil (no es un "usuario" de texto),
# y Mercado Libre/WeChat/Vimeo/Clapper no tienen una URL de perfil armable
# solo con un usuario (subdominio por país, etc.) — esas siguen
# disponibles como "Otro enlace", pegando la URL de siempre. Amazon, eBay,
# Discord, Twitch y Spotify se agregaron el 2026-09-16 (pedido de Jose).
REDES_RAPIDAS_LINK: list[tuple[str, str]] = [
    ("instagram", "Instagram"),
    ("tiktok", "TikTok"),
    ("facebook", "Facebook"),
    ("x", "X (Twitter)"),
    ("youtube", "YouTube"),
    ("linkedin", "LinkedIn"),
    ("threads", "Threads"),
    ("telegram", "Telegram"),
    ("snapchat", "Snapchat"),
    ("reddit", "Reddit"),
    ("onlyfans", "OnlyFans"),
    ("fansly", "Fansly"),
    ("discord", "Discord"),
    ("twitch", "Twitch"),
    ("spotify", "Spotify"),
    ("amazon", "Amazon"),
    ("ebay", "eBay"),
]

# Plantilla de URL de cada red rápida — "{usuario}" se reemplaza por lo
# que escriba el vendedor, ya limpio de "@" y espacios (ver
# `construir_url_red_social`). Discord es un caso especial: no tiene un
# perfil público por nombre de usuario, así que acá "usuario" es en
# realidad el código de invitación de su servidor/comunidad (lo que la
# gente comparte como "mi Discord es tal").
_PLANTILLA_URL_RED: dict[str, str] = {
    "instagram": "https://instagram.com/{usuario}",
    "tiktok": "https://www.tiktok.com/@{usuario}",
    "facebook": "https://facebook.com/{usuario}",
    "x": "https://x.com/{usuario}",
    "youtube": "https://youtube.com/@{usuario}",
    "linkedin": "https://linkedin.com/in/{usuario}",
    "threads": "https://www.threads.net/@{usuario}",
    "telegram": "https://t.me/{usuario}",
    "snapchat": "https://www.snapchat.com/add/{usuario}",
    "reddit": "https://www.reddit.com/user/{usuario}",
    "onlyfans": "https://onlyfans.com/{usuario}",
    "fansly": "https://fansly.com/{usuario}",
    "discord": "https://discord.gg/{usuario}",
    "twitch": "https://twitch.tv/{usuario}",
    "spotify": "https://open.spotify.com/user/{usuario}",
    "amazon": "https://www.amazon.com/shop/{usuario}",
    "ebay": "https://www.ebay.com/str/{usuario}",
}
_NOMBRE_RED_RAPIDA: dict[str, str] = dict(REDES_RAPIDAS_LINK)


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


def construir_url_red_social(clave: str, valor: str) -> str:
    """Arma la URL final de un enlace del selector rápido de redes sociales.

    Acepta 2 formas de escribir `valor` (mismo criterio que Linktree/
    Beacons, pedido de Jose): el usuario solo, con o sin "@" adelante
    (ej. "@josemoramoron" o "josemoramoron"), o el enlace completo ya
    copiado desde la red (ej. "https://instagram.com/josemoramoron") — si
    ya empieza con http(s)://, se usa tal cual (mismas reglas que
    cualquier otro enlace, ver `_validar_url_link`) en vez de tratarlo
    como nombre de usuario.

    Args:
        clave: Una de las claves de `REDES_RAPIDAS_LINK`.
        valor: Lo que escribió/pegó el vendedor en el campo de usuario.

    Returns:
        La URL completa, lista para guardar en el `VendorLink`.

    Raises:
        LinkInvalidoError: Si `clave` no es una red reconocida, o si
            `valor` queda vacío después de limpiarlo.
    """
    valor = valor.strip()
    if not valor:
        raise LinkInvalidoError("Escribe tu usuario, o pega el enlace completo.")
    if valor.lower().startswith(("http://", "https://")):
        return _validar_url_link(valor)
    plantilla = _PLANTILLA_URL_RED.get(clave)
    if plantilla is None:
        raise LinkInvalidoError("Red social no reconocida.")
    usuario = valor.lstrip("@").strip().strip("/")
    if not usuario:
        raise LinkInvalidoError("Escribe tu usuario, o pega el enlace completo.")
    return plantilla.format(usuario=usuario)


def nombre_red_rapida(clave: str) -> str | None:
    """Nombre visible de una red del selector rápido, por su clave.

    Se usa para autocompletar el título del botón (ej. "Instagram") si
    el vendedor no escribió uno propio al usar el selector rápido.

    Args:
        clave: Una de las claves de `REDES_RAPIDAS_LINK`.

    Returns:
        El nombre visible, o None si `clave` no es una red reconocida.
    """
    return _NOMBRE_RED_RAPIDA.get(clave)


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
