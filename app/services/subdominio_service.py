"""Resolución de subdominio de vendedor a partir del host de la petición.

Usado por el `before_request` de `app/__init__.py` para decidir si una
petición debe servir la tienda pública de un vendedor en vez del sitio
normal. Ver `claude/spec-tiendas-vendedor.md` (sección 4) en el
proyecto para el diseño completo.
"""
from __future__ import annotations

from app.services.vendor_service import obtener_vendor_por_slug_activo


def extraer_slug_de_host(host: str, dominio_base: str) -> str | None:
    """Extrae el slug de subdominio de un host, si corresponde a uno de vendedor.

    Args:
        host: Header Host de la petición (puede incluir puerto, ej.
            "electroandes.eservicios.org" o "localhost:5000").
        dominio_base: Dominio raíz del sitio (ej. "eservicios.org").

    Returns:
        El slug en minúsculas si el host es "<slug>.<dominio_base>" con
        un único nivel de subdominio, o None si es el dominio raíz,
        "www", o no coincide con el dominio base en absoluto (ej. un
        `localhost` de desarrollo).
    """
    host_sin_puerto = host.split(":")[0].lower()
    dominio_base = dominio_base.lower()

    if host_sin_puerto in (dominio_base, f"www.{dominio_base}"):
        return None
    sufijo = f".{dominio_base}"
    if not host_sin_puerto.endswith(sufijo):
        return None

    subdominio = host_sin_puerto[: -len(sufijo)]
    if not subdominio or "." in subdominio:
        # Vacío (no debería pasar) o con más de un nivel — no es una tienda.
        return None
    return subdominio


def resolver_vendor_por_host(host: str, dominio_base: str):
    """Busca la tienda de vendedor activa correspondiente a un host.

    Args:
        host: Header Host de la petición.
        dominio_base: Dominio raíz del sitio.

    Returns:
        El `Vendor` activo si el host corresponde a un subdominio de
        vendedor existente, o None si no aplica o no se encontró.
    """
    slug = extraer_slug_de_host(host, dominio_base)
    if slug is None:
        return None
    return obtener_vendor_por_slug_activo(slug)
