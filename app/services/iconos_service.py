"""Carga de íconos SVG inline para las categorías del catálogo.

Los íconos se insertan inline en el HTML (no como `<img src="...">`)
para que `stroke="currentColor"` herede el `color` de CSS y se adapten
a tema claro/oscuro, según la regla de `.clinerules`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ICONOS_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "categorias"


@lru_cache(maxsize=64)
def obtener_icono_svg(slug: str) -> str:
    """Lee el contenido de un ícono SVG de categoría por su slug.

    El resultado se cachea en memoria (los archivos son estáticos y no
    cambian mientras el proceso está corriendo).

    Args:
        slug: Slug de la categoría, debe coincidir con el nombre del
            archivo `<slug>.svg` dentro de `static/img/categorias/`.

    Returns:
        El markup SVG como texto, o una cadena vacía si no existe el
        archivo (para que la plantilla simplemente no muestre nada).
    """
    ruta = _ICONOS_DIR / f"{slug}.svg"
    if not ruta.is_file():
        return ""
    return ruta.read_text(encoding="utf-8")
