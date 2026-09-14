"""Asistente de redacción con IA para descripciones de producto y bio de tienda.

Función anotada en el roadmap ("Ideas para más adelante", 2026-09-13) y
construida el 2026-09-14: genera un primer borrador editable a partir
de los datos que el vendedor ya cargó (título/categoría del producto,
o nombre de la tienda), pensado para el vendedor que "no sabe vender
con palabras" — nunca guarda nada por sí solo, solo entrega el texto
para que el vendedor lo revise en el formulario antes de guardar.

Proveedor: Anthropic (Claude), llamado directo a su API REST de
Mensajes con `requests` (ya es una dependencia del proyecto) — se evita
agregar el SDK oficial `anthropic` como dependencia nueva solo para
esto, mismo criterio que `email_service.py` usa `smtplib` de la
librería estándar en vez de un cliente HTTP de Brevo.

⚠️ PENDIENTE (2026-09-14): Jose pidió dejar el proveedor sin decidir
todavía. Mientras `AI_API_KEY` no esté configurada (ver `.env.example`
y `config.py`), `asistente_ia_disponible()` devuelve False y las rutas
de `app/routes/vendedor.py` no muestran el botón "Escribir con IA" en
el panel — no queda ningún botón roto esperando a los vendedores. El
día que Jose cree su cuenta (ej. en console.anthropic.com) y ponga la
API key en el `.env` de producción, la función se activa sola, sin
tocar nada de este archivo.
"""
from __future__ import annotations

import requests
from flask import current_app

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_TIMEOUT_SEGUNDOS = 20
_MAX_TOKENS_RESPUESTA = 400


class AsistenteIANoDisponibleError(Exception):
    """No hay una API key de IA configurada en este entorno todavía."""


class AsistenteIAError(Exception):
    """La API de IA respondió con un error, o la conexión/respuesta falló."""


def asistente_ia_disponible() -> bool:
    """Indica si hay una API key de IA configurada en este entorno.

    Returns:
        True si `AI_API_KEY` tiene un valor no vacío en la configuración.
    """
    return bool(current_app.config.get("AI_API_KEY"))


def _llamar_claude(prompt: str) -> str:
    """Envía un prompt a la API de Mensajes de Anthropic y devuelve el texto de la respuesta.

    Args:
        prompt: Instrucción completa ya armada (incluye los datos
            disponibles y las reglas de redacción).

    Returns:
        Texto generado, recortado de espacios sobrantes.

    Raises:
        AsistenteIANoDisponibleError: Si no hay API key configurada.
        AsistenteIAError: Si la API responde con error, la conexión
            falla, o la respuesta no tiene el formato esperado.
    """
    if not asistente_ia_disponible():
        raise AsistenteIANoDisponibleError("El asistente de IA todavía no está configurado en este entorno.")

    try:
        respuesta = requests.post(
            _API_URL,
            headers={
                "x-api-key": current_app.config["AI_API_KEY"],
                "anthropic-version": _API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": current_app.config["AI_MODEL"],
                "max_tokens": _MAX_TOKENS_RESPUESTA,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=_TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
    except requests.RequestException as exc:
        raise AsistenteIAError("No se pudo contactar al asistente de IA. Intenta de nuevo en un momento.") from exc

    cuerpo = respuesta.json()
    try:
        texto = cuerpo["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AsistenteIAError("El asistente de IA devolvió una respuesta inesperada.") from exc
    return texto.strip()


def generar_descripcion_producto(*, titulo: str, categoria: str | None, borrador: str | None) -> str:
    """Genera (o mejora) la descripción pública de un producto de la tienda.

    Args:
        titulo: Título ya cargado del producto (siempre presente).
        categoria: Nombre de la categoría propia del vendedor asignada
            al producto, si tiene una — solo para dar más contexto.
        borrador: Lo que el vendedor ya haya escrito en el campo
            "Descripción" al momento de pedir ayuda, si algo. Si no
            está vacío, se le pide al modelo mejorarlo en vez de
            ignorarlo y empezar de cero.

    Returns:
        Texto de la descripción generada, listo para mostrarse en el
        textarea del formulario (el vendedor decide si lo edita y
        guarda).
    """
    instrucciones = (
        "Eres un asistente que ayuda a pequeños vendedores informales de Venezuela y "
        "Colombia (comida, ropa, artesanías, servicios) a redactar la descripción de "
        "un producto para su tienda online. Escribe en español neutro, en un tono "
        "cercano y confiable, sin tecnicismos ni palabras en inglés. Máximo 3 frases "
        "cortas, sin emojis, sin signos de exclamación excesivos, y sin inventar "
        "datos que no te dieron (precio, ingredientes, garantías, tiempos de "
        "entrega). Devuelve SOLO el texto de la descripción, sin comillas ni "
        "explicación alrededor."
    )
    datos = f'Producto: "{titulo}".'
    if categoria:
        datos += f' Categoría: "{categoria}".'
    if borrador:
        tarea = f'Mejora este borrador del vendedor, conservando su idea: "{borrador}"'
    else:
        tarea = "Escribe una descripción atractiva desde cero con estos datos."
    return _llamar_claude(f"{instrucciones}\n\n{datos}\n{tarea}")


def generar_bio_tienda(*, nombre_negocio: str, borrador: str | None) -> str:
    """Genera (o mejora) la bio corta de la tienda, en el perfil del vendedor.

    Args:
        nombre_negocio: Nombre de la tienda ya cargado (siempre presente).
        borrador: Lo que el vendedor ya haya escrito en el campo "Bio"
            al momento de pedir ayuda, si algo.

    Returns:
        Texto de la bio generada, listo para mostrarse en el textarea
        del formulario (el vendedor decide si lo edita y guarda).
    """
    instrucciones = (
        "Eres un asistente que ayuda a pequeños vendedores informales de Venezuela y "
        "Colombia a redactar la bio corta de su tienda online (se muestra debajo del "
        "logo, arriba de todo en la tienda). Español neutro, tono cercano y "
        "confiable. Máximo 2 frases cortas (menos de 200 caracteres en total), sin "
        "emojis, sin inventar datos que no te dieron. Devuelve SOLO el texto de la "
        "bio, sin comillas ni explicación alrededor."
    )
    datos = f'Nombre del negocio: "{nombre_negocio}".'
    if borrador:
        tarea = f'Mejora este borrador del vendedor, conservando su idea: "{borrador}"'
    else:
        tarea = "Escribe una bio atractiva desde cero con este dato."
    return _llamar_claude(f"{instrucciones}\n\n{datos}\n{tarea}")
