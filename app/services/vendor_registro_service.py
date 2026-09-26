"""Registro de tiendas, ciclo de vida del subdominio (slug) y login con Google.

Extraído de vendor_service.py (bloque "Registro + Google OAuth" del
split de god-files, 2026-09-26). Cubre el alta de una tienda con
correo/contraseña o vía Google, todo el ciclo de vida del slug
(formato, disponibilidad, límites de cambio) y los lookups de tienda
por slug/email/google_id que usan la tienda pública y el resto de
rutas para resolver subdominios.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.extensions import db
from app.models import ReservedSlug, Vendor, VendorSlugHistorial
from app.services.monedas_service import detectar_moneda_por_whatsapp

# Formato del subdominio elegido por el vendedor (ver validar_formato_slug).
_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")

# Límites de seguridad del cambio de subdominio (ver `cambiar_slug`): un
# vendedor puede cambiar su slug como máximo `MAX_CAMBIOS_SLUG` veces en
# toda la vida de la tienda, con al menos `DIAS_ENTRE_CAMBIOS_SLUG` días
# entre un cambio y el siguiente. Cada vez que cambia, el slug anterior
# sigue redirigiendo automáticamente al nuevo por
# `DIAS_REDIRECCION_SLUG_ANTERIOR` días (ver `VendorSlugHistorial`).
MAX_CAMBIOS_SLUG = 2
DIAS_ENTRE_CAMBIOS_SLUG = 15
DIAS_REDIRECCION_SLUG_ANTERIOR = 30


class SlugInvalidoError(Exception):
    """El slug no cumple el formato permitido (letras minúsculas, números y guiones)."""


class SlugReservadoError(Exception):
    """El slug pedido está en la lista de palabras reservadas."""


class SlugDuplicadoError(Exception):
    """Ya existe otra tienda con ese slug."""


class EmailInvalidoError(Exception):
    """El correo no tiene un formato válido."""


class EmailDuplicadoError(Exception):
    """Ya existe una tienda registrada con ese correo."""


class LimiteCambiosSlugError(Exception):
    """El vendedor ya usó todos los cambios de subdominio permitidos."""


class CambioSlugMuyRecienteError(Exception):
    """Todavía no pasó el tiempo mínimo desde el último cambio de subdominio."""


def validar_formato_slug(slug: str) -> str:
    """Normaliza y valida el formato de un slug de subdominio.

    Reglas: 3 a 63 caracteres (límite de un label DNS), solo minúsculas,
    números y guiones, sin guion al inicio ni al final.

    Args:
        slug: Slug tal como lo escribió el vendedor.

    Returns:
        El slug normalizado (minúsculas, sin espacios).

    Raises:
        SlugInvalidoError: Si no cumple el formato.
    """
    normalizado = slug.strip().lower()
    if len(normalizado) < 3 or len(normalizado) > 63 or not _SLUG_RE.match(normalizado):
        raise SlugInvalidoError(
            "El subdominio debe tener entre 3 y 63 caracteres: solo minúsculas, "
            "números y guiones, sin empezar ni terminar en guion."
        )
    return normalizado


def slug_disponible(slug: str) -> bool:
    """Indica si un slug ya normalizado está libre para usarse.

    Además de la lista de reservados y las tiendas activas, un slug
    tampoco está disponible mientras esté funcionando como redirección
    temporal del subdominio anterior de otro vendedor (ver
    `VendorSlugHistorial` y `cambiar_slug`) — evita que alguien se
    "robe" el slug viejo de otra tienda mientras esa redirección sigue
    vigente.

    Args:
        slug: Slug ya normalizado (ver `validar_formato_slug`).

    Returns:
        True si no está reservado, en uso por otra tienda, ni
        redirigiendo temporalmente hacia otra tienda.
    """
    if ReservedSlug.query.filter_by(palabra=slug).first() is not None:
        return False
    if Vendor.query.filter_by(slug=slug).first() is not None:
        return False
    redireccion_vigente = (
        VendorSlugHistorial.query.filter_by(slug_anterior=slug)
        .filter(VendorSlugHistorial.expira_en > datetime.utcnow())
        .first()
    )
    return redireccion_vigente is None


def registrar_vendor(
    *,
    email: str,
    password: str,
    slug: str,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str | None = None,
) -> Vendor:
    """Valida y crea una tienda de vendedor nueva.

    Args:
        email: Correo del vendedor (login).
        password: Contraseña en texto plano a hashear.
        slug: Subdominio elegido, sin normalizar todavía.
        nombre_negocio: Nombre visible de la tienda.
        whatsapp_numero: Número de WhatsApp con código de país (solo dígitos).
        bio: Descripción corta opcional de la tienda.

    Returns:
        El `Vendor` recién creado (ya guardado en la base de datos), con
        `moneda` sugerida a partir del código de país de `whatsapp_numero`
        (ver `monedas_service.detectar_moneda_por_whatsapp`) — el
        vendedor puede cambiarla después desde `/vendedor/perfil`.

    Raises:
        EmailInvalidoError: Si el correo no tiene formato válido.
        EmailDuplicadoError: Si ya existe una tienda con ese correo.
        SlugInvalidoError: Si el slug no cumple el formato.
        SlugReservadoError: Si el slug está reservado.
        SlugDuplicadoError: Si el slug ya está en uso.
    """
    email_normalizado = email.strip().lower()
    if "@" not in email_normalizado or "." not in email_normalizado.split("@")[-1]:
        raise EmailInvalidoError("El correo no tiene un formato válido.")
    if Vendor.query.filter_by(email=email_normalizado).first() is not None:
        raise EmailDuplicadoError("Ya existe una tienda registrada con ese correo.")

    slug_normalizado = validar_formato_slug(slug)
    if ReservedSlug.query.filter_by(palabra=slug_normalizado).first() is not None:
        raise SlugReservadoError("Ese subdominio no está disponible.")
    if Vendor.query.filter_by(slug=slug_normalizado).first() is not None:
        raise SlugDuplicadoError("Ese subdominio ya está en uso por otra tienda.")

    whatsapp_numero_normalizado = whatsapp_numero.strip()
    vendor = Vendor(
        email=email_normalizado,
        slug=slug_normalizado,
        nombre_negocio=nombre_negocio.strip(),
        whatsapp_numero=whatsapp_numero_normalizado,
        bio=(bio or "").strip() or None,
        moneda=detectar_moneda_por_whatsapp(whatsapp_numero_normalizado),
    )
    vendor.set_password(password)
    db.session.add(vendor)
    db.session.commit()
    return vendor


def obtener_vendor_por_google_id(google_id: str) -> Vendor | None:
    """Busca una tienda por el id de cuenta de Google vinculado.

    Args:
        google_id: Claim `sub` del perfil de Google (id estable de la cuenta).

    Returns:
        El `Vendor` encontrado, o None.
    """
    return Vendor.query.filter_by(google_id=google_id).first()


def vincular_google(vendor: Vendor, google_id: str) -> None:
    """Vincula una cuenta de Google a una tienda que ya existía con correo y contraseña.

    Se llama cuando alguien inicia sesión con Google usando el mismo
    correo con el que ya se había registrado por contraseña — Google ya
    confirmó ese correo, así que de paso se marca `email_verificado`
    (por si el vendedor nunca terminó de verificarlo con el código de
    Brevo).

    Args:
        vendor: Tienda existente a vincular.
        google_id: Claim `sub` del perfil de Google.
    """
    vendor.google_id = google_id
    vendor.email_verificado = True
    db.session.commit()


def registrar_vendor_google(
    *,
    google_id: str,
    email: str,
    slug: str,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str | None = None,
) -> Vendor:
    """Crea una tienda de vendedor nueva a partir de un login con Google.

    A diferencia de `registrar_vendor`, no hay contraseña
    (`password_hash` queda en `None` — ver `Vendor.check_password`, que
    ya contempla ese caso) y `email_verificado` empieza en `True`:
    Google ya confirmó la titularidad del correo (ver
    `app/routes/vendedor.py::auth_google_callback`, que chequea
    `email_verified` antes de llegar hasta acá), así que no hace falta
    pasar por el código de verificación de
    `vendor_email_verificacion_service`.

    Args:
        google_id: Claim `sub` del perfil de Google (id estable de la cuenta).
        email: Correo ya confirmado por Google.
        slug: Subdominio elegido, sin normalizar todavía.
        nombre_negocio: Nombre visible de la tienda.
        whatsapp_numero: Número de WhatsApp con código de país.
        bio: Descripción corta opcional.

    Returns:
        El `Vendor` recién creado.

    Raises:
        EmailDuplicadoError: Si ya existe una tienda con ese correo (no
            debería pasar en el flujo normal — `auth_google_callback` ya
            intenta vincular por correo antes de llegar aquí — pero se
            revalida por si la cuenta se creó por otro medio en el
            tiempo que el vendedor tardó en completar este formulario).
        SlugInvalidoError: Si el slug no cumple el formato.
        SlugReservadoError: Si el slug está reservado.
        SlugDuplicadoError: Si el slug ya está en uso.
    """
    email_normalizado = email.strip().lower()
    if Vendor.query.filter_by(email=email_normalizado).first() is not None:
        raise EmailDuplicadoError("Ya existe una tienda registrada con ese correo.")

    slug_normalizado = validar_formato_slug(slug)
    if ReservedSlug.query.filter_by(palabra=slug_normalizado).first() is not None:
        raise SlugReservadoError("Ese subdominio no está disponible.")
    if Vendor.query.filter_by(slug=slug_normalizado).first() is not None:
        raise SlugDuplicadoError("Ese subdominio ya está en uso por otra tienda.")

    whatsapp_numero_normalizado = whatsapp_numero.strip()
    vendor = Vendor(
        email=email_normalizado,
        google_id=google_id,
        slug=slug_normalizado,
        nombre_negocio=nombre_negocio.strip(),
        whatsapp_numero=whatsapp_numero_normalizado,
        bio=(bio or "").strip() or None,
        email_verificado=True,
        moneda=detectar_moneda_por_whatsapp(whatsapp_numero_normalizado),
    )
    db.session.add(vendor)
    db.session.commit()
    return vendor


def obtener_vendor_por_slug_activo(slug: str) -> Vendor | None:
    """Busca una tienda activa por su slug, para la página pública.

    Args:
        slug: Slug del subdominio.

    Returns:
        El `Vendor` si existe y está activo, o None.
    """
    return Vendor.query.filter_by(slug=slug.lower(), activo=True).first()


def obtener_vendor_por_slug(slug: str) -> Vendor | None:
    """Busca una tienda por su slug, sin filtrar por si está activa.

    A diferencia de `obtener_vendor_por_slug_activo` (usada para
    resolver la tienda pública), esta se usa cuando justamente interesa
    saber si existe una tienda inactiva con ese slug — para mostrarle
    al visitante un aviso claro de "tienda no disponible" en vez de
    dejar que el subdominio caiga al sitio principal como si nunca
    hubiera existido.

    Args:
        slug: Slug del subdominio.

    Returns:
        El `Vendor` si existe (activo o no), o None.
    """
    return Vendor.query.filter_by(slug=slug.lower()).first()


def obtener_vendor_por_email(email: str) -> Vendor | None:
    """Busca una tienda por el correo de su dueño.

    Args:
        email: Correo del vendedor.

    Returns:
        El `Vendor` encontrado, o None.
    """
    return Vendor.query.filter_by(email=email.strip().lower()).first()


def estado_cambio_slug(vendor: Vendor) -> dict:
    """Resume la situación de un vendedor frente a los límites de `cambiar_slug`.

    Pensado para la pantalla de cambio de subdominio: cuántos cambios le
    quedan y, si ya no puede cambiar ahora mismo por el límite de
    frecuencia, desde cuándo va a poder.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        Diccionario con `cambios_usados` (int), `cambios_restantes`
        (int), `puede_cambiar_ahora` (bool), y
        `proxima_fecha_disponible` (`datetime | None`, solo tiene valor
        si el único motivo por el que no puede cambiar ahora es el
        límite de frecuencia — no si ya agotó los cambios permitidos).
    """
    cambios_usados = len(vendor.slugs_anteriores)
    cambios_restantes = max(0, MAX_CAMBIOS_SLUG - cambios_usados)
    puede_cambiar_ahora = cambios_restantes > 0
    proxima_fecha_disponible = None

    if puede_cambiar_ahora and vendor.slugs_anteriores:
        ultimo_cambio = vendor.slugs_anteriores[0].creado_en
        fecha_habilitado = ultimo_cambio + timedelta(days=DIAS_ENTRE_CAMBIOS_SLUG)
        if datetime.utcnow() < fecha_habilitado:
            puede_cambiar_ahora = False
            proxima_fecha_disponible = fecha_habilitado

    return {
        "cambios_usados": cambios_usados,
        "cambios_restantes": cambios_restantes,
        "puede_cambiar_ahora": puede_cambiar_ahora,
        "proxima_fecha_disponible": proxima_fecha_disponible,
    }


def cambiar_slug(vendor: Vendor, *, nuevo_slug: str) -> str:
    """Cambia el subdominio de una tienda, con los límites de seguridad del plan gratis.

    Reglas (ver constantes al inicio del módulo): máximo
    `MAX_CAMBIOS_SLUG` cambios en toda la vida de la tienda, mínimo
    `DIAS_ENTRE_CAMBIOS_SLUG` días desde el último cambio, y el slug
    anterior queda redirigiendo automáticamente al nuevo por
    `DIAS_REDIRECCION_SLUG_ANTERIOR` días (`VendorSlugHistorial`,
    resuelto por `subdominio_service.resolver_redireccion_slug_antiguo`)
    para no romper enlaces que el vendedor ya haya compartido.

    Los chequeos de límite (cantidad y frecuencia) van primero a
    propósito: si el vendedor ya no puede cambiar de slug, no tiene
    sentido validarle el formato del que quiera escribir.

    Args:
        vendor: Tienda que va a cambiar de subdominio.
        nuevo_slug: Subdominio nuevo, sin normalizar todavía.

    Returns:
        El slug nuevo, ya normalizado y aplicado a `vendor`.

    Raises:
        LimiteCambiosSlugError: Si ya se usaron los `MAX_CAMBIOS_SLUG`
            cambios permitidos.
        CambioSlugMuyRecienteError: Si no pasaron `DIAS_ENTRE_CAMBIOS_SLUG`
            días desde el último cambio.
        SlugInvalidoError: Si el nuevo slug no cumple el formato, o es
            igual al actual.
        SlugReservadoError: Si el nuevo slug está en la lista de reservados.
        SlugDuplicadoError: Si el nuevo slug ya está en uso por otra
            tienda, o todavía reservado por una redirección vigente.
    """
    estado = estado_cambio_slug(vendor)
    if estado["cambios_restantes"] <= 0:
        raise LimiteCambiosSlugError(
            f"Ya usaste los {MAX_CAMBIOS_SLUG} cambios de subdominio disponibles para tu tienda."
        )
    if not estado["puede_cambiar_ahora"]:
        dias_faltantes = max(1, (estado["proxima_fecha_disponible"] - datetime.utcnow()).days + 1)
        raise CambioSlugMuyRecienteError(
            f"Todavía tienes que esperar {dias_faltantes} día(s) para volver a cambiar el subdominio "
            f"(máximo un cambio cada {DIAS_ENTRE_CAMBIOS_SLUG} días)."
        )

    slug_normalizado = validar_formato_slug(nuevo_slug)
    if slug_normalizado == vendor.slug:
        raise SlugInvalidoError("El nuevo subdominio debe ser diferente al actual.")
    if ReservedSlug.query.filter_by(palabra=slug_normalizado).first() is not None:
        raise SlugReservadoError("Ese subdominio no está disponible.")
    if Vendor.query.filter_by(slug=slug_normalizado).first() is not None:
        raise SlugDuplicadoError("Ese subdominio ya está en uso por otra tienda.")
    redireccion_vigente = (
        VendorSlugHistorial.query.filter_by(slug_anterior=slug_normalizado)
        .filter(VendorSlugHistorial.expira_en > datetime.utcnow())
        .first()
    )
    if redireccion_vigente is not None:
        raise SlugDuplicadoError("Ese subdominio todavía está reservado — otra tienda lo usó recientemente.")

    slug_anterior = vendor.slug
    vendor.slug = slug_normalizado
    db.session.add(
        VendorSlugHistorial(
            vendor_id=vendor.id,
            slug_anterior=slug_anterior,
            expira_en=datetime.utcnow() + timedelta(days=DIAS_REDIRECCION_SLUG_ANTERIOR),
        )
    )
    db.session.commit()
    return slug_normalizado


