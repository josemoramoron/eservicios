"""Personalización de e-link Plus: acento, plantilla, badges, stock, categorías.

Extraído de vendor_service.py (bloque "Theming" del split de god-files,
2026-09-25). Todas las funciones siguen el mismo patrón "resolver_*":
punto único de entrada que decide el valor EFECTIVO a mostrar (siempre
gateado por `plan_plus_o_prueba_vigente`, con el valor guardado en el
Vendor/VendorProduct como respaldo aunque el plan no esté vigente).
`routes/tienda.py` (tienda pública) y `routes/vendedor.py` (panel,
selector de color) son los únicos que llaman a este módulo.
"""
from __future__ import annotations

import re

from app.models import Vendor, VendorCategoria, VendorProduct
from app.services.badges_producto_service import obtener_badge_producto
from app.services.estados_stock_service import obtener_estado_stock
from app.services.plantillas_tienda_service import obtener_plantilla_tienda
from app.services.vendor_categoria_service import listar_categorias_de_vendor
from app.services.vendor_perfil_service import plan_plus_o_prueba_vigente

# Duplicado a propósito del mismo patrón en vendor_service.py (usado ahí
# por actualizar_perfil para validar el color que el vendedor guarda) —
# es una sola línea, no vale la pena importar un símbolo privado entre
# módulos por esto.
_PATRON_COLOR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _contraste_legible(color_hex: str) -> str:
    """Elige texto casi negro o blanco según qué tan clara sea `color_hex`.

    Usa la fórmula de luminancia relativa perceptual (coeficientes
    ITU-R BT.601, sin la corrección gamma completa de la fórmula WCAG
    exacta) — suficiente para elegir entre dos opciones de contraste, no
    para certificar una razón de contraste específica.

    Args:
        color_hex: Color en formato "#rrggbb".

    Returns:
        "#111111" si `color_hex` es un color claro, "#ffffff" si es oscuro.
    """
    r = int(color_hex[1:3], 16) / 255
    g = int(color_hex[3:5], 16) / 255
    b = int(color_hex[5:7], 16) / 255
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    return "#111111" if luminancia > 0.6 else "#ffffff"


