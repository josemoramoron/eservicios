"""Extracción y validación de links de video de TikTok para los embeds de e-link.

Hermano de `youtube_service.py` para la misma función del roadmap
("Video, estados y productos digitales bloqueados"), pero con una
diferencia importante: el link público de un video de TikTok
(`tiktok.com/@usuario/video/VIDEOID`) incluye el nombre de usuario en
la ruta, y TikTok lo resuelve por esa ruta completa — a diferencia de
YouTube, que resuelve por ID sin importar nada más, un link de TikTok
deja de funcionar si el usuario cambia de nombre o si la ruta no
coincide exacto. Por eso acá SÍ se guarda el link completo que pegó el
vendedor (`VendorProduct.tiktok_video_url` / `Vendor.tiktok_trailer_video_url`,
en vez de un ID de 11 caracteres como en YouTube) y el ID numérico para
el embed se recalcula al vuelo con `extraer_id_video` cada vez que hace
falta — ver `vendor_theming_service.resolver_video_producto`/
`resolver_trailer_vendor`.

El "Embed Player" oficial de TikTok (`tiktok.com/player/v1/VIDEOID`) sí
resuelve solo por el ID numérico, sin necesitar el usuario — por eso es
estable aunque el link público del vendedor deje de funcionar más
adelante (ej. si cambia su @usuario en TikTok). Esa URL de embed ya no
se arma acá — desde 2026-10-01 el armado se unificó del lado del
cliente en `tienda.js` (tabla `PLATAFORMAS_VIDEO`) para las 4
plataformas de tipo "iframe" (YouTube, TikTok, Vimeo, Twitch) — ver
`app/services/video_service.py`.

Mismo criterio de "silenciosamente inválido" que `youtube_service`: un
link que no matchea el formato reconocido simplemente no se guarda
(None), sin lanzar ningún error.

OJO — limitación conocida (2026-10-01): el link CORTO que da el botón
"Compartir" de la app de TikTok (`vm.tiktok.com/XXXXXXX/` o
`vt.tiktok.com/XXXXXXX/`) todavía no se reconoce acá. Ese formato no
trae el ID en la URL — hace falta resolver un redirect contra TikTok
en el momento de guardar para sacarlo, algo que hoy ningún otro link
del sitio necesita (todo lo demás es puro regex, sin red). Se deja
fuera a propósito por ahora; si los vendedores chocan con esto en la
práctica, se agrega aparte. Mientras tanto, el vendedor debe pegar el
link "largo" (el que se ve en la barra de direcciones del navegador,
con su @usuario y "/video/" en la ruta), no el link corto del botón de
compartir del celular.
"""
from __future__ import annotations

import re

# Reconoce el link público normal de un video de TikTok:
#   https://www.tiktok.com/@usuario/video/VIDEOID
#   https://m.tiktok.com/@usuario/video/VIDEOID
# con o sin "www."/"m." al principio, y con o sin parámetros extra al
# final (ej. ?is_from_webapp=1&sender_device=pc, que TikTok agrega solo
# al copiar desde el navegador). El ID es siempre numérico.
_PATRON_VIDEO_ID = re.compile(r"tiktok\.com/@[\w.-]+/video/(\d+)")


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID numérico de un link de video de TikTok.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID numérico si `url` es un link de TikTok reconocible, o
        None si viene vacío o no matchea el formato conocido (link de
        otro sitio, el link corto de "Compartir" del celular — ver
        limitación en el docstring del módulo, un link pegado a
        medias, etc.).
    """
    if not url:
        return None
    coincidencia = _PATRON_VIDEO_ID.search(url.strip())
    return coincidencia.group(1) if coincidencia else None


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de TikTok y lo recorta, listo para guardarse tal cual.

    A diferencia de YouTube (que guarda solo el ID porque alcanza para
    reconstruir el link), acá se guarda el link completo — ver el
    docstring del módulo.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El link recortado (sin espacios al borde) si es reconocible, o
        None en caso contrario.
    """
    if not url or not extraer_id_video(url):
        return None
    return url.strip()
