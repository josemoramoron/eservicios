"""Validación de links de video de Facebook para los embeds de e-link.

Hermano de `tiktok_service.py` en cuanto al criterio de guardado: acá
también se guarda el link completo (no un ID), porque el mecanismo de
embed de Facebook (a diferencia de YouTube/Vimeo/TikTok/Twitch) no es
un `<iframe>` con una URL propia, sino el "Embedded Video Player" de
Meta — un `<div class="fb-video" data-href="LINK">` que el SDK de
JavaScript de Facebook (cargado una sola vez por página) reemplaza por
el reproductor real. `tienda.js` arma ese `<div>` al vuelo a partir del
link guardado tal cual — el vendedor nunca necesita escribir ni ver
HTML, solo pega el link.

Gratis y sin token de acceso (la Embedded Video Player plugin de Meta
no lo exige para contenido público).
"""
from __future__ import annotations

import re

# Reconoce un link de video público de Facebook en sus dos formas
# habituales: el link largo (facebook.com/.../videos/ID o
# facebook.com/watch/?v=ID) y el link corto para compartir
# (fb.watch/CODIGO).
_PATRON = re.compile(
    r"facebook\.com/(?:[\w.-]+/videos/\d+|watch/?\?v=\d+)|fb\.watch/[\w-]+",
    re.IGNORECASE,
)


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de video de Facebook y lo recorta, listo para guardarse tal cual.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El link recortado si es reconocible, o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    return url if _PATRON.search(url) else None
