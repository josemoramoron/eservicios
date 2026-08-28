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
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


class EnvioCorreoError(Exception):
    """El correo no pudo enviarse (credenciales inválidas, SMTP caído, etc.)."""


def enviar_correo(destinatario: str, asunto: str, cuerpo_texto: str) -> None:
    """Envía un correo de texto plano vía el relay SMTP de Brevo.

    Args:
        destinatario: Email del destinatario.
        asunto: Asunto del correo.
        cuerpo_texto: Cuerpo del mensaje, en texto plano.

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
