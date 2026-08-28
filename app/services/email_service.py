"""Envío de correos transaccionales vía Brevo (relay SMTP).

Usa `smtplib`/`email` de la librería estándar en vez del SDK o la API
HTTP de Brevo, específicamente para no añadir una dependencia nueva a
`requirements.txt` — Brevo también soporta un relay SMTP normal
(`smtp-relay.brevo.com:587`), así que no hace falta más que eso.

Por ahora el único correo que manda eServicios es el código de
verificación del vendedor (ver `vendor_email_verificacion_service.py`),
pero este módulo queda genérico por si aparecen más casos de uso
(recuperar contraseña, notificaciones, etc.) — ver
`claude/spec-tiendas-vendedor.md` en el proyecto.

Plantillas de correo: se renderizan con `renderizar_plantilla_correo()`,
que usa `current_app.jinja_env.get_template()` en vez del `render_template()`
normal de Flask — a propósito, según la "Regla sobre contexto de petición"
de `.clinerules`: el envío de correo transaccional es uno de los casos
señalados ahí como candidato a correr algún día fuera de una petición
HTTP (un hilo, una cola), y `render_template()` ejecuta los context
processors de la app (que dependen de `session`/`request` activos) —
`get_template().render()` no, así que esta función funciona igual hoy
(llamada desde una ruta) que el día que el envío se mueva a background.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app

# Paleta de correo: espeja el bloque claro de `:root` en
# app/static/css/style.css. Los clientes de correo (sobre todo Outlook
# de escritorio) no soportan variables CSS ni siempre respetan
# `prefers-color-scheme`, así que los valores van fijos en Python UNA
# sola vez acá — nunca sueltos/repetidos dentro de una plantilla de
# correo — y toda plantilla nueva los recibe ya inyectados por
# `renderizar_plantilla_correo()`. Si la paleta de `style.css` cambia,
# actualizar también aquí.
_COLOR_BG = "#ffffff"
_COLOR_SURFACE = "#f5f7fa"
_COLOR_TEXT = "#111111"
_COLOR_TEXT_MUTED = "#5a5a5a"
_COLOR_BORDER = "#e2e5ea"
_COLOR_ACCENT = "#2563eb"


class EnvioCorreoError(Exception):
    """El correo no pudo enviarse (credenciales inválidas, SMTP caído, etc.)."""


def renderizar_plantilla_correo(nombre_plantilla: str, **contexto) -> str:
    """Renderiza una plantilla HTML de correo con la paleta de marca ya inyectada.

    Usa `current_app.jinja_env.get_template()` en vez de
    `flask.render_template()` para no depender de una petición HTTP
    activa (ver docstring del módulo). Toda plantilla en
    `app/templates/email/` recibe automáticamente `color_bg`,
    `color_surface`, `color_text`, `color_text_muted`, `color_border` y
    `color_accent` — no hay que pasarlos a mano ni repetirlos en cada
    plantilla nueva.

    Args:
        nombre_plantilla: Ruta relativa a `app/templates/`, ej.
            `"email/verificacion_codigo.html"`.
        **contexto: Variables propias de esa plantilla (ej. `codigo`,
            `nombre_negocio`).

    Returns:
        El HTML ya renderizado, listo para pasar como `cuerpo_html` a
        `enviar_correo()`.
    """
    plantilla = current_app.jinja_env.get_template(nombre_plantilla)
    return plantilla.render(
        color_bg=_COLOR_BG,
        color_surface=_COLOR_SURFACE,
        color_text=_COLOR_TEXT,
        color_text_muted=_COLOR_TEXT_MUTED,
        color_border=_COLOR_BORDER,
        color_accent=_COLOR_ACCENT,
        **contexto,
    )


def enviar_correo(
    destinatario: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str | None = None,
) -> None:
    """Envía un correo vía el relay SMTP de Brevo.

    Args:
        destinatario: Email del destinatario.
        asunto: Asunto del correo.
        cuerpo_texto: Cuerpo del mensaje, en texto plano — siempre
            requerido como respaldo (algunos clientes de correo o
            lectores de pantalla lo prefieren, y sirve si `cuerpo_html`
            falla al renderizar en el cliente del destinatario).
        cuerpo_html: Cuerpo alternativo en HTML, ya renderizado (ver
            `renderizar_plantilla_correo()`). Si se pasa, el correo se
            manda como `multipart/alternative` con ambas versiones; si
            se omite, el correo va solo en texto plano.

    Raises:
        EnvioCorreoError: Si el envío falla por cualquier motivo (SMTP
            caído, credenciales inválidas, etc.). El detalle técnico
            queda en el log; el mensaje de la excepción es apto para
            mostrárselo al usuario.
    """
    config = current_app.config
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = config["BREVO_REMITENTE"]
    mensaje["To"] = destinatario
    mensaje.set_content(cuerpo_texto)
    if cuerpo_html:
        mensaje.add_alternative(cuerpo_html, subtype="html")

    try:
        with smtplib.SMTP(config["BREVO_SMTP_HOST"], config["BREVO_SMTP_PORT"], timeout=10) as servidor:
            servidor.starttls()
            servidor.login(config["BREVO_SMTP_LOGIN"], config["BREVO_SMTP_PASSWORD"])
            servidor.send_message(mensaje)
    except (smtplib.SMTPException, OSError) as error:
        current_app.logger.error("Fallo al enviar correo a %s: %s", destinatario, error)
        raise EnvioCorreoError(
            "No se pudo enviar el correo. Intenta de nuevo en un momento."
        ) from error
