"""Lógica de negocio de las tiendas de vendedor (registro, slug, productos, perfil).

Incluye la validación y disponibilidad del subdominio elegido por el
vendedor, el CRUD que usa el panel `/vendedor`, la actualización del
perfil (personalización + seguridad) y los helpers para armar los
links `wa.me` (WhatsApp) que se muestran en la tienda pública. La
subida de imágenes a Cloudflare R2 vive en `r2_service.py` — este
módulo solo recibe URLs ya resueltas y las guarda en el modelo. Ver
`claude/spec-tiendas-vendedor.md` en el proyecto para el diseño completo.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from sqlalchemy import func

from app.extensions import db
from app.models import PlanVendor, ReservedSlug, Vendor, VendorLink, VendorProduct, VendorSlugHistorial
from app.services.estilos_portada_service import PRESETS_PORTADA
from app.services.plantillas_tienda_service import PLANTILLAS_TIENDA, obtener_plantilla_tienda

# Formato exigido para Vendor.color_acento — "#" + 6 dígitos hexadecimales,
# el mismo formato que produce un <input type="color"> nativo del navegador
# (ver vendedor/perfil.html). Cualquier otro valor se ignora en silencio,
# mismo criterio que ya se usa con estilo_portada en actualizar_perfil().
_PATRON_COLOR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")

MAX_FOTOS_PRODUCTO = 5

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


class PerfilInvalidoError(Exception):
    """Los datos de personalización de la tienda no son válidos."""


class PasswordActualIncorrectaError(Exception):
    """La contraseña actual ingresada no coincide con la guardada."""


class PasswordNuevaInvalidaError(Exception):
    """La contraseña nueva no cumple los requisitos mínimos."""


class LinkInvalidoError(Exception):
    """El título o la URL del enlace no son válidos."""


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
        El `Vendor` recién creado (ya guardado en la base de datos).

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

    vendor = Vendor(
        email=email_normalizado,
        slug=slug_normalizado,
        nombre_negocio=nombre_negocio.strip(),
        whatsapp_numero=whatsapp_numero.strip(),
        bio=(bio or "").strip() or None,
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

    vendor = Vendor(
        email=email_normalizado,
        google_id=google_id,
        slug=slug_normalizado,
        nombre_negocio=nombre_negocio.strip(),
        whatsapp_numero=whatsapp_numero.strip(),
        bio=(bio or "").strip() or None,
        email_verificado=True,
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


def actualizar_perfil(
    vendor: Vendor,
    *,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str,
    logo_url: str | None,
    banner_url: str | None,
    estilo_portada: str | None = None,
    color_acento: str | None = None,
    plantilla: str | None = None,
) -> None:
    """Actualiza los datos de personalización de la tienda del vendedor.

    El slug y el correo NO se editan aquí a propósito: el slug es el
    subdominio público (cambiarlo rompería enlaces ya compartidos) y el
    correo es la credencial de acceso — ambos quedan fuera de alcance
    de esta primera versión del perfil.

    Args:
        vendor: Tienda a actualizar.
        nombre_negocio: Nuevo nombre visible de la tienda.
        whatsapp_numero: Nuevo número de WhatsApp (con código de país).
        bio: Nueva descripción corta (puede quedar vacía).
        logo_url: URL del logo ya subido a R2, o None para quitarlo.
        banner_url: URL del banner ya subido a R2, o None para quitarlo.
        estilo_portada: Clave de un preset de `estilos_portada_service`
            (ej. "oceano"), o vacío/None para usar el placeholder
            genérico. Un valor que no exista en `PRESETS_PORTADA` se
            ignora en silencio (queda en None) en vez de lanzar error —
            es un `<select>`/radio cerrado, no texto libre del usuario.
        color_acento: Valor FINAL a guardar como color de acento propio
            ("#rrggbb", función de e-link Plus — ver
            `resolver_acento_vendor`), o None para dejarlo sin color
            propio. A diferencia de los demás parámetros, esto no
            representa "el campo tal como llegó del formulario" — es
            responsabilidad del llamador resolver antes de llamar aquí
            si el vendedor pidió quitar el color, escribió uno nuevo, o
            el formulario ni siquiera incluía el selector (por no tener
            Plus vigente), en cuyo caso el llamador debe pasar el valor
            que ya tenía `vendor.color_acento` para no perderlo (ver
            `vendedor.perfil`). Un valor que no cumpla el formato se
            ignora en silencio (queda en None) en vez de lanzar error —
            no debería ocurrir nunca desde un `<input type="color">`
            nativo, pero se valida igual por si llega manipulado. Este
            parámetro NO valida que el vendedor tenga Plus vigente —
            se guarda igual aunque el plan no esté vigente, para no
            perder la elección si el vendedor vuelve a Plus más adelante.
        plantilla: Clave de una plantilla de `plantillas_tienda_service`
            (ej. "editorial"), o vacío/None para la plantilla "Clásica".
            Mismo trato que `estilo_portada`: un valor que no exista en
            `PLANTILLAS_TIENDA` se ignora en silencio (queda en None) en
            vez de lanzar error. Tampoco valida el plan Plus aquí —esa
            función de e-link Plus se gatea en tiempo de render (ver
            `resolver_plantilla_vendor`), no al guardar.

    Raises:
        PerfilInvalidoError: Si el nombre o el WhatsApp quedan vacíos.
    """
    nombre_negocio = nombre_negocio.strip()
    whatsapp_numero = whatsapp_numero.strip()
    if not nombre_negocio:
        raise PerfilInvalidoError("El nombre de la tienda es obligatorio.")
    if not whatsapp_numero:
        raise PerfilInvalidoError("El número de WhatsApp es obligatorio.")

    if estilo_portada and estilo_portada not in PRESETS_PORTADA:
        estilo_portada = None
    if plantilla and plantilla not in PLANTILLAS_TIENDA:
        plantilla = None

    vendor.nombre_negocio = nombre_negocio
    vendor.whatsapp_numero = whatsapp_numero
    vendor.bio = bio.strip() or None
    vendor.logo_url = logo_url
    vendor.banner_url = banner_url
    vendor.estilo_portada = estilo_portada or None
    vendor.color_acento = color_acento if (color_acento and _PATRON_COLOR_HEX.match(color_acento)) else None
    vendor.plantilla = plantilla or None
    db.session.commit()


def plan_plus_vigente(vendor: Vendor) -> bool:
    """Indica si la tienda tiene el plan Plus activo y no vencido en este momento.

    Chequeo mínimo de plan del roadmap (Fase 3, punto 22), usado como
    condición para las funciones exclusivas de Plus (por ahora, el color
    de acento propio del punto 12).

    Args:
        vendor: Tienda a evaluar.

    Returns:
        True si `vendor.plan` es `PlanVendor.PLUS` y, cuando tiene una
        fecha de vencimiento (`plan_expira_en`), esa fecha todavía no
        pasó. Un `plan_expira_en` en None junto con plan Plus se
        considera vigente sin límite de tiempo (caso especial — el alta
        manual de admin, `vendor_admin_service.cambiar_plan_vendor`,
        siempre fija una fecha, así que este caso no ocurre desde ahí).
    """
    if vendor.plan != PlanVendor.PLUS:
        return False
    if vendor.plan_expira_en is None:
        return True
    return vendor.plan_expira_en > datetime.utcnow()


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


def resolver_acento_vendor(vendor: Vendor) -> dict[str, str] | None:
    """Resuelve el color de acento propio efectivo de una tienda, si aplica.

    Punto único de entrada para la función Plus del punto 12 del roadmap
    — tanto la tienda pública (`routes/tienda.py`) como el panel del
    propio vendedor (`routes/vendedor.py`, vía el context processor)
    llaman a esta función en vez de leer `vendor.color_acento`
    directamente, para que el chequeo de plan nunca se les olvide.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        None cuando la tienda no tiene un color de acento propio
        guardado, o cuando no tiene el plan Plus vigente ahora mismo
        (ver `plan_plus_vigente`) — en ese caso el valor puede seguir
        guardado en `vendor.color_acento`, listo para reactivarse solo
        con volver a Plus. Si aplica, un diccionario con `color` (el hex
        guardado) y `contraste` (blanco o casi negro, calculado para que
        el texto sea legible sobre ese color).
    """
    if not vendor.color_acento or not plan_plus_vigente(vendor):
        return None
    return {"color": vendor.color_acento, "contraste": _contraste_legible(vendor.color_acento)}


PLANTILLA_POR_DEFECTO = "clasica"


def resolver_plantilla_vendor(vendor: Vendor) -> str:
    """Resuelve la plantilla visual efectiva de la tienda pública de un vendedor.

    Punto único de entrada para la función Plus del punto 13 del roadmap
    (plantillas prediseñadas) — `routes/tienda.py` la usa para decidir
    qué archivo de template renderizar. A diferencia de
    `resolver_acento_vendor`, siempre devuelve un valor (nunca None):
    toda tienda tiene que renderizarse con alguna plantilla, y
    "clasica" es la que ya existía antes de esta función, gratis para
    todos.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        `"clasica"` cuando la tienda no eligió ninguna plantilla premium,
        cuando la clave guardada ya no es válida, o cuando no tiene el
        plan Plus vigente ahora mismo (ver `plan_plus_vigente`) — en ese
        último caso el valor sigue guardado en `vendor.plantilla`, listo
        para reactivarse solo con volver a Plus. Si todo lo anterior
        aplica, la clave guardada tal cual (ej. `"editorial"`).
    """
    if not vendor.plantilla or not plan_plus_vigente(vendor):
        return PLANTILLA_POR_DEFECTO
    if obtener_plantilla_tienda(vendor.plantilla) is None:
        return PLANTILLA_POR_DEFECTO
    return vendor.plantilla


def cambiar_password(vendor: Vendor, *, password_actual: str, password_nueva: str) -> None:
    """Cambia la contraseña del vendedor, verificando la actual primero.

    Args:
        vendor: Tienda cuya contraseña se va a cambiar.
        password_actual: Contraseña actual, para confirmar la identidad.
        password_nueva: Contraseña nueva en texto plano.

    Raises:
        PasswordActualIncorrectaError: Si `password_actual` no coincide con la guardada.
        PasswordNuevaInvalidaError: Si `password_nueva` tiene menos de 8 caracteres.
    """
    if not vendor.check_password(password_actual):
        raise PasswordActualIncorrectaError("La contraseña actual no es correcta.")
    if len(password_nueva) < 8:
        raise PasswordNuevaInvalidaError("La nueva contraseña debe tener al menos 8 caracteres.")
    vendor.set_password(password_nueva)
    db.session.commit()


def listar_productos_de_vendor(vendor: Vendor) -> list[VendorProduct]:
    """Devuelve todos los productos de una tienda (activos e inactivos), para el panel.

    Args:
        vendor: Tienda dueña de los productos.

    Returns:
        Lista de `VendorProduct`, más recientes primero.
    """
    return VendorProduct.query.filter_by(vendor_id=vendor.id).order_by(VendorProduct.id.desc()).all()


def listar_productos_activos(vendor: Vendor) -> list[VendorProduct]:
    """Devuelve los productos activos de una tienda, para la página pública.

    Args:
        vendor: Tienda dueña de los productos.

    Returns:
        Lista de `VendorProduct` activos, más recientes primero.
    """
    return (
        VendorProduct.query.filter_by(vendor_id=vendor.id, activo=True)
        .order_by(VendorProduct.id.desc())
        .all()
    )


def obtener_producto_de_vendor(vendor: Vendor, producto_id: int) -> VendorProduct | None:
    """Busca un producto por id, verificando que pertenezca a la tienda dada.

    Evita que un vendedor edite o borre productos de otra tienda
    adivinando ids en la URL.

    Args:
        vendor: Tienda que debería ser dueña del producto.
        producto_id: Id del producto buscado.

    Returns:
        El `VendorProduct` si existe y pertenece a `vendor`, o None.
    """
    return VendorProduct.query.filter_by(id=producto_id, vendor_id=vendor.id).first()


def _establecer_fotos_producto(producto: VendorProduct, urls: list[str]) -> None:
    """Reemplaza la galería de fotos de un producto y sincroniza la portada.

    `VendorProduct.foto_url` (la portada, usada en la tarjeta de la
    grilla y como imagen inicial del modal) se mantiene siempre igual a
    la primera foto de `urls` — así no hay dos fuentes de verdad que se
    puedan desincronizar. Igual que `catalogo_service._establecer_fotos_oferta`,
    se reemplaza la colección completa de golpe (`cascade="all, delete-orphan"`
    en `VendorProduct.fotos`) en vez de diffear fila por fila.

    Args:
        producto: Producto dueño de la galería (nuevo o existente).
        urls: URLs ya resueltas (subidas a R2), en el orden final, sin
            huecos ni duplicados de posición vacía. Máximo `MAX_FOTOS_PRODUCTO`.
    """
    from app.models import VendorProductFoto  # import local para evitar ciclo con VendorProduct

    urls = urls[:MAX_FOTOS_PRODUCTO]
    producto.fotos = [VendorProductFoto(url=url, orden=indice) for indice, url in enumerate(urls)]
    producto.foto_url = urls[0] if urls else None


def crear_producto(
    vendor: Vendor, *, titulo: str, descripcion: str, precio: Decimal, fotos_urls: list[str] | None = None
) -> VendorProduct:
    """Crea un producto nuevo para una tienda. Sin moderación: queda activo de inmediato.

    Args:
        vendor: Tienda dueña del producto nuevo.
        titulo: Nombre del producto.
        descripcion: Descripción del producto.
        precio: Precio en USD.
        fotos_urls: URLs de las fotos del producto ya subidas a R2 (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada).

    Returns:
        El `VendorProduct` recién creado.
    """
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        precio=precio,
    )
    _establecer_fotos_producto(producto, fotos_urls or [])
    db.session.add(producto)
    db.session.commit()
    return producto


def actualizar_producto(
    producto: VendorProduct,
    *,
    titulo: str,
    descripcion: str,
    precio: Decimal,
    fotos_urls: list[str] | None,
    activo: bool,
) -> None:
    """Actualiza los datos de un producto existente.

    Args:
        producto: Producto a actualizar.
        titulo: Nuevo nombre del producto.
        descripcion: Nueva descripción.
        precio: Nuevo precio en USD.
        fotos_urls: URLs finales de las fotos del producto (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada;
            lista vacía si se quitaron todas).
        activo: Si el producto debe seguir visible en la tienda pública.
    """
    producto.titulo = titulo.strip()
    producto.descripcion = descripcion.strip()
    producto.precio = precio
    _establecer_fotos_producto(producto, fotos_urls or [])
    producto.activo = activo
    db.session.commit()


def eliminar_producto(producto: VendorProduct) -> None:
    """Elimina un producto de forma permanente.

    Args:
        producto: Producto a eliminar.
    """
    db.session.delete(producto)
    db.session.commit()


def construir_whatsapp_href(numero: str, mensaje: str) -> str:
    """Arma un link `wa.me` con mensaje prellenado.

    Toda la lógica de codificación de URL vive aquí a propósito — los
    templates de eServicios no llevan lógica Python, solo la muestran.

    Args:
        numero: Número de WhatsApp del vendedor (con código de país).
        mensaje: Texto a prellenar en el chat.

    Returns:
        URL lista para usar en un `<a href>`.
    """
    return f"https://wa.me/{numero}?text={quote(mensaje)}"


def _membrete_trazabilidad(vendor: Vendor) -> str:
    """Firma que se agrega al final de todo mensaje de WhatsApp armado desde una tienda.

    Deja un rastro de qué tienda de e-link originó el mensaje — si
    alguien usa el número de WhatsApp de otra persona sin autorización,
    esta firma facilita identificar desde qué subdominio salió el
    contacto (ver también `reportes.enviar`, el "reportar este sitio"
    de la tienda pública).

    Args:
        vendor: Tienda desde la que se arma el mensaje.

    Returns:
        Línea de firma lista para concatenar al mensaje.
    """
    return f"\n\n— vía {vendor.slug}.eservicios.org"


def href_whatsapp_tienda(vendor: Vendor) -> str:
    """Link de WhatsApp general de la tienda (botón del encabezado).

    Args:
        vendor: Tienda para la que se arma el link.

    Returns:
        URL `wa.me` con un mensaje genérico y el membrete de trazabilidad.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero,
        f"Hola, tengo una consulta sobre {vendor.nombre_negocio}.{_membrete_trazabilidad(vendor)}",
    )