def _oscurecer_color(color_hex: str, factor: float = 0.45) -> str:
    """Oscurece un color hexadecimal, para usarlo como segundo tono de un degradado.

    Interpola cada canal RGB hacia el negro en la proporción `factor`,
    sin tocar el matiz — el mismo tono, más oscuro. Reemplaza a los
    pares de color fijos que antes vivían uno por uno en
    `estilos_portada_service` (eliminado en la unificación del
    2026-09-11): ahora el degradado del banner/avatar sale de un solo
    color de acento, no de un preset elegido aparte.

    Args:
        color_hex: Color en formato "#rrggbb".
        factor: Qué tan oscuro debe quedar (0 = igual, 1 = negro). 0.45
            por defecto — suficiente contraste con el tono original para
            que el degradado se note, sin llegar a negro puro.

    Returns:
        Color oscurecido, en formato "#rrggbb".
    """
    r = round(int(color_hex[1:3], 16) * (1 - factor))
    g = round(int(color_hex[3:5], 16) * (1 - factor))
    b = round(int(color_hex[5:7], 16) * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def resolver_acento_vendor(vendor: Vendor) -> dict[str, str]:
    """Resuelve el color de acento propio efectivo de una tienda — siempre devuelve uno.

    Punto único de entrada para el color de marca de la tienda — tanto
    la tienda pública (`routes/tienda.py`) como el panel del propio
    vendedor (`routes/vendedor.py`, vía el context processor) llaman a
    esta función en vez de leer `vendor.color_acento` directamente.

    Desde la unificación del 2026-09-11 (antes "diseño de portada y
    avatar" y "color de acento propio" eran dos mecanismos separados —
    ver el viejo `estilos_portada_service`, eliminado), este color hace
    dos trabajos a la vez: el acento plano (`color`/`contraste`, en
    botones/precios/fondo) y el degradado del banner/avatar de respaldo
    (`color` a `gradiente_fin`) mientras el vendedor no suba su propio
    logo/portada. Y, a diferencia de la versión anterior de esta
    función, YA NO devuelve `None`: el plan Plus ya no decide si hay
    acento o no, sino QUÉ colores están permitidos (ver
    `listar_paleta_acento`) — con el plan gratis, entre el azul de
    eServicios y un rosado fijo; con Plus, entre una paleta más amplia o
    cualquier color personalizado.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        Diccionario con `color` (el hex efectivo, nunca vacío),
        `contraste` (blanco o casi negro, legible sobre `color`) y
        `gradiente_fin` (una versión oscurecida de `color` — el propio
        `color` es el otro extremo del degradado).
    """
    color = vendor.color_acento
    if color and _PATRON_COLOR_HEX.match(color):
        if not plan_plus_o_prueba_vigente(vendor) and color.lower() not in {c.lower() for c in PALETA_ACENTO_GRATIS}:
            # Color exclusivo de Plus (cuenta la prueba gratuita, ver
            # plan_plus_o_prueba_vigente), guardado cuando el plan
            # estaba vigente — ahora vencido, cae de vuelta al
            # azul/rosado gratis hasta que el vendedor vuelva a Plus (el
            # valor sigue guardado en la base, no se pierde: ver
            # actualizar_perfil).
            color = None
    else:
        color = None
    color = color or COLOR_ACENTO_POR_DEFECTO
    return {
        "color": color,
        "contraste": _contraste_legible(color),
        "gradiente_fin": _oscurecer_color(color),
    }


def resolver_cupon_vendor(vendor: Vendor) -> str | None:
    """Resuelve el cupón/código de descuento efectivo de una tienda, si aplica.

    Punto único de entrada para la función Plus del punto 16 del roadmap
    — `routes/tienda.py` la usa en vez de leer `vendor.cupon` directo,
    para que el chequeo de plan nunca se le olvide. Mismo patrón que
    `resolver_acento_vendor`: no es un sistema de descuentos, solo
    decide si el texto que el vendedor guardó se muestra ahora mismo.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        None cuando la tienda no tiene ningún cupón guardado, o cuando
        no tiene Plus (real o de prueba) vigente ahora mismo (ver
        `plan_plus_o_prueba_vigente`) — en ese caso el texto puede
        seguir guardado en `vendor.cupon`, listo para reactivarse solo
        con volver a Plus. Si aplica, el texto del cupón tal cual el
        vendedor lo escribió.
    """
    if not vendor.cupon or not plan_plus_o_prueba_vigente(vendor):
        return None
    return vendor.cupon


# Azul de marca de eServicios — el acento por defecto de cualquier
# tienda que no eligió ningún color propio (ver resolver_acento_vendor),
# y el mismo valor que --color-accent trae de fábrica en style.css.
COLOR_ACENTO_POR_DEFECTO = "#2563eb"

# Paleta curada de colores de acento — atajo de un clic en
# /vendedor/perfil (círculos), inspirada en el mismo mockup aprobado por
# Jose para las plantillas del punto 13. Dos niveles, unificados en un
# solo mecanismo (ver resolver_acento_vendor): el plan gratis solo
# puede usar PALETA_ACENTO_GRATIS (el azul de siempre + un rosado fijo);
# el plan Plus además desbloquea PALETA_ACENTO_PLUS completa y el
# selector de color nativo (`<input type="color">`) para cualquier hex.
PALETA_ACENTO_GRATIS: list[str] = [
    COLOR_ACENTO_POR_DEFECTO,  # azul (el de siempre)
    "#ec4899",  # rosado
]

PALETA_ACENTO_PLUS: list[str] = PALETA_ACENTO_GRATIS + [
    "#e11d48",  # rosa fuerte/rojo
    "#059669",  # verde esmeralda
    "#7c3aed",  # violeta
    "#ea580c",  # naranja
    "#0f172a",  # grafito casi negro
    "#78350f",  # marrón
]
# Nota (2026-09-11): Jose pidió quitar 2 de los 10 círculos originales —
# "vinotinto" (#7f1d1d, antepenúltimo) y "fucsia" (#c026d3, el último de
# la derecha) — dejando 8. No hace falta ninguna migración ni afecta a un
# vendedor que ya haya guardado alguno de estos 2 colores como su
# `color_acento`: `resolver_acento_vendor` solo valida el formato hex para
# planes Plus (el selector de color personalizado siempre permitió
# cualquier hex, no solo los de esta lista curada) — el cambio es
# puramente sobre qué círculos de acceso rápido se muestran en
# `/vendedor/perfil`.


def listar_paleta_acento(plan_plus_activo: bool) -> list[str]:
    """Devuelve la paleta curada de colores de acento disponible para el plan del vendedor.

    Args:
        plan_plus_activo: Si la tienda tiene Plus vigente ahora mismo,
            real o de prueba (ver `plan_plus_o_prueba_vigente`).

    Returns:
        `PALETA_ACENTO_PLUS` (10 colores) si `plan_plus_activo`,
        `PALETA_ACENTO_GRATIS` (2 colores: azul y rosado) en caso
        contrario — en el orden en que deben mostrarse los círculos en
        `/vendedor/perfil`, todos en una sola fila.
    """
    return list(PALETA_ACENTO_PLUS if plan_plus_activo else PALETA_ACENTO_GRATIS)


PLANTILLA_POR_DEFECTO = "clasica"


def resolver_plantilla_vendor(vendor: Vendor) -> str:
    """Resuelve la plantilla visual efectiva de la tienda pública de un vendedor.

    Punto único de entrada para la función Plus del punto 13 del roadmap
    (plantillas prediseñadas) — `routes/tienda.py` la usa para decidir
    qué archivo de template renderizar. Igual que `resolver_acento_vendor`,
    siempre devuelve un valor (nunca None): toda tienda tiene que
    renderizarse con alguna plantilla, y "clasica" es la que ya existía
    antes de esta función, gratis para todos.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        `"clasica"` cuando la tienda no eligió ninguna plantilla premium,
        cuando la clave guardada ya no es válida, o cuando no tiene Plus
        (real o de prueba) vigente ahora mismo (ver
        `plan_plus_o_prueba_vigente`) — en ese último caso el valor
        sigue guardado en `vendor.plantilla`, listo para reactivarse
        solo con volver a Plus. Si todo lo anterior aplica, la clave
        guardada tal cual (ej. `"editorial"`).
    """
    if not vendor.plantilla or not plan_plus_o_prueba_vigente(vendor):
        return PLANTILLA_POR_DEFECTO
    if obtener_plantilla_tienda(vendor.plantilla) is None:
        return PLANTILLA_POR_DEFECTO
    return vendor.plantilla


def resolver_badge_producto(vendor: Vendor, producto: VendorProduct) -> dict[str, str] | None:
    """Resuelve el badge efectivo de un producto ("Más vendido", "Oferta", "Nuevo"), si aplica.

    Punto único de entrada para la función Plus del punto 14 del roadmap
    — `routes/tienda.py` la usa para decidir si pinta un badge sobre la
    tarjeta del producto en la tienda pública, en vez de leer
    `producto.badge` directamente.

    Args:
        vendor: Tienda dueña del producto (para chequear su plan).
        producto: Producto a evaluar.

    Returns:
        None cuando el producto no tiene badge guardado, cuando la
        tienda no tiene Plus (real o de prueba) vigente ahora mismo (ver
        `plan_plus_o_prueba_vigente`), o cuando la clave guardada ya no
        es válida — en cualquiera de esos casos el valor puede seguir
        guardado en `producto.badge`, listo para reactivarse solo con
        volver a Plus. Si aplica, un diccionario con `clave` y `nombre`
        (ver `badges_producto_service.obtener_badge_producto`).
    """
    if not producto.badge or not plan_plus_o_prueba_vigente(vendor):
        return None
    return obtener_badge_producto(producto.badge)


def resolver_disponibilidad_vendor(vendor: Vendor) -> bool | None:
    """Resuelve si debe mostrarse el indicador "Disponible ahora" / "Fuera de horario".

    Punto único de entrada para la función Plus del punto 15 del roadmap
    — un interruptor manual (`Vendor.disponible_ahora`, sin horarios ni
    zona horaria calculados) que el vendedor prende/apaga desde
    `/vendedor/perfil`.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        None cuando la tienda no tiene Plus (real o de prueba) vigente
        ahora mismo (ver `plan_plus_o_prueba_vigente`) — en ese caso la
        tienda pública no debe mostrar ningún indicador, aunque
        `vendor.disponible_ahora` siga guardado. Si Plus está vigente,
        `True` o `False` según el interruptor guardado.
    """
    if not plan_plus_o_prueba_vigente(vendor):
        return None
    return vendor.disponible_ahora


def resolver_estado_stock_producto(vendor: Vendor, producto: VendorProduct) -> dict[str, str] | None:
    """Resuelve el estado de stock efectivo de un producto ("Pocas unidades", "Agotado"), si aplica.

    Punto único de entrada para la función Plus del punto 17 del roadmap
    — `routes/tienda.py` la usa para decidir si muestra el indicador de
    stock (y si ofrece el mini-formulario "avísame cuando vuelva") en la
    tienda pública, en vez de leer `producto.estado_stock` directamente.
    Mismo criterio que `resolver_badge_producto`.

    Args:
        vendor: Tienda dueña del producto (para chequear su plan).
        producto: Producto a evaluar.

    Returns:
        None cuando el producto está en stock normal, cuando la tienda
        no tiene Plus (real o de prueba) vigente ahora mismo (ver
        `plan_plus_o_prueba_vigente`), o cuando la clave guardada ya no
        es válida — en cualquiera de esos casos el valor puede seguir
        guardado en `producto.estado_stock`, listo para reactivarse solo
        con volver a Plus. Si aplica, un diccionario con `clave` y
        `nombre` (ver `estados_stock_service.obtener_estado_stock`).
    """
    if not producto.estado_stock or not plan_plus_o_prueba_vigente(vendor):
        return None
    return obtener_estado_stock(producto.estado_stock)


def resolver_categorias_producto(vendor: Vendor) -> list[VendorCategoria]:
    """Resuelve las categorías que deben ofrecerse como filtro en la tienda pública.

    Punto único de entrada para la función Plus del punto 18 del roadmap
    — igual que `resolver_badge_producto`/`resolver_estado_stock_producto`,
    las categorías se guardan siempre pero solo se aplican (acá, se
    muestran como filtro) mientras el plan Plus esté vigente.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        Lista vacía cuando la tienda no tiene Plus (real o de prueba)
        vigente ahora mismo (ver `plan_plus_o_prueba_vigente`) — en ese
        caso la tienda pública no debe mostrar el filtro de categorías,
        aunque sigan guardadas. Si Plus está vigente, todas las
        categorías de la tienda (ver `listar_categorias_de_vendor`).
    """
    if not plan_plus_o_prueba_vigente(vendor):
        return []
    return listar_categorias_de_vendor(vendor)


