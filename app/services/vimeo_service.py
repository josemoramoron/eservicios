"""Extracción del ID de video de Vimeo para los embeds de e-link.

Hermano de `youtube_service.py`/`tiktok_service.py` — ver `video_service.py`
para el dispatcher único que los combina. Vimeo es, de las plataformas
nuevas (2026-10-01: Vimeo, Twitch, Facebook, Threads, Instagram, X), la
más parecida a YouTube: el Reproductor de Vimeo (`player.vimeo.com/video/ID`)
resuelve por ID numérico sin pedir nada más — por eso acá también alcanza
con guardar el ID, no el link completo.
"""
from __future__ import annotations

import re

# Reconoce el link normal de un video de Vimeo en cualquiera de sus
# formas habituales — directo (vimeo.com/ID), dentro de un canal
# (vimeo.com/channels/nombre/ID), de un grupo
# (vimeo.com/groups/nombre/videos/ID), de un álbum
# (vimeo.com/album/N/video/ID) o ya con la URL de embed
# (player.vimeo.com/video/ID, por si el vendedor la copia tal cual).
#
# OJO — limitación conocida: no reconoce el "hash" extra que trae un
# video marcado como "unlisted" en Vimeo (vimeo.com/ID/hashextra) — ese
# tipo de video seguiría sin reproducirse embebido. Alcanza para el
# caso normal (video público).
_PATRON_ID = re.compile(
    r"(?:vimeo\.com/(?:channels/(?:[^/]+/)?|groups/[^/]+/videos/|album/\d+/video/)?|"
    r"player\.vimeo\.com/video/)(\d+)(?:$|[/?])"
)


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID numérico de un link de video de Vimeo.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID numérico si `url` es un link de Vimeo reconocible, o None
        en caso contrario.
    """
    if not url:
        return None
    coincidencia = _PATRON_ID.search(url.strip())
    return coincidencia.group(1) if coincidencia else None
