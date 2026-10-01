"""Punto único de entrada para detectar la plataforma de un video de e-link.

Los formularios de producto y de perfil piden al vendedor un solo
campo de "link de video" — decisión de Jose 2026-10-01 ("recuerda
POO"): un campo único que detecta la red, en vez de un input separado
por plataforma. Esto cubre hoy **8 redes**: YouTube, TikTok, Vimeo,
Twitch (video y clip, bajo el mismo campo), Facebook, Threads,
Instagram y X — cada una con su propio service hermano
(`youtube_service.py`, `tiktok_service.py`, `vimeo_service.py`,
`twitch_service.py`, `facebook_service.py`, `threads_service.py`,
`instagram_service.py`, `x_service.py`). Este módulo es el que prueba
cada una en orden y le devuelve a cada service de guardado
(`vendor_producto_service.crear_producto`/`actualizar_producto`,
`vendor_perfil_service.actualizar_perfil`) la pareja (plataforma,
valor) ya resuelta — mutuamente excluyentes: un producto o un perfil
tiene como mucho un video, de una sola plataforma a la vez.

**Esquema de guardado (`video_plataforma`/`video_valor` en
`VendorProduct`, `video_trailer_plataforma`/`video_trailer_valor` en
`Vendor`):** una sola pareja de columnas genéricas para las 8
plataformas, en vez de un par de columnas por plataforma — decisión
tomada acá (2026-10-01, migración `6d9a798e63df`) al sumar las 6 redes
nuevas, para no terminar con 16 columnas (8 plataformas × 2 columnas ×
2 lugares). Reemplaza el diseño anterior de columnas específicas por
YouTube/TikTok (`youtube_video_id`/`tiktok_video_url` y sus
equivalentes de tráiler), que se mantienen en la base de datos como
respaldo histórico de solo lectura (la migración las vuelca ahí antes
de dejar de usarlas) pero ya no están mapeadas en los modelos — ver
`app/models/vendor_product.py`/`vendor.py`.

**"valor" guarda lo mínimo necesario para reconstruir el embed, y eso
varía por plataforma:**
- Reconstruible desde un ID solo (no hace falta guardar el link
  completo): YouTube, Vimeo, Twitch (video y clip).
- El link público exige más que un ID (usuario, dominio, formato
  completo) para seguir funcionando — se guarda el link completo tal
  cual: TikTok, Facebook, Threads, Instagram, X.

**Mecanismo de embed, resuelto enteramente del lado del cliente
(`tienda.js`, tabla `PLATAFORMAS_VIDEO`) a partir de (plataforma,
valor) — este módulo y los resolvers de `vendor_theming_service.py`
NUNCA arman una URL de embed ni HTML de ningún tipo:**
- YouTube, TikTok, Vimeo, Twitch: un `<iframe>` directo — la URL de
  embed se arma en JS a partir del "valor" guardado.
- Facebook, Threads, Instagram, X: no tienen una URL de iframe propia
  — el embed real es un bloque HTML (`<div>`/`<blockquote>`) que el
  script oficial de esa red (cargado una sola vez por `tienda.js`)
  reemplaza por el reproductor/post real. El vendedor nunca necesita
  pensar en HTML ni en cuál mecanismo usa cada red — solo pega el
  link, exactamente igual que con YouTube.

Agregar una plataforma nueva en el futuro es sumar un
`servicio_nueva_plataforma.py` hermano de estos, una rama más acá, y
una entrada más en la tabla `PLATAFORMAS_VIDEO` de `tienda.js` —
ningún otro módulo necesita cambiar.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import (
    facebook_service,
    instagram_service,
    threads_service,
    tiktok_service,
    twitch_service,
    vimeo_service,
    x_service,
    youtube_service,
)

# Plataformas cuyo video es casi siempre vertical (9:16) — usado por
# `vendor_theming_service` para decidir si el modal muestra la caja de
# video vertical o la horizontal de siempre (ver
# `.tienda-modal__video-wrap--vertical` en tienda.css). Solo importa
# para las plataformas de tipo "iframe" (ver tienda.js); las de tipo
# "widget" (Facebook/Threads/Instagram/X) se autodimensionan con su
# propio script y ese valor se ignora para ellas en el cliente excepto
# Instagram, que sí se respeta por si en algún momento se decide armar
# una caja también para su "widget".
PLATAFORMAS_VERTICALES = frozenset({"tiktok", "instagram"})


@dataclass(frozen=True)
class CamposVideo:
    """Valores ya resueltos, listos para guardar en la pareja de columnas de video de un modelo."""

    plataforma: str | None
    valor: str | None


def resolver_campos_video(url: str | None) -> CamposVideo:
    """Detecta la plataforma de `url` entre las 8 reconocidas y devuelve el valor a guardar.

    Prueba cada plataforma en orden (YouTube, TikTok, Vimeo, Twitch
    video, Twitch clip, Facebook, Threads, Instagram, X) y se queda con
    la primera que matchee. Mismo criterio de "silenciosamente
    inválido" que cada service individual: si `url` viene vacío, es de
    un sitio no reconocido, o es un formato de alguna de las 8 que
    todavía no se reconoce (ver las limitaciones documentadas en cada
    service — ej. el link corto de TikTok), ambos campos quedan en
    None, lo que en la práctica borra cualquier video guardado antes.

    Args:
        url: Link completo pegado por el vendedor en el campo único de
            video, o vacío/None.

    Returns:
        `CamposVideo` con, como mucho, una plataforma detectada.
    """
    if video_id := youtube_service.extraer_id_video(url):
        return CamposVideo("youtube", video_id)
    if url_tiktok := tiktok_service.normalizar_url(url):
        return CamposVideo("tiktok", url_tiktok)
    if video_id := vimeo_service.extraer_id_video(url):
        return CamposVideo("vimeo", video_id)
    if video_id := twitch_service.extraer_id_video(url):
        return CamposVideo("twitch_video", video_id)
    if clip_slug := twitch_service.extraer_clip_slug(url):
        return CamposVideo("twitch_clip", clip_slug)
    if url_facebook := facebook_service.normalizar_url(url):
        return CamposVideo("facebook", url_facebook)
    if url_threads := threads_service.normalizar_url(url):
        return CamposVideo("threads", url_threads)
    if url_instagram := instagram_service.normalizar_url(url):
        return CamposVideo("instagram", url_instagram)
    if url_x := x_service.normalizar_url(url):
        return CamposVideo("x", url_x)
    return CamposVideo(None, None)


def armar_url_prellenado(plataforma: str | None, valor: str | None) -> str:
    """URL para precargar el campo único de video de un formulario.

    Las plataformas que guardan el link completo (ver el docstring del
    módulo) devuelven `valor` tal cual. Las que guardan solo un ID
    reconstruyen un link público "normal" a partir de ese ID.

    Args:
        plataforma: `VendorProduct.video_plataforma` o
            `Vendor.video_trailer_plataforma`, o None.
        valor: `VendorProduct.video_valor` o
            `Vendor.video_trailer_valor`, o None.

    Returns:
        La URL lista para el `value` de un `<input>`, o cadena vacía
        si no hay ningún video guardado.
    """
    if not plataforma or not valor:
        return ""
    if plataforma == "youtube":
        return youtube_service.armar_url_watch(valor)
    if plataforma == "vimeo":
        return f"https://vimeo.com/{valor}"
    if plataforma == "twitch_video":
        return f"https://www.twitch.tv/videos/{valor}"
    if plataforma == "twitch_clip":
        return f"https://clips.twitch.tv/{valor}"
    # tiktok, facebook, threads, instagram, x: `valor` ya es el link
    # completo, se guardó tal cual.
    return valor
