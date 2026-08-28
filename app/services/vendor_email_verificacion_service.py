"""Verificación del correo del vendedor mediante código de 6 dígitos.

Flujo: al registrarse (o al hacer login sin haber verificado todavía),
se genera un código y se manda por correo vía Brevo (`email_service`).
El vendedor lo escribe en `/vendedor/verificar-email`; mientras
`Vendor.email_verificado` sea False no tiene sesión completa — ver el
uso de `session["vendor_pendiente_id"]` en `routes/vendedor.py`.

El código expira a los `MINUTOS_VALIDEZ_CODIGO` minutos y hay un
enfriamiento mínimo (`SEGUNDOS_ENTRE_REENVIOS`) entre reenvíos, para no
poder golpear el relay de Brevo a repetición.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Vendor
from app.services.email_service import enviar_correo

LONGITUD_CODIGO = 6
MINUTOS_VALIDEZ_CODIGO = 15
SEGUNDOS_ENTRE_REENVIOS = 60


class ReenvioMuyProntoError(Exception):
    """Se pidió un código nuevo antes de que pase el enfriamiento mínimo."""


def generar_y_enviar_codigo(vendor: Vendor) -> None:
    """Genera un código de verificación nuevo, lo guarda y lo envía por correo.

    Siempre genera uno nuevo, sin importar si ya había uno vigente —
    para eso está `asegurar_codigo_vigente`, que sí respeta uno
    existente.

    Args:
        vendor: Vendedor a verificar.
    """
    codigo = f"{secrets.randbelow(10 ** LONGITUD_CODIGO):0{LONGITUD_CODIGO}d}"
    vendor.codigo_verificacion_email = codigo
    vendor.codigo_verificacion_expira_en = datetime.utcnow() + timedelta(minutes=MINUTOS_VALIDEZ_CODIGO)
    db.session.commit()

    enviar_correo(
        destinatario=vendor.email,
        asunto="Tu código de verificación — eServicios",
        cuerpo_texto=(
            f"Hola {vendor.nombre_negocio},\n\n"
            f"Tu código de verificación es: {codigo}\n\n"
            f"Vence en {MINUTOS_VALIDEZ_CODIGO} minutos. Si tú no creaste esta "
            "cuenta en eServicios, puedes ignorar este correo.\n"
        ),
    )


def asegurar_codigo_vigente(vendor: Vendor) -> None:
    """Genera y envía un código nuevo solo si no hay uno vigente todavía.

    Pensado para el login: si el vendedor ya tiene un código sin usar y
    sin expirar (por ejemplo, cerró la pestaña de verificación y volvió
    a entrar), no le manda uno nuevo — puede seguir usando el mismo.

    Args:
        vendor: Vendedor a verificar.
    """
    sin_codigo_vigente = (
        vendor.codigo_verificacion_expira_en is None
        or datetime.utcnow() > vendor.codigo_verificacion_expira_en
    )
    if sin_codigo_vigente:
        generar_y_enviar_codigo(vendor)


def reenviar_codigo(vendor: Vendor) -> None:
    """Reenvía el código de verificación, respetando el enfriamiento mínimo.

    Args:
        vendor: Vendedor a verificar.

    Raises:
        ReenvioMuyProntoError: Si todavía no pasa `SEGUNDOS_ENTRE_REENVIOS`
            desde el último envío.
    """
    if vendor.codigo_verificacion_expira_en is not None:
        enviado_en = vendor.codigo_verificacion_expira_en - timedelta(minutes=MINUTOS_VALIDEZ_CODIGO)
        segundos_transcurridos = (datetime.utcnow() - enviado_en).total_seconds()
        if segundos_transcurridos < SEGUNDOS_ENTRE_REENVIOS:
            raise ReenvioMuyProntoError("Espera un momento antes de pedir otro código.")
    generar_y_enviar_codigo(vendor)


def verificar_codigo(vendor: Vendor, codigo: str) -> bool:
    """Valida el código ingresado y, si es correcto, marca el correo como verificado.

    Args:
        vendor: Vendedor a verificar.
        codigo: Código de 6 dígitos ingresado por el usuario.

    Returns:
        True si el código es correcto y no había expirado (en cuyo caso
        ya quedó marcado `email_verificado=True` y el código se borró);
        False en cualquier otro caso.
    """
    if not vendor.codigo_verificacion_email or not vendor.codigo_verificacion_expira_en:
        return False
    if datetime.utcnow() > vendor.codigo_verificacion_expira_en:
        return False
    if not secrets.compare_digest(codigo.strip(), vendor.codigo_verificacion_email):
        return False

    vendor.email_verificado = True
    vendor.codigo_verificacion_email = None
    vendor.codigo_verificacion_expira_en = None
    db.session.commit()
    return True
