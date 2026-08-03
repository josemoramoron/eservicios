"""Carga de íconos SVG inline (categorías del catálogo y redes sociales).

Los íconos se insertan inline en el HTML (no como `<img src="...">`)
para que `stroke="currentColor"` / `fill="currentColor"` hereden el
`color` de CSS y se adapten a tema claro/oscuro, según la regla de
`.clinerules`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_STATIC_IMG_DIR = Path(__file__).resolve().parent.parent / "static" / "img"
_CATEGORIAS_DIR = _STATIC_IMG_DIR / "categorias"
_REDES_DIR = _STATIC_IMG_DIR / "redes"


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
