"""Extracción de video/clip/canal de Twitch para los embeds de e-link.

Hermano de `youtube_service.py`/`tiktok_service.py`/`vimeo_service.py` —
ver `video_service.py` para el dispatcher único. Twitch distingue TRES
tipos de contenido con URLs y mecanismos de embed distintos — por eso
expone tres funciones de detección en vez de una sola, y
`video_service.py` las guarda bajo tres claves de plataforma separadas
("twitch_video"/"twitch_clip"/"twitch_channel"), aunque de cara al
vendedor sea solo "Twitch".

- **Video (VOD)**: `twitch.tv/videos/ID` — se guarda el ID numérico.
- **Clip**: `clips.twitch.tv/SLUG` o `twitch.tv/canal/clip/SLUG` — se
  guarda el "slug" (el identificador alfanumérico del clip).
- **Canal (en vivo)** (2026-10-01, Jose probó con el link de su propio
  canal — `twitch.tv/usuario`, el que se comparte para invitar a ver
  un stream en vivo — y no se reconocía): `twitch.tv/USUARIO`, sin
  `/videos/` ni `/clip/` en la ruta — se guarda el nombre de usuario
  tal cual. El Reproductor de Twitch para un canal (`player.twitch.tv/
  ?channel=USUARIO`) funciona esté el canal en vivo o no (muestra la
  pantalla "offline" del canal cuando no transmite), así que no hace
  falta consultar la API de Twitch para saber si está en vivo.

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

# Reconoce el link de un canal de Twitch (twitch.tv/USUARIO, sin nada
# más en la ruta) — hay que probarlo DESPUÉS de descartar video/clip,
# porque esas rutas también empiezan con "twitch.tv/algo". Los nombres
# de usuario de Twitch son letras/números/guion bajo, 4 a 25
# caracteres.
_PATRON_CANAL = re.compile(r"twitch\.tv/([A-Za-z0-9_]{4,25})(?:$|[/?])", re.IGNORECASE)

# Rutas de Twitch que no son un canal, para no confundirlas con uno
# cuando no matchearon video/clip (ej. un link a la sección "drops" o
# al directorio general, que tiene la misma forma twitch.tv/palabra).
_RUTAS_RESERVADAS = frozenset({
    "videos", "directory", "settings", "subscriptions", "wallet", "drops",
    "turbo", "payments", "login", "signup", "friends", "inventory",
    "p", "jobs", "security", "logout", "search", "messages", "prime",
    "products", "team", "teams", "creatorcamp", "store",
})


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID numérico de un video (VOD) de Twitch.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID numérico si `url` es un link de video de Twitch
        (`twitch.tv/videos/...`), o None en caso contrario (incluye un
        link de clip o de canal, que se reconocen aparte).
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


def extraer_canal(url: str | None) -> str | None:
    """Extrae el nombre de usuario de un link de canal de Twitch (en vivo).

    Se prueba después de `extraer_id_video`/`extraer_clip_slug` en
    `video_service.resolver_campos_video` — un link de video o de clip
    también matchea la forma "twitch.tv/algo", así que hay que
    descartar esos dos primero para no confundirlos con un canal.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El nombre de usuario si `url` es un link de canal de Twitch
        reconocible y no es una ruta reservada del sitio (ver
        `_RUTAS_RESERVADAS`), o None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    if _PATRON_VIDEO.search(url) or _PATRON_CLIP_SUBDOMINIO.search(url) or _PATRON_CLIP_RUTA.search(url):
        return None
    coincidencia = _PATRON_CANAL.search(url)
    if not coincidencia:
        return None
    canal = coincidencia.group(1)
    if canal.lower() in _RUTAS_RESERVADAS:
        return None
    return canal
