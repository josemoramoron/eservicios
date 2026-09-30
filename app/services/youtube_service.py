"""Extracción y validación de IDs de video de YouTube para los embeds de e-link.

Los formularios de producto y de perfil (`VendorProduct.youtube_video_id`
/ `Vendor.youtube_trailer_video_id`) piden al vendedor que pegue el link
completo del video, tal como lo copia desde YouTube o desde la app para
compartir — este módulo es el único lugar que sabe reconocer las
distintas formas que puede tener ese link (`watch?v=`, `youtu.be/`,
`shorts/`, `embed/`) y quedarse solo con el ID de 11 caracteres, que es
lo único que en verdad se guarda (ver el comentario en ambos modelos).
Reconstruir una URL para volver a mostrarla en un formulario es tan
simple como `armar_url_watch` — no hace falta guardar el link original
completo.

Mismo criterio de "silenciosamente inválido" que `badges_producto_service`
/ `estados_stock_service`: un link que no matchea ningún formato conocido
simplemente no se guarda (None), sin lanzar ningún error — ver
`vendor_producto_service.crear_producto`/`actualizar_producto` y
`vendor_perfil_service.actualizar_perfil`, que son quienes de verdad
guardan el resultado de `extraer_id_video`.
"""
from __future__ import annotations

import re

# El ID de un video de YouTube son siempre 11 caracteres (letras,
# números, "-" y "_"). Se acepta pegado en cualquiera de sus formatos
# habituales:
#   https://www.youtube.com/watch?v=VIDEOID   (+ parámetros extra, ej. &t=10s)
#   https://youtu.be/VIDEOID
#   https://www.youtube.com/shorts/VIDEOID
#   https://www.youtube.com/embed/VIDEOID
# con o sin "www.", "http" o "https" al principio.
_PATRON_VIDEO_ID = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extraer_id_video(url: str | None) -> str | None:
    """Extrae el ID de video de un link de YouTube, en cualquiera de sus formatos.

    Args:
        url: Link completo pegado por el vendedor, o vacío/None.

    Returns:
        El ID de 11 caracteres si `url` es un link de YouTube reconocible,
        o None si viene vacío o no matchea ningún formato conocido (link
        de otro sitio, pegado a medias, un ID que no llegó a copiarse
        entero, etc.).
    """
    if not url:
        return None
    coincidencia = _PATRON_VIDEO_ID.search(url.strip())
    return coincidencia.group(1) if coincidencia else None


def armar_embed_url(video_id: str) -> str:
    """Arma la URL de embed (youtube-nocookie.com) para un ID de video ya validado.

    Se usa el dominio "youtube-nocookie.com" en vez de "youtube.com/embed"
    a propósito (recomendación de Google para reducir cookies de
    terceros antes de que el visitante interactúe con el reproductor) —
    mismo video, mismo comportamiento, para el vendedor no cambia nada.

    Args:
        video_id: ID de 11 caracteres ya extraído con `extraer_id_video`.

    Returns:
        URL lista para el `src` de un `<iframe>`.
    """
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def armar_url_watch(video_id: str | None) -> str:
    """Reconstruye una URL "watch" normal a partir de un ID guardado, para precargar un formulario.

    Args:
        video_id: ID guardado (`Vendor.youtube_trailer_video_id` o
            `VendorProduct.youtube_video_id`), o None.

    Returns:
        La URL lista para el `value` de un `<input>`, o cadena vacía si
        no hay ningún ID guardado.
    """
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
