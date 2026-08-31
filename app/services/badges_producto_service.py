"""Badges opcionales de producto ("Más vendido", "Oferta", "Nuevo").

Función de e-link Plus (roadmap, Fase 2, punto 14) — un badge es una
etiqueta corta que resalta un producto puntual en la tienda pública, no
un estado del producto (`VendorProduct.activo` ya cubre eso). Mismo
criterio de conjunto cerrado que `plantillas_tienda_service.py` y
`estilos_portada_service.py`: el vendedor elige entre opciones curadas,
no texto libre — así el color de cada badge se puede fijar por CSS
(`.tienda-badge-producto--<clave>`, ver `app/static/css/tienda.css`) sin
depender de nada que el vendedor escriba.

`vendor_service.resolver_badge_producto()` es quien de verdad gatea esto
contra el plan Plus del vendedor — este servicio solo conoce los badges
disponibles, no decide si un vendedor puede usarlos.
"""
from __future__ import annotations

BADGES_PRODUCTO: dict[str, dict[str, str]] = {
    "mas_vendido": {"nombre": "Más vendido"},
    "oferta": {"nombre": "Oferta"},
    "nuevo": {"nombre": "Nuevo"},
}


def listar_badges_producto() -> list[dict[str, str]]:
    """Devuelve los badges disponibles, con su clave incluida.

    Returns:
        Lista de dicts `{"clave", "nombre"}`, en el orden en que deben
        mostrarse las opciones en el formulario de producto.
    """
    return [{"clave": clave, **datos} for clave, datos in BADGES_PRODUCTO.items()]


def obtener_badge_producto(clave: str | None) -> dict[str, str] | None:
    """Busca un badge por su clave.

    Args:
        clave: Clave del badge (ej. "oferta"), o vacío/None.

    Returns:
        El dict del badge (con su propia `clave` incluida, para que el
        template arme la clase CSS `tienda-badge-producto--<clave>` sin
        necesitar lógica adicional), o None si `clave` está vacía o no
        corresponde a ningún badge.
    """
    if not clave or clave not in BADGES_PRODUCTO:
        return None
    return {"clave": clave, **BADGES_PRODUCTO[clave]}
