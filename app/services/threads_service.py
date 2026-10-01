"""Validación de links de post de Threads para los embeds de e-link.

Mismo criterio que `facebook_service.py`: se guarda el link completo,
porque el embed de Threads tampoco es un `<iframe>` sino un
`<blockquote class="text-post-media" data-text-post-permalink="LINK">`
que el script `embed.js` de Threads (cargado por `tienda.js`) reemplaza
por el post real. Gratis y sin token de acceso.

OJO: un post de Threads no siempre tiene video (puede ser solo texto o
una imagen) — eso lo decide el vendedor al elegir qué pegar, e-link no
lo valida; el widget de Threads igual renderiza el post completo.
"""
from __future__ import annotations

import re

# Reconoce el link normal de un post de Threads, con el dominio
# "nuevo" (threads.com, el que Meta usa desde 2026) o el original
# (threads.net), y en sus dos formas de ruta: la que trae el @usuario
# o la forma corta "/t/".
_PATRON = re.compile(
    r"threads\.(?:net|com)/@[\w.]+/post/[\w-]+|threads\.(?:net|com)/t/[\w-]+",
    re.IGNORECASE,
)


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de post de Threads y lo recorta, listo para guardarse tal cual.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El link recortado si es reconocible, o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    return url if _PATRON.search(url) else None
