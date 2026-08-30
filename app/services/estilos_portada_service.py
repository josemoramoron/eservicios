"""Presets curados de color para el banner/avatar de respaldo de la tienda pública.

Le da al vendedor una tercera opción, además de dejarlo en blanco (usa
el acento compartido — ver `--color-accent` en `tienda.css`) o subir su
propia foto: elegir uno de estos diseños ya armados con un clic, sin
tener que diseñar ni subir nada. Ver `claude/roadmap-monetizacion-e-link.md`,
Fase 1, punto 26.

Deliberadamente NO reutiliza `--color-accent`: esa variable queda
reservada para el futuro color de acento propio de "e-link Plus" (Fase
2, punto 12 del roadmap) — mezclar ambos mecanismos haría que elegir un
preset acá y el acento de Plus más adelante se pisaran entre sí. En su
lugar, `tienda.css` referencia `--color-portada-inicio`/`--color-portada-fin`/
`--color-portada-contraste` con un valor de respaldo que cae de vuelta
al acento compartido cuando el vendedor no eligió ningún preset — así
ninguna tienda existente cambia de aspecto por accidente.
"""
from __future__ import annotations

PRESETS_PORTADA: dict[str, dict[str, str]] = {
    "oceano": {"nombre": "Océano", "color_inicio": "#0284c7", "color_fin": "#0c4a6e"},
    "atardecer": {"nombre": "Atardecer", "color_inicio": "#ea580c", "color_fin": "#9d174d"},
    "bosque": {"nombre": "Bosque", "color_inicio": "#15803d", "color_fin": "#14532d"},
    "uva": {"nombre": "Uva", "color_inicio": "#7e22ce", "color_fin": "#4c1d95"},
    "fuego": {"nombre": "Fuego", "color_inicio": "#b91c1c", "color_fin": "#7c2d12"},
    "grafito": {"nombre": "Grafito", "color_inicio": "#334155", "color_fin": "#0f172a"},
    "dorado": {"nombre": "Dorado", "color_inicio": "#b45309", "color_fin": "#78350f"},
    "coral": {"nombre": "Coral", "color_inicio": "#be123c", "color_fin": "#831843"},
}


def listar_presets_portada() -> list[dict[str, str]]:
    """Devuelve los presets disponibles, con su clave incluida, en orden fijo.

    Returns:
        Lista de dicts `{"clave", "nombre", "color_inicio", "color_fin"}`,
        listos para pintar la galería de `/vendedor/perfil`.
    """
    return [{"clave": clave, **datos} for clave, datos in PRESETS_PORTADA.items()]


def obtener_preset_portada(clave: str | None) -> dict[str, str] | None:
    """Busca un preset por su clave.

    Args:
        clave: Clave del preset (ej. "oceano"), o vacío/None.

    Returns:
        El dict del preset, o None si `clave` está vacía o no existe
        ninguno con ese nombre. Nunca lanza error — un valor viejo o
        inválido guardado en `Vendor.estilo_portada` simplemente cae de
        vuelta al placeholder genérico (acento compartido).
    """
    if not clave:
        return None
    return PRESETS_PORTADA.get(clave)