def href_whatsapp_producto(vendor: Vendor, producto: VendorProduct) -> str:
    """Link de WhatsApp de un producto puntual (botón del detalle).

    Args:
        vendor: Tienda dueña del producto.
        producto: Producto sobre el que se pregunta.

    Returns:
        URL `wa.me` con el nombre del producto y el membrete de trazabilidad.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero,
        f'Hola, quiero info sobre "{producto.titulo}" en {vendor.nombre_negocio}.'
        f"{_membrete_trazabilidad(vendor)}",
    )


def _escapar_texto_vcard(texto: str) -> str:
    """Escapa los caracteres especiales del formato vCard (backslash, punto y coma, coma, salto de línea).

    Args:
        texto: Texto sin escapar.

    Returns:
        El texto listo para insertarse en un campo de una línea vCard.
    """
    return texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def construir_vcard(vendor: Vendor) -> str:
    """Arma el contenido de un archivo vCard (.vcf) con los datos públicos de la tienda.

    Pensado para que el vendedor lo descargue junto al QR (ver
    `/vendedor/contacto.vcf`) y lo comparta para que sus clientes
    guarden la tienda como contacto de un toque, sin escribir el
    número a mano.

    Args:
        vendor: Tienda cuyo contacto se exporta.

    Returns:
        Texto en formato vCard 3.0, listo para escribir a un archivo `.vcf`.
    """
    lineas = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{_escapar_texto_vcard(vendor.nombre_negocio)}",
        f"ORG:{_escapar_texto_vcard(vendor.nombre_negocio)}",
        f"TEL;TYPE=CELL:{vendor.whatsapp_numero}",
        f"URL:https://{vendor.slug}.eservicios.org",
    ]
    if vendor.bio:
        lineas.append(f"NOTE:{_escapar_texto_vcard(vendor.bio)}")
    lineas.append("END:VCARD")
    return "\r\n".join(lineas)


# --- Enlaces personalizados (estilo Linktree) ---


def _validar_url_link(url: str) -> str:
    """Valida y normaliza la URL de un enlace personalizado.

    Solo exige que empiece con `http://` o `https://` — no se valida
    contra una lista de dominios permitidos a propósito, para que el
    vendedor pueda enlazar cualquier red o sitio (Instagram, TikTok,
    su propio sitio web, etc.), igual que en Linktree/Beacons.

    Args:
        url: URL tal como la escribió el vendedor.

    Returns:
        La URL con espacios recortados.

    Raises:
        LinkInvalidoError: Si no empieza con `http://` o `https://`.
    """
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise LinkInvalidoError("El enlace debe empezar con http:// o https://.")
    return url


def listar_links_de_vendor(vendor: Vendor) -> list[VendorLink]:
    """Devuelve todos los enlaces de una tienda (activos e inactivos), para el panel.

    Args:
        vendor: Tienda dueña de los enlaces.

    Returns:
        Lista de `VendorLink` ordenada por el campo `orden`.
    """
    return VendorLink.query.filter_by(vendor_id=vendor.id).order_by(VendorLink.orden).all()


def listar_links_activos(vendor: Vendor) -> list[VendorLink]:
    """Devuelve los enlaces activos de una tienda, para la página pública.

    Args:
        vendor: Tienda dueña de los enlaces.

    Returns:
        Lista de `VendorLink` activos, ordenada por el campo `orden`.
    """
    return (
        VendorLink.query.filter_by(vendor_id=vendor.id, activo=True)
        .order_by(VendorLink.orden)
        .all()
    )


def obtener_link_de_vendor(vendor: Vendor, link_id: int) -> VendorLink | None:
    """Busca un enlace por id, verificando que pertenezca a la tienda dada.

    Evita que un vendedor edite o borre enlaces de otra tienda
    adivinando ids en la URL.

    Args:
        vendor: Tienda que debería ser dueña del enlace.
        link_id: Id del enlace buscado.

    Returns:
        El `VendorLink` si existe y pertenece a `vendor`, o None.
    """
    return VendorLink.query.filter_by(id=link_id, vendor_id=vendor.id).first()


def crear_link(vendor: Vendor, *, titulo: str, url: str) -> VendorLink:
    """Crea un enlace personalizado nuevo para una tienda.

    Se agrega al final del orden actual (no hay límite de cantidad —
    el plan gratis no restringe cuántos enlaces puede tener una tienda).

    Args:
        vendor: Tienda dueña del enlace nuevo.
        titulo: Texto visible del botón (ej. "Mi Instagram").
        url: Destino del enlace.

    Returns:
        El `VendorLink` recién creado.

    Raises:
        LinkInvalidoError: Si el título queda vacío o la URL no es válida.
    """
    titulo = titulo.strip()
    if not titulo:
        raise LinkInvalidoError("El título del enlace es obligatorio.")
    url_valida = _validar_url_link(url)

    orden_maximo = (
        db.session.query(func.max(VendorLink.orden)).filter(VendorLink.vendor_id == vendor.id).scalar()
    )
    siguiente_orden = (orden_maximo + 1) if orden_maximo is not None else 0

    link = VendorLink(vendor_id=vendor.id, titulo=titulo, url=url_valida, orden=siguiente_orden)
    db.session.add(link)
    db.session.commit()
    return link


def actualizar_link(link: VendorLink, *, titulo: str, url: str, activo: bool) -> None:
    """Actualiza los datos de un enlace existente.

    Args:
        link: Enlace a actualizar.
        titulo: Nuevo texto visible del botón.
        url: Nuevo destino del enlace.
        activo: Si el enlace debe seguir visible en la tienda pública.

    Raises:
        LinkInvalidoError: Si el título queda vacío o la URL no es válida.
    """
    titulo = titulo.strip()
    if not titulo:
        raise LinkInvalidoError("El título del enlace es obligatorio.")
    link.titulo = titulo
    link.url = _validar_url_link(url)
    link.activo = activo
    db.session.commit()


def eliminar_link(link: VendorLink) -> None:
    """Elimina un enlace de forma permanente.

    Args:
        link: Enlace a eliminar.
    """
    db.session.delete(link)
    db.session.commit()


def mover_link(vendor: Vendor, link: VendorLink, *, direccion: str) -> None:
    """Sube o baja un enlace un puesto, intercambiando `orden` con su vecino.

    Se busca el vecino inmediato en la lista completa (activos e
    inactivos) de la tienda, ordenada por `orden`, y se intercambian los
    valores — así no hace falta renumerar toda la lista ni usar
    drag-and-drop en el front.

    Args:
        vendor: Tienda dueña del enlace (para acotar la búsqueda del vecino).
        link: Enlace a mover.
        direccion: `"arriba"` o `"abajo"`.
    """
    links = listar_links_de_vendor(vendor)
    posicion = next((i for i, l in enumerate(links) if l.id == link.id), None)
    if posicion is None:
        return

    if direccion == "arriba" and posicion > 0:
        vecino = links[posicion - 1]
    elif direccion == "abajo" and posicion < len(links) - 1:
        vecino = links[posicion + 1]
    else:
        return

    link.orden, vecino.orden = vecino.orden, link.orden
    db.session.commit()
