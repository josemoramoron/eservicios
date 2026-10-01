"""Validación de links de post de X (antes Twitter) para los embeds de e-link.

Mismo criterio que `facebook_service.py`/`threads_service.py`/
`instagram_service.py`: se guarda el link completo, porque el embed de
X tampoco es un `<iframe>` sino un
`<blockquote class="twitter-tweet"><a href="LINK"></a></blockquote>`
que el script `widgets.js` de X/Twitter (cargado por `tienda.js`)
reemplaza por el post real. Gratis y sin token de acceso — funciona
igual con un link de `x.com` que de `twitter.com` (el dominio viejo
sigue resolviendo).
"""
from __future__ import annotations

import re

# Reconoce el link normal de un post, con cualquiera de los dos
# dominios (x.com o twitter.com).
_PATRON = re.compile(r"(?:x\.com|twitter\.com)/\w+/status/\d+", re.IGNORECASE)


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de post de X y lo recorta, listo para guardarse tal cual.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El link recortado si es reconocible, o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    return url if _PATRON.search(url) else None
