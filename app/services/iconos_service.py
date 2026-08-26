"""Carga de íconos SVG inline (categorías del catálogo y redes sociales).

Los íconos se insertan inline en el HTML (no como `<img src="...">`)
para que `stroke="currentColor"` / `fill="currentColor"` hereden el
`color` de CSS y se adapten a tema claro/oscuro, según la regla de
`.clinerules`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

_STATIC_IMG_DIR = Path(__file__).resolve().parent.parent / "static" / "img"
_CATEGORIAS_DIR = _STATIC_IMG_DIR / "categorias"
_REDES_DIR = _STATIC_IMG_DIR / "redes"

# Dominios de redes sociales reconocidas -> clave de ícono (coincide con el
# nombre de archivo en `static/img/redes/`). Se usa para decidir si un
# `VendorLink` se muestra como botón circular con ícono (red reconocida) o
# como botón con texto (cualquier otro sitio) en la tienda pública.
_DOMINIOS_REDES_SOCIALES: dict[str, str] = {
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "twitter.com": "x",
    "x.com": "x",
    "tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "wa.me": "whatsapp",
    "whatsapp.com": "whatsapp",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "telegram.org": "telegram",
    "onlyfans.com": "onlyfans",
    "fansly.com": "fansly",
    "clapperapp.com": "clapper",
    "reddit.com": "reddit",
    "redd.it": "reddit",
    "threads.net": "threads",
    "threads.com": "threads",
    "discord.com": "discord",
    "discord.gg": "discord",
    "wechat.com": "wechat",
    "vimeo.com": "vimeo",
    "snapchat.com": "snapchat",
}

# Mercado Libre/Mercado Livre usa un dominio de nivel superior distinto por
# país (mercadolibre.com.ar, mercadolibre.com.mx, mercadolivre.com.br,
# etc.) — en vez de listar cada TLD a mano en el diccionario de arriba, se
# reconoce buscando esta etiqueta dentro del dominio completo.
_ETIQUETAS_MERCADOLIBRE = ("mercadolibre", "mercadolivre")


def _leer_svg(ruta: Path) -> str:
    """Lee el contenido de un archivo SVG si existe.

    Args:
        ruta: Ruta absoluta al archivo `.svg`.

    Returns:
        El markup SVG como texto, o cadena vacía si el archivo no existe.
    """
    if not ruta.is_file():
        return ""
    return ruta.read_text(encoding="utf-8")


@lru_cache(maxsize=64)
def obtener_icono_categoria(slug: str) -> str:
    """Ícono SVG de una categoría del catálogo, por su slug.

    Args:
        slug: Debe coincidir con `<slug>.svg` en `static/img/categorias/`.

    Returns:
        Markup SVG, o cadena vacía si no existe el archivo.
    """
    return _leer_svg(_CATEGORIAS_DIR / f"{slug}.svg")


@lru_cache(maxsize=32)
def obtener_icono_red(clave: str) -> str:
    """Ícono SVG de una red social, por su clave.

    Args:
        clave: Debe coincidir con `<clave>.svg` en `static/img/redes/`.

    Returns:
        Markup SVG, o cadena vacía si no existe el archivo.
    """
    return _leer_svg(_REDES_DIR / f"{clave}.svg")


def detectar_red_social(url: str) -> str | None:
    """Detecta si una URL pertenece a una red social reconocida, por su dominio.

    Se usa para decidir cómo se muestra un `VendorLink` en la tienda
    pública: las redes reconocidas se pintan como un ícono circular
    (ahorra espacio, se ven varias en una fila), cualquier otro sitio
    se pinta como botón con texto (comportamiento anterior).

    Args:
        url: URL completa del enlace (ya validada con http(s)://).

    Returns:
        La clave del ícono (coincide con `obtener_icono_red`) si el
        dominio es una red social reconocida, o None si no lo es.
    """
    dominio = urlparse(url).netloc.lower()
    if dominio.startswith("www."):
        dominio = dominio[4:]
    for sufijo, clave in _DOMINIOS_REDES_SOCIALES.items():
        if dominio == sufijo or dominio.endswith(f".{sufijo}"):
            return clave
    if any(etiqueta in dominio.split(".") for etiqueta in _ETIQUETAS_MERCADOLIBRE):
        return "mercadolibre"
    return None
