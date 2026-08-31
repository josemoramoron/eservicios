"""Estados manuales de stock ("Pocas unidades", "Agotado") — contador de urgencia.

Función de e-link Plus (roadmap, Fase 2, punto 17) — un estado de stock
es un aviso manual de 3 niveles (Normal / Pocas unidades / Agotado), sin
conteo numérico exacto: el vendedor lo cambia a mano desde el formulario
de producto, igual que `disponible_ahora` en el perfil. Mismo criterio
de conjunto cerrado que `badges_producto_service.py`: el vendedor elige
entre opciones curadas, no texto libre, y "Normal" no vive como clave
propia (None/ausente = Normal, mismo criterio que "sin badge" en
`BADGES_PRODUCTO`).

`vendor_service.resolver_estado_stock_producto()` es quien de verdad
gatea esto contra el plan Plus del vendedor — este servicio solo conoce
los estados disponibles, no decide si un vendedor puede usarlos.
"""
from __future__ import annotations

ESTADOS_STOCK: dict[str, dict[str, str]] = {
    "pocas_unidades": {"nombre": "Pocas unidades"},
    "agotado": {"nombre": "Agotado"},
}


def listar_estados_stock() -> list[dict[str, str]]:
    """Devuelve los estados de stock disponibles, con su clave incluida.

    Returns:
        Lista de dicts `{"clave", "nombre"}`, en el orden en que deben
        mostrarse las opciones en el formulario de producto.
    """
    return [{"clave": clave, **datos} for clave, datos in ESTADOS_STOCK.items()]


def obtener_estado_stock(clave: str | None) -> dict[str, str] | None:
    """Busca un estado de stock por su clave.

    Args:
        clave: Clave del estado (ej. "agotado"), o vacío/None.

    Returns:
        El dict del estado (con su propia `clave` incluida, para que el
        template arme la clase CSS `tienda-estado-stock--<clave>` sin
        necesitar lógica adicional), o None si `clave` está vacía o no
        corresponde a ningún estado (es decir, "Normal").
    """
    if not clave or clave not in ESTADOS_STOCK:
        return None
    return {"clave": clave, **ESTADOS_STOCK[clave]}
