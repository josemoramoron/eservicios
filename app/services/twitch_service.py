"""Extracción de video/clip de Twitch para los embeds de e-link.

Hermano de `youtube_service.py`/`tiktok_service.py`/`vimeo_service.py` —
ver `video_service.py` para el dispatcher único. Twitch distingue dos
tipos de contenido con URLs y mecanismos de embed distintos — por eso
expone dos funciones de detección en vez de una sola, y
`video_service.py` las guarda bajo dos claves de plataforma separadas
("twitch_video"/"twitch_clip"), aunque de cara al vendedor sea solo
"Twitch".

- **Video (VOD)**: `twitch.tv/videos/ID` — se guarda el ID numérico.
- **Clip**: `clips.twitch.tv/SLUG` o `twitch.tv/canal/clip/SLUG` — se
  guarda el "slug" (el identificador alfanumérico del clip).

El Reproductor de Twitch exige un parámetro `parent` con el dominio
exacto desde donde se embebe (mismo requisito de seguridad que
cualquier sitio que embeba Twitch) — como cada tienda de e-link vive en
su propio subdominio (`<negocio>.eservicios.org`), ese parámetro no se
puede fijar de antemano del lado del servidor: `tienda.js` lo arma al
vuelo con `location.hostname`, el dominio real de la página que está
mostrando el video en cada caso.
"""
from __future__ import annotations

import re

_PATRON_VIDEO = re.compile(r"twitch\.tv/videos/(\d+)")
_PATRON_CLIP_SUBDOMINIO = re.compile(r"clips\.twitch\.tv/([A-Za-z0-9_-]+)")
_PATRON_CLIP_RUTA = re.compile(r"twitch\.tv/[\w]+/clip/([A-Za-z0-9_-]+)")


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID numérico de un video (VOD) de Twitch.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID numérico si `url` es un link de video de Twitch
        (`twitch.tv/videos/...`), o None en caso contrario (incluye un
        link de clip, que se reconoce aparte con `extraer_clip_slug`).
    """
    if not url:
        return None
    coincidencia = _PATRON_VIDEO.search(url.strip())
    return coincidencia.group(1) if coincidencia else None


def extraer_clip_slug(url: str | None) -> str | None:
    """Extrae el "slug" de un clip de Twitch, en cualquiera de sus dos formas de link.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El slug del clip si `url` es un link de clip de Twitch
        reconocible, o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    coincidencia = _PATRON_CLIP_SUBDOMINIO.search(url) or _PATRON_CLIP_RUTA.search(url)
    return coincidencia.group(1) if coincidencia else None
