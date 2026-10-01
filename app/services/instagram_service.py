"""Validación de links de post/reel de Instagram para los embeds de e-link.

Mismo criterio que `facebook_service.py`/`threads_service.py`: se
guarda el link completo, porque el embed de Instagram tampoco es un
`<iframe>` sino un
`<blockquote class="instagram-media" data-instgrm-permalink="LINK">`
que el script `embed.js` de Instagram (cargado por `tienda.js`)
reemplaza por el post real. Desde junio de 2026 Meta volvió "sin
token" el acceso a este mecanismo — antes exigía crear una app de
Facebook y pasar revisión; hoy alcanza con el link público, igual que
YouTube/TikTok.

A diferencia de TikTok, el link que da el botón "Compartir" de la app
de Instagram YA es el link público permanente (no tiene el problema
del link corto de TikTok, que no trae el ID) — funciona pegado tal
cual.
"""
from __future__ import annotations

import re

# Reconoce el link normal de un post ("/p/"), un reel ("/reel/") o un
# video clásico ("/tv/") de Instagram.
_PATRON = re.compile(r"instagram\.com/(?:p|reel|tv)/[\w-]+", re.IGNORECASE)


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de post/reel de Instagram y lo recorta, listo para guardarse tal cual.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El link recortado si es reconocible, o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    return url if _PATRON.search(url) else None
