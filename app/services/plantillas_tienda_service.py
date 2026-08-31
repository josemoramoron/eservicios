"""Plantillas visuales prediseñadas para la tienda pública de un vendedor.

Cada plantilla es un par (layout + tipografía) coherente, no solo un
cambio de color — por eso vive como su propio archivo de template
(`tienda/publica_<clave>.html`) en vez de una variable CSS más, a
diferencia de la galería de estilos de portada/avatar (punto 26) o el
color de acento (punto 12). Ver `claude/roadmap-monetizacion-e-link.md`,
Fase 2, punto 13 — "absorbe la elección de tipografía": no hay un
selector de fuente aparte, cada plantilla ya trae la suya.

Función de e-link Plus: `vendor_service.resolver_plantilla_vendor()` es
quien de verdad gatea esto contra el plan — este servicio solo conoce
las plantillas disponibles, no decide si un vendedor puede usarlas.

La plantilla "Clásica" (el diseño original de la tienda, gratis para
todos) deliberadamente NO aparece en este diccionario — se representa
como `None`/clave vacía en `Vendor.plantilla`, igual que "Por defecto"
en `estilos_portada_service.PRESETS_PORTADA`, y sigue viviendo en
`tienda/publica.html`.
"""
from __future__ import annotations

PLANTILLAS_TIENDA: dict[str, dict[str, str]] = {
    "editorial": {
        "nombre": "Editorial",
        "descripcion": "Un producto destacado en grande arriba y el resto en una lista con líneas finas, "
        "tipografía Fraunces + Work Sans — estilo catálogo boutique.",
    },
    "minimalista": {
        "nombre": "Minimalista",
        "descripcion": "Lista densa de una sola columna, esquinas rectas y mucho espacio en blanco, "
        "tipografía Manrope + IBM Plex Sans.",
    },
}


def listar_plantillas_tienda() -> list[dict[str, str]]:
    """Devuelve las plantillas premium disponibles, con su clave incluida.

    No incluye "Clásica" (ver el docstring del módulo) — la pantalla de
    `/vendedor/perfil` la agrega aparte como la opción "por defecto".

    Returns:
        Lista de dicts `{"clave", "nombre", "descripcion"}`.
    """
    return [{"clave": clave, **datos} for clave, datos in PLANTILLAS_TIENDA.items()]


def obtener_plantilla_tienda(clave: str | None) -> dict[str, str] | None:
    """Busca una plantilla premium por su clave.

    Args:
        clave: Clave de la plantilla (ej. "editorial"), o vacío/None.

    Returns:
        El dict de la plantilla, o None si `clave` está vacía o no
        corresponde a ninguna plantilla premium (incluida la propia
        "clasica", que nunca vive en este diccionario).
    """
    if not clave:
        return None
    return PLANTILLAS_TIENDA.get(clave)
