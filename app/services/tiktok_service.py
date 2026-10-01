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
link que no matchea ningún formato reconocido (incluido un link corto
cuyo redirect no se pudo resolver, ver abajo) simplemente no se guarda
(None), sin lanzar ningún error.

Link CORTO de "Compartir" (2026-10-01, Jose reportó que era el único
que no andaba — antes quedaba afuera a propósito, ver el commit
anterior): el botón "Compartir" de la app de TikTok en el celular da
`vm.tiktok.com/XXXXXXX/` o `vt.tiktok.com/XXXXXXX/`, un link que NO
trae el ID del video — es un redirect que TikTok resuelve del otro
lado. A diferencia de las demás plataformas (puro regex, sin red), acá
hace falta seguir ese redirect una vez, en el momento de guardar
(`_resolver_link_corto`), para conseguir el link largo de siempre y
extraerle el ID como de costumbre. Con un User-Agent de navegador de
escritorio (TikTok no resuelve el redirect igual, o directamente lo
bloquea, si detecta un cliente sin UA de navegador) y un timeout corto
— si TikTok no responde a tiempo o el link no resuelve a un video
reconocible, se guarda None como cualquier otro link inválido, nunca
se le muestra un error al vendedor por esto.
"""
from __future__ import annotations

import re

import requests

# Reconoce el link público normal de un video de TikTok:
#   https://www.tiktok.com/@usuario/video/VIDEOID
#   https://m.tiktok.com/@usuario/video/VIDEOID
# con o sin "www."/"m." al principio, y con o sin parámetros extra al
# final (ej. ?is_from_webapp=1&sender_device=pc, que TikTok agrega solo
# al copiar desde el navegador). El ID es siempre numérico.
_PATRON_VIDEO_ID = re.compile(r"tiktok\.com/@[\w.-]+/video/(\d+)")

# Reconoce el link CORTO que da el botón "Compartir" de la app de
# TikTok en el celular — no trae el ID, hace falta resolver su
# redirect (ver _resolver_link_corto).
_PATRON_LINK_CORTO = re.compile(r"(?:vm|vt)\.tiktok\.com/[\w-]+", re.IGNORECASE)

_TIMEOUT_SEGUNDOS = 6

# TikTok responde con una interstitial (o directamente no redirige)
# si el pedido no parece venir de un navegador real — mismo UA que un
# Chrome de escritorio reciente, sin ninguna otra intención.
_USER_AGENT_NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _resolver_link_corto(url: str) -> str | None:
    """Sigue el redirect de un link corto `vm.tiktok.com`/`vt.tiktok.com` y devuelve el link largo.

    Única llamada de red de todo el módulo de video (el resto de las
    plataformas, incluido el resto de TikTok, es puro regex). Se usa
    `stream=True` para no bajar el cuerpo de la respuesta — alcanza con
    la URL final a la que redirigió, en `response.url`.

    Args:
        url: El link corto tal cual lo pegó el vendedor.

    Returns:
        El link largo ya resuelto (listo para `extraer_id_video`), o
        None si TikTok no respondió, tardó más de `_TIMEOUT_SEGUNDOS`,
        o cualquier otro error de red — mismo criterio "silenciosamente
        inválido" que el resto del módulo.
    """
    try:
        respuesta = requests.get(
            url,
            allow_redirects=True,
            timeout=_TIMEOUT_SEGUNDOS,
            headers={"User-Agent": _USER_AGENT_NAVEGADOR},
            stream=True,
        )
        respuesta.close()
    except requests.RequestException:
        return None
    return respuesta.url


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID numérico de un link de video de TikTok.

    No resuelve links cortos (`vm.tiktok.com`/`vt.tiktok.com`) — eso
    solo lo hace `normalizar_url`, que es quien decide si vale la pena
    pagar esa llamada de red. Esta función se queda en puro regex,
    sobre el link ya largo.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID numérico si `url` es un link de TikTok reconocible, o
        None si viene vacío o no matchea el formato conocido (link de
        otro sitio, un link corto todavía sin resolver, un link pegado
        a medias, etc.).
    """
    if not url:
        return None
    coincidencia = _PATRON_VIDEO_ID.search(url.strip())
    return coincidencia.group(1) if coincidencia else None


def normalizar_url(url: str | None) -> str | None:
    """Valida un link de TikTok y lo recorta, listo para guardarse tal cual.

    A diferencia de YouTube (que guarda solo el ID porque alcanza para
    reconstruir el link), acá se guarda el link completo — ver el
    docstring del módulo. Si `url` es el link corto de "Compartir"
    (`vm.tiktok.com`/`vt.tiktok.com`), primero resuelve su redirect y
    guarda el link largo resultante, no el corto.

    Args:
        url: Link completo (o corto) pegado por el vendedor, o
            vacío/None.

    Returns:
        El link recortado (sin espacios al borde) si es reconocible, o
        None en caso contrario.
    """
    if not url:
        return None
    url = url.strip()
    if _PATRON_LINK_CORTO.search(url):
        url_resuelta = _resolver_link_corto(url)
        if not url_resuelta:
            return None
        url = url_resuelta
    if not extraer_id_video(url):
        return None
    return url
