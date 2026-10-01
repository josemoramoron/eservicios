"""Punto único de entrada para detectar la plataforma de un video de e-link.

Los formularios de producto y de perfil piden al vendedor un solo
campo de "link de video" — decisión de Jose 2026-10-01 al sumar TikTok
("recuerda POO": un campo único que detecta la red, en vez de un
input separado por plataforma) — que acepta indistintamente un link de
YouTube (`youtube_service`) o de TikTok (`tiktok_service`). Este
módulo es el que decide cuál es de las dos, y le devuelve a cada
service de guardado (`vendor_producto_service.crear_producto`/
`actualizar_producto`, `vendor_perfil_service.actualizar_perfil`) los
valores ya resueltos para las columnas de cada plataforma —
mutuamente excluyentes: un producto o un perfil tiene como mucho un
video, de una sola plataforma a la vez.

Agregar una plataforma nueva en el futuro (Instagram, por ejemplo) es
sumar un `servicio_nueva_plataforma.py` hermano de estos dos más una
rama más acá — ningún otro módulo necesita saber que existen varias
plataformas.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import tiktok_service, youtube_service


@dataclass(frozen=True)
class CamposVideo:
    """Valores ya resueltos, listos para guardar en las columnas de video de un modelo."""

    youtube_video_id: str | None
    tiktok_video_url: str | None


def resolver_campos_video(url: str | None) -> CamposVideo:
    """Detecta la plataforma de `url` y devuelve los valores listos para guardar.

    Prueba primero YouTube y después TikTok. Mismo criterio de
    "silenciosamente inválido" que ambos services: si `url` viene
    vacío, es de otro sitio, o es un formato de alguna de las dos
    plataformas que todavía no se reconoce (ver las limitaciones
    documentadas en cada service), ambos campos quedan en None — lo
    que en la práctica borra cualquier video guardado antes.

    Args:
        url: Link completo pegado por el vendedor en el campo único de
            video, o vacío/None.

    Returns:
        `CamposVideo` con como mucho uno de los dos campos distinto de
        None.
    """
    video_id_youtube = youtube_service.extraer_id_video(url)
    if video_id_youtube:
        return CamposVideo(youtube_video_id=video_id_youtube, tiktok_video_url=None)
    url_tiktok = tiktok_service.normalizar_url(url)
    if url_tiktok:
        return CamposVideo(youtube_video_id=None, tiktok_video_url=url_tiktok)
    return CamposVideo(youtube_video_id=None, tiktok_video_url=None)


def armar_url_prellenado(youtube_video_id: str | None, tiktok_video_url: str | None) -> str:
    """URL para precargar el campo único de video de un formulario.

    YouTube se reconstruye desde el ID guardado (ver
    `youtube_service.armar_url_watch`) porque alcanza. TikTok no se
    puede reconstruir desde un ID (su link público exige el @usuario
    correcto en la ruta — ver `tiktok_service`), así que ahí se guardó
    el link completo tal cual y se devuelve sin tocar.

    Args:
        youtube_video_id: `VendorProduct.youtube_video_id` o
            `Vendor.youtube_trailer_video_id`, o None.
        tiktok_video_url: `VendorProduct.tiktok_video_url` o
            `Vendor.tiktok_trailer_video_url`, o None.

    Returns:
        La URL lista para el `value` de un `<input>`, o cadena vacía
        si no hay ningún video guardado.
    """
    if youtube_video_id:
        return youtube_service.armar_url_watch(youtube_video_id)
    if tiktok_video_url:
        return tiktok_video_url
    return ""
