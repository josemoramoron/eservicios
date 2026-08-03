"""Información de contacto y redes sociales de eServicios LLC.

Modelada como objetos (no como diccionarios sueltos ni texto embebido
en las plantillas) para que el footer, el botón flotante de WhatsApp
y cualquier otra vista que necesite estos datos los consuman desde un
solo lugar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RedSocial:
    """Una red social de la empresa: nombre, enlace e ícono asociado."""

    clave: str
    """Identificador corto usado para encontrar el ícono SVG (`<clave>.svg`)."""

    nombre: str
    """Nombre para mostrar, ej. "LinkedIn", "X"."""

    url: str
    """Enlace completo al perfil."""

    handle: str | None = None
    """Usuario visible, ej. "@eserviciosllc" (opcional)."""


@dataclass(frozen=True)
class InformacionContacto:
    """Datos de contacto de eServicios LLC."""

    direccion: str
    sitio_web: str
    email: str
    whatsapp_numero: str
    """Número en formato legible, ej. "+1 (201) 680-0843"."""

    @property
    def whatsapp_url(self) -> str:
        """Construye el enlace `wa.me` a partir del número de contacto.

        Returns:
            URL lista para abrir un chat de WhatsApp con ese número.
        """
        solo_digitos = re.sub(r"\D", "", self.whatsapp_numero)
        return f"https://wa.me/{solo_digitos}"


@dataclass(frozen=True)
class InformacionSitio:
    """Agrupa contacto y redes sociales para inyectar en las plantillas."""

    contacto: InformacionContacto
    redes_sociales: list[RedSocial] = field(default_factory=list)


def obtener_info_sitio() -> InformacionSitio:
    """Construye la información de contacto y redes sociales del sitio.

    Returns:
        Instancia de `InformacionSitio` lista para usar en templates.
    """
    contacto = InformacionContacto(
        direccion="Sheridan, Wyoming 82801",
        sitio_web="https://eservicios.org",
        email="info@eservicios.org",
        whatsapp_numero="+1 (201) 680-0843",
    )
    redes_sociales = [
        RedSocial(clave="x", nombre="X", url="https://x.com/eserviciosllc", handle="@eServiciosllc"),
        RedSocial(
            clave="tiktok",
            nombre="TikTok",
            url="https://www.tiktok.com/@eserviciosllc",
            handle="@eServiciosllc",
        ),
        RedSocial(
            clave="linkedin",
            nombre="LinkedIn",
            url="https://www.linkedin.com/company/eservicios-llc/",
            handle="eServicios LLC",
        ),
        RedSocial(
            clave="instagram",
            nombre="Instagram",
            url="https://www.instagram.com/eserviciosllc",
            handle="@eserviciosllc",
        ),
        RedSocial(
            clave="facebook",
            nombre="Facebook",
            url="https://www.facebook.com/6157067676764540",
            handle="EServicios",
        ),
    ]
    return InformacionSitio(contacto=contacto, redes_sociales=redes_sociales)
