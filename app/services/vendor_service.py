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

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import (
    PlanVendor,
    Vendor,
    VendorCategoria,
    VendorProduct,
)
from app.services.badges_producto_service import BADGES_PRODUCTO
from app.services.email_service import EnvioCorreoError, enviar_correo, renderizar_plantilla_correo
from app.services.estados_stock_service import ESTADOS_STOCK
from app.services.monedas_service import MONEDAS
from app.services.plantillas_tienda_service import PLANTILLAS_TIENDA
from app.services.site_info_service import obtener_info_sitio

# Duraciones que el vendedor puede pedir desde /vendedor/perfil/plan/solicitar
# (ver solicitar_plan_plus) — mismas 4 opciones que ya ofrece el alta manual
# de admin (`admin/vendedor_detalle.html`, formulario de "Plan"), para que
# lo que el vendedor pide y lo que el admin puede otorgar sea siempre lo
# mismo.
MESES_PLAN_SOLICITABLES = {1, 3, 6, 12}

# Precios de e-link Plus por duración (definidos por Jose, 2026-09-14) —
# mismas claves que MESES_PLAN_SOLICITABLES, para que el formulario de
# solicitud y la pantalla de comparación de planes (/vendedor/perfil/plan)
# usen siempre la misma fuente de verdad. Strings, no float/Decimal: son
# solo texto para mostrar (ver planes_plus_con_precio()), nunca se usan
# para cobrar nada — no hay pago automático todavía (solicitar_plan_plus
# es un formulario de "pago manual + reporte", ver más abajo).
PRECIOS_PLAN_PLUS: dict[int, str] = {
    1: "4.99",
    3: "13.99",
    6: "27.49",
    12: "53.99",
}

# Duración de la prueba gratuita de e-link Plus (ver activar_prueba_plus/
# prueba_plus_vigente más abajo) — pedido de Jose, 2026-09-14.
DIAS_PRUEBA_PLUS = 7

# Formato exigido para Vendor.color_acento — "#" + 6 dígitos hexadecimales,
# el mismo formato que produce un <input type="color"> nativo del navegador
# (ver vendedor/perfil.html). Cualquier otro valor se ignora en silencio,
# mismo criterio que ya se usa con plantilla en actualizar_perfil().
_PATRON_COLOR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

MAX_FOTOS_PRODUCTO = 5


class PerfilInvalidoError(Exception):
    """Los datos de personalización de la tienda no son válidos."""


class PasswordActualIncorrectaError(Exception):
    """La contraseña actual ingresada no coincide con la guardada."""


class PasswordNuevaInvalidaError(Exception):
    """La contraseña nueva no cumple los requisitos mínimos."""


class SolicitudVerificacionInvalidaError(Exception):
    """El mensaje de la solicitud de verificación viene vacío, o la tienda ya está verificada."""


class SolicitudPlanInvalidaError(Exception):
    """Los datos de la solicitud de pago a e-link Plus no son válidos (meses, mensaje o comprobante)."""


class PruebaPlusInvalidaError(Exception):
    """La tienda ya usó su prueba gratuita de e-link Plus, o ya tiene Plus real vigente."""


def actualizar_perfil(
    vendor: Vendor,
    *,
    nombre_negocio: str,
    whatsapp_numero: str,
    bio: str,
    logo_url: str | None,
    banner_url: str | None,
    color_acento: str | None = None,
    plantilla: str | None = None,
    disponible_ahora: bool = True,
    moneda: str | None = None,
    cupon: str = "",
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
        color_acento: Color de acento propio de la tienda ("#rrggbb"),
            elegido de la paleta de círculos o (con e-link Plus) de un
            selector de color libre — ver `resolver_acento_vendor` y
            `listar_paleta_acento`. Reemplaza, desde la unificación del
            2026-09-11, al viejo selector separado de "diseño de portada
            y avatar": este mismo color ahora también arma el degradado
            del banner/avatar cuando el vendedor no subió su propio logo
            o portada. Un valor que no cumpla el formato "#rrggbb" se
            ignora en silencio (queda en None, que resuelve al azul de
            eServicios) en vez de lanzar error. A propósito NO valida
            acá si el color es de los permitidos para el plan actual del
            vendedor (ej. un color exclusivo de Plus guardado con Plus
            vigente, que luego vence): se guarda tal cual llegue, y es
            `resolver_acento_vendor` quien decide en tiempo de render si
            corresponde usarlo o caer de vuelta al azul/rosado gratis —
            así el vendedor no pierde su elección si vuelve a Plus más
            adelante.
        plantilla: Clave de una plantilla de `plantillas_tienda_service`
            (ej. "editorial"), o vacío/None para la plantilla "Clásica".
            Un valor que no exista en `PLANTILLAS_TIENDA` se ignora en
            silencio (queda en None) en vez de lanzar error. Tampoco
            valida el plan Plus aquí —esa función de e-link Plus se
            gatea en tiempo de render (ver `resolver_plantilla_vendor`),
            no al guardar.
        disponible_ahora: Estado del interruptor manual "Disponible
            ahora" / "Fuera de horario" (función de e-link Plus, punto
            15 del roadmap). A diferencia de `plantilla`, no hay valor
            inválido posible (siempre es `True` o `False`), así que se
            guarda tal cual — es responsabilidad del llamador conservar
            `vendor.disponible_ahora` en vez de pasar un valor nuevo
            cuando el formulario ni siquiera mostraba el interruptor
            (por no tener Plus vigente), igual que ya hace con
            `cupon` (ver `vendedor.perfil`).
        moneda: Clave de una moneda de `monedas_service` (ej. "cop"), o
            vacío/None/inválida para conservar la moneda que la tienda
            ya tenía (nunca queda sin moneda — a diferencia de
            `plantilla`, no existe un "sin moneda" para resetear). Sin
            relación con el plan: gratis para cualquier tienda, no se
            gatea en ningún resolver (ver `monedas_service` para el
            porqué).
        cupon: Texto del cupón/código de descuento (ej. "VERANO10"),
            función de e-link Plus (punto 16 del roadmap) — cadena vacía
            para quitarlo. No valida ningún formato (es texto libre
            corto, no un código con reglas), y se guarda tal cual aunque
            el plan no esté vigente en este momento, mismo trato que
            `color_acento`/`plantilla` — la aplicación real se resuelve
            en tiempo de render (ver `resolver_cupon_vendor`).

    Raises:
        PerfilInvalidoError: Si el nombre o el WhatsApp quedan vacíos.
    """
    nombre_negocio = nombre_negocio.strip()
    whatsapp_numero = whatsapp_numero.strip()
    if not nombre_negocio:
        raise PerfilInvalidoError("El nombre de la tienda es obligatorio.")
    if not whatsapp_numero:
        raise PerfilInvalidoError("El número de WhatsApp es obligatorio.")

    if plantilla and plantilla not in PLANTILLAS_TIENDA:
        plantilla = None

    vendor.nombre_negocio = nombre_negocio
    vendor.whatsapp_numero = whatsapp_numero
    vendor.bio = bio.strip() or None
    vendor.logo_url = logo_url
    vendor.banner_url = banner_url
    vendor.color_acento = color_acento if (color_acento and _PATRON_COLOR_HEX.match(color_acento)) else None
    vendor.plantilla = plantilla or None
    vendor.disponible_ahora = disponible_ahora
    if moneda and moneda in MONEDAS:
        vendor.moneda = moneda
    vendor.cupon = cupon.strip() or None
    db.session.commit()


def solicitar_verificacion_vendedor(
    vendor: Vendor, *, mensaje: str, documento_url: str | None = None
) -> None:
    """Envía (o actualiza) la solicitud de la insignia "Vendedor verificado por eServicios".

    El vendedor explica por qué debería verificarse su tienda y, de
    forma opcional, adjunta una foto de un documento de respaldo
    (cédula, RUC/registro de negocio, factura de servicios, etc.). La
    subida a R2 ya se resuelve en la ruta antes de llamar aquí (mismo
    patrón que logo/portada/fotos de producto — ver
    `routes/vendedor.py._subir_imagen_opcional`); esta función solo
    recibe la URL ya resuelta, nunca un archivo. El equipo de eServicios
    revisa la solicitud desde `/admin/vendedores/<id>` y la aprueba
    (`vendor_admin_service.marcar_verificado`) o la rechaza
    (`vendor_admin_service.rechazar_solicitud_verificacion`) — no hay
    verificación automática todavía.

    Reenviar mientras una solicitud sigue pendiente simplemente la
    reemplaza (mensaje nuevo, fecha actualizada, y el documento solo si
    se adjuntó uno nuevo) — no hace falta que el vendedor espere una
    respuesta para corregir o completar lo que ya mandó.

    Requiere plan Plus vigente (decisión de Jose, 2026-08-31). Jose
    aclaró el 2026-09-14 que esto NUNCA se quitó — la confusión de una
    pasada anterior fue de presentación, no de reglas: antes, sin Plus,
    `/vendedor/perfil/verificacion` mandaba derecho a
    `/vendedor/perfil/plan`; ahora esa misma pantalla se queda donde
    está y lista "Plan e-link Plus vigente" como uno más de sus
    requisitos, con su propio enlace para resolverlo — el chequeo real
    sigue siendo este de acá. A diferencia del badge en sí, que sigue
    siendo gratis para cualquier plan una vez otorgado
    (`Vendor.verificado` no tiene ningún resolver de gating, se lee
    directo en las plantillas): el plan Plus es la puerta para *pedir*
    la verificación, no una condición para conservarla — una tienda ya
    verificada la mantiene aunque su Plus venza después.

    Al enviarla con éxito se manda además un correo de aviso a
    info@eservicios.org (mismo patrón que `solicitar_plan_plus`) para
    que el equipo no dependa de entrar a `/admin` a cada rato — ese
    correo es solo un aviso, la cola en `/admin` sigue siendo la fuente
    de verdad. Si el envío falla, la solicitud igual queda guardada: el
    error se registra en el log sin hacer fallar el envío del vendedor.

    Args:
        vendor: Tienda que solicita la verificación.
        mensaje: Explicación breve de por qué debería verificarse. No
            puede venir vacío.
        documento_url: URL en R2 de la foto de respaldo, si el vendedor
            adjuntó una en este envío. None si no adjuntó ninguna en
            este envío — en ese caso se conserva el documento ya
            guardado de un envío anterior, si había uno.

    Raises:
        SolicitudVerificacionInvalidaError: Si `mensaje` viene vacío, si
            la tienda ya está verificada (no tiene sentido volver a
            solicitarlo), o si el plan Plus no está vigente.
    """
    mensaje = (mensaje or "").strip()
    if not mensaje:
        raise SolicitudVerificacionInvalidaError(
            "Contanos brevemente por qué debería verificarse tu tienda."
        )
    if vendor.verificado:
        raise SolicitudVerificacionInvalidaError("Tu tienda ya está verificada.")
    if not plan_plus_vigente(vendor):
        raise SolicitudVerificacionInvalidaError(
            "Solicitar la verificación requiere e-link Plus vigente."
        )

    vendor.solicitud_verificacion_mensaje = mensaje
    if documento_url is not None:
        vendor.solicitud_verificacion_documento_url = documento_url
    vendor.solicitud_verificacion_en = datetime.utcnow()
    db.session.commit()

    try:
        destinatario = obtener_info_sitio().contacto.email
        documento_final = vendor.solicitud_verificacion_documento_url
        cuerpo_html = renderizar_plantilla_correo(
            "email/solicitud_verificacion.html",
            nombre_negocio=vendor.nombre_negocio,
            slug=vendor.slug,
            email=vendor.email,
            mensaje=mensaje,
            documento_url=documento_final,
        )
        cuerpo_texto = (
            f'Nueva solicitud de la insignia "Vendedor verificado"\n\n'
            f"Tienda: {vendor.nombre_negocio} ({vendor.slug}.eservicios.org)\n"
            f"Correo del vendedor: {vendor.email}\n\n"
            f"Por qué debería verificarse:\n{mensaje}\n\n"
            + (
                f"Documento adjunto: {documento_final}\n\n"
                if documento_final
                else "Sin documento adjunto.\n\n"
            )
            + f"Revisar y aprobar/rechazar desde /admin/vendedores/{vendor.id}."
        )
        enviar_correo(
            destinatario,
            f'Solicitud de insignia "Vendedor verificado" — {vendor.nombre_negocio}',
            cuerpo_texto,
            cuerpo_html=cuerpo_html,
        )
    except EnvioCorreoError as error:
        current_app.logger.error(
            "No se pudo enviar el aviso de solicitud de verificación de %s: %s", vendor.slug, error
        )


def solicitar_plan_plus(vendor: Vendor, *, meses: int, mensaje: str, comprobante_url: str) -> None:
    """Envía la solicitud de pago manual a e-link Plus, autoservicio (roadmap, Fase 3-bis).

    A diferencia de `solicitar_verificacion_vendedor`, acá SÍ hace falta
    un comprobante nuevo en cada envío (no tiene sentido reusar la
    "foto del pago anterior" para justificar un pago distinto) — la
    subida a R2 ya se resuelve en la ruta antes de llamar aquí, mismo
    patrón de siempre (ver `routes/vendedor.py._subir_imagen_opcional`).

    Dos cosas pasan al enviarla: (1) queda guardada en la tienda para
    que el equipo de eServicios la revise desde `/admin/vendedores/<id>`
    y la apruebe (`vendor_admin_service.aprobar_solicitud_plan`, que
    otorga Plus por los meses pedidos) o la rechace
    (`rechazar_solicitud_plan`); (2) se manda un correo de aviso a
    info@eservicios.org con los mismos datos, para que Jose no dependa
    de entrar a `/admin` a cada rato para enterarse de una solicitud
    nueva — ese correo es solo un aviso, la cola en `/admin` sigue
    siendo la fuente de verdad para aprobar o rechazar. Si el envío del
    correo falla (SMTP caído, etc.) la solicitud igual queda guardada:
    el error se registra en el log, sin hacer fallar el envío del
    vendedor por un problema que no es culpa suya.

    Reenviar mientras una solicitud sigue pendiente simplemente la
    reemplaza (meses, mensaje y comprobante nuevos, fecha actualizada).

    Args:
        vendor: Tienda que solicita el plan Plus.
        meses: Cantidad de meses que dice haber pagado. Debe ser uno de
            `MESES_PLAN_SOLICITABLES` (1, 3, 6 o 12 — las mismas 4
            opciones que ofrece el alta manual de admin).
        mensaje: Detalles de la transacción (método usado, referencia,
            fecha, quién pagó, etc.). No puede venir vacío.
        comprobante_url: URL en R2 de la foto/captura del comprobante de
            pago. No puede venir vacío.

    Raises:
        SolicitudPlanInvalidaError: Si `meses` no es una de las
            duraciones permitidas, si `mensaje` viene vacío, o si
            `comprobante_url` viene vacío.
    """
    if meses not in MESES_PLAN_SOLICITABLES:
        raise SolicitudPlanInvalidaError("Elige una de las duraciones disponibles.")
    mensaje = (mensaje or "").strip()
    if not mensaje:
        raise SolicitudPlanInvalidaError(
            "Cuéntanos los detalles de tu pago (método usado, referencia, fecha)."
        )
    if not comprobante_url:
        raise SolicitudPlanInvalidaError("Adjunta una foto o captura del comprobante de pago.")

    vendor.solicitud_plan_meses = meses
    vendor.solicitud_plan_mensaje = mensaje
    vendor.solicitud_plan_comprobante_url = comprobante_url
    vendor.solicitud_plan_en = datetime.utcnow()
    db.session.commit()

    try:
        destinatario = obtener_info_sitio().contacto.email
        cuerpo_html = renderizar_plantilla_correo(
            "email/solicitud_plan.html",
            nombre_negocio=vendor.nombre_negocio,
            slug=vendor.slug,
            email=vendor.email,
            meses=meses,
            mensaje=mensaje,
            comprobante_url=comprobante_url,
        )
        cuerpo_texto = (
            f"Nueva solicitud de e-link Plus\n\n"
            f"Tienda: {vendor.nombre_negocio} ({vendor.slug}.eservicios.org)\n"
            f"Correo del vendedor: {vendor.email}\n"
            f"Meses pedidos: {meses}\n\n"
            f"Detalles de la transacción:\n{mensaje}\n\n"
            f"Comprobante: {comprobante_url}\n\n"
            f"Revisar y aprobar/rechazar desde /admin/vendedores/{vendor.id}."
        )
        enviar_correo(
            destinatario,
            f"Solicitud de e-link Plus — {vendor.nombre_negocio}",
            cuerpo_texto,
            cuerpo_html=cuerpo_html,
        )
    except EnvioCorreoError as error:
        current_app.logger.error(
            "No se pudo enviar el aviso de solicitud de plan de %s: %s", vendor.slug, error
        )


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


def planes_plus_con_precio() -> list[dict[str, object]]:
    """Arma la tabla de precios de e-link Plus para /vendedor/perfil/plan y el formulario de solicitud.

    Fuente única de precios (`PRECIOS_PLAN_PLUS`) convertida a un formato
    listo para las plantillas: precio total, equivalente mensual (2
    decimales) y, para los planes de más de un mes, el porcentaje de
    ahorro frente a pagar mes a mes esa misma cantidad de meses (con el
    precio de 1 mes como base). El plan de 12 meses se marca
    `destacado=True` para el tratamiento visual de "mejor precio" que
    pidió Jose para el pago anual.

    Returns:
        Una entrada por cada mes de `MESES_PLAN_SOLICITABLES` (ordenadas
        de menor a mayor duración), cada una con `meses` (int), `precio`
        (str, ej. "13.99"), `precio_por_mes` (str, ej. "4.66"),
        `ahorro_pct` (int, o None para el plan de 1 mes) y `destacado`
        (bool).
    """
    precio_mensual = Decimal(PRECIOS_PLAN_PLUS[1])
    planes: list[dict[str, object]] = []
    for meses in sorted(MESES_PLAN_SOLICITABLES):
        precio = Decimal(PRECIOS_PLAN_PLUS[meses])
        precio_por_mes = precio / meses
        if meses == 1:
            ahorro_pct = None
        else:
            base = precio_mensual * meses
            ahorro_pct = int(round((1 - precio / base) * 100))
        planes.append(
            {
                "meses": meses,
                "precio": f"{precio:.2f}",
                "precio_por_mes": f"{precio_por_mes:.2f}",
                "ahorro_pct": ahorro_pct,
                "destacado": meses == 12,
            }
        )
    return planes


def prueba_plus_expira_en(vendor: Vendor) -> datetime | None:
    """Fecha y hora en que vence (o venció) la prueba gratuita de e-link Plus de la tienda.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        None si nunca activó la prueba (`vendor.prueba_plus_activada_en`
        es None). Si la activó, esa fecha más `DIAS_PRUEBA_PLUS` días —
        pasada o futura, sin importar si sigue vigente ahora mismo (ver
        `prueba_plus_vigente` para eso).
    """
    if vendor.prueba_plus_activada_en is None:
        return None
    return vendor.prueba_plus_activada_en + timedelta(days=DIAS_PRUEBA_PLUS)


def prueba_plus_vigente(vendor: Vendor) -> bool:
    """Indica si la prueba gratuita de 7 días de e-link Plus está activa ahora mismo.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        True si el vendedor activó la prueba (`activar_prueba_plus`) y
        todavía no pasaron `DIAS_PRUEBA_PLUS` días desde entonces.
    """
    expira = prueba_plus_expira_en(vendor)
    return expira is not None and datetime.utcnow() < expira


def prueba_plus_disponible(vendor: Vendor) -> bool:
    """Indica si el vendedor todavía puede activar la prueba gratuita (nunca la usó).

    Condición para mostrar el aviso de activación en `/vendedor/inicio`
    — a propósito no chequea si la tienda ya tiene Plus real (eso lo
    decide cada ruta, para no ofrecerle la prueba a quien ya paga).

    Args:
        vendor: Tienda a evaluar.

    Returns:
        True si `vendor.prueba_plus_activada_en` sigue en None. La
        prueba es de una sola vez por cuenta, para siempre, aunque ya
        haya vencido — por eso esto NO vuelve a dar True cuando la
        prueba expiró.
    """
    return vendor.prueba_plus_activada_en is None


def plan_plus_o_prueba_vigente(vendor: Vendor) -> bool:
    """Indica si la tienda puede usar las funciones de e-link Plus ahora mismo (real o de prueba).

    Puerta general para las funciones de personalización y venta de Plus
    (color, plantilla, disponibilidad, cupón, badge de producto, estado
    de stock, categorías, consulta múltiple) — a diferencia de
    `plan_plus_vigente()` a secas, esta SÍ cuenta la prueba gratuita de
    7 días (ver `prueba_plus_vigente`), agregada 2026-09-14 a pedido de
    Jose.

    IMPORTANTE: esta función nunca debe usarse para decidir si el
    vendedor puede *solicitar* la insignia "Vendedor verificado" — ese
    chequeo (`solicitar_verificacion_vendedor` y la ruta
    `vendedor.perfil_verificacion`) sigue usando `plan_plus_vigente()` a
    secas, a propósito: la prueba no cuenta para la insignia (decisión
    explícita de Jose) — solo un plan Plus real, pagado y aprobado (o un
    admin que la otorgue a mano vía `marcar_verificado`), la habilita.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        True si `plan_plus_vigente(vendor)` o `prueba_plus_vigente(vendor)`.
    """
    return plan_plus_vigente(vendor) or prueba_plus_vigente(vendor)


def activar_prueba_plus(vendor: Vendor) -> None:
    """Activa, una única vez por cuenta, la prueba gratuita de 7 días de e-link Plus.

    Se llama desde `/vendedor/prueba` (aviso en `/vendedor/inicio`,
    pedido de Jose 2026-09-14) — pensada para que un vendedor free note
    la diferencia con Plus antes de decidirse a pagar. No otorga ningún
    plan real ni toca `vendor.plan`/`vendor.plan_expira_en`: solo marca
    `vendor.prueba_plus_activada_en`, que es lo único que
    `plan_plus_o_prueba_vigente` consulta para la prueba.

    Args:
        vendor: Tienda que activa la prueba.

    Raises:
        PruebaPlusInvalidaError: Si ya usó su prueba antes (vigente o ya
            vencida — es de una sola vez para siempre), o si ya tiene
            e-link Plus real vigente ahora mismo (no tendría sentido).
    """
    if not prueba_plus_disponible(vendor):
        raise PruebaPlusInvalidaError(
            "Ya usaste tu prueba gratuita de e-link Plus — es de una sola vez por cuenta."
        )
    if plan_plus_vigente(vendor):
        raise PruebaPlusInvalidaError("Tu tienda ya tiene e-link Plus vigente, no hace falta la prueba.")
    vendor.prueba_plus_activada_en = datetime.utcnow()
    db.session.commit()


def cambiar_password(vendor: Vendor, *, password_actual: str, password_nueva: str) -> None:
    """Cambia la contraseña del vendedor, o la crea si todavía no tiene una.

    Una tienda registrada solo con "Iniciar sesión con Google" no tiene
    `password_hash` (ver `Vendor.password_hash`) — para esos casos no hay
    contraseña actual que verificar, así que `password_actual` se ignora
    y se crea la primera contraseña directamente (2026-09-14, pedido de
    Jose: la sección "Seguridad" del perfil ahora le ofrece a esas cuentas
    crear una contraseña propia, además de seguir entrando con Google).
    Cuando sí hay una contraseña guardada, el comportamiento es el de
    siempre: hay que confirmarla primero.

    Args:
        vendor: Tienda cuya contraseña se va a cambiar o crear.
        password_actual: Contraseña actual, para confirmar la identidad.
            Se ignora si la tienda todavía no tiene ninguna contraseña.
        password_nueva: Contraseña nueva en texto plano.

    Raises:
        PasswordActualIncorrectaError: Si la tienda ya tenía contraseña y
            `password_actual` no coincide con la guardada.
        PasswordNuevaInvalidaError: Si `password_nueva` tiene menos de 8 caracteres.
    """
    if vendor.password_hash and not vendor.check_password(password_actual):
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


def _categoria_id_valida(vendor: Vendor, categoria_id: int | None) -> int | None:
    """Verifica que un `categoria_id` pertenezca a la tienda dada antes de guardarlo.

    Mismo trato de "silenciosamente inválido" que `badge`/`estado_stock`
    en `crear_producto`/`actualizar_producto`: evita guardar un id de
    categoría de otra tienda (formulario manipulado) sin tener que
    lanzar un error — el producto simplemente queda sin categoría.

    Args:
        vendor: Tienda dueña del producto.
        categoria_id: Id propuesto, o None.

    Returns:
        `categoria_id` si corresponde a una categoría de `vendor`, o None.
    """
    if categoria_id is None:
        return None
    if VendorCategoria.query.filter_by(id=categoria_id, vendor_id=vendor.id).first() is None:
        return None
    return categoria_id


def crear_producto(
    vendor: Vendor,
    *,
    titulo: str,
    descripcion: str,
    precio: Decimal,
    fotos_urls: list[str] | None = None,
    badge: str | None = None,
    estado_stock: str | None = None,
    categoria_id: int | None = None,
) -> VendorProduct:
    """Crea un producto nuevo para una tienda. Sin moderación: queda activo de inmediato.

    Args:
        vendor: Tienda dueña del producto nuevo.
        titulo: Nombre del producto.
        descripcion: Descripción del producto.
        precio: Precio en la moneda de la tienda (`vendor.moneda`) — sin
            conversión, se muestra tal cual (ver `monedas_service`).
        fotos_urls: URLs de las fotos del producto ya subidas a R2 (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada).
        badge: Clave de un badge de `badges_producto_service` (ej.
            "oferta"), o vacío/None para no mostrar ninguno. Un valor que
            no exista en `BADGES_PRODUCTO` se ignora en silencio (queda
            en None) — mismo trato que `plantilla` en `Vendor`. No
            valida el plan Plus aquí — esa función se gatea
            en tiempo de render (ver `resolver_badge_producto`).
        estado_stock: Clave de un estado de `estados_stock_service` (ej.
            "agotado"), o vacío/None para "Normal". Mismo trato que
            `badge`: una clave inválida se ignora en silencio, y el plan
            Plus se gatea en tiempo de render (ver
            `resolver_estado_stock_producto`).
        categoria_id: Id de una `VendorCategoria` de esta misma tienda, o
            None para dejar el producto sin categorizar. Un id que no
            pertenezca a `vendor` se ignora en silencio (queda en None)
            — mismo trato que `badge`/`estado_stock`, para no depender
            de que el formulario haya sido manipulado con un id ajeno.

    Returns:
        El `VendorProduct` recién creado.
    """
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        precio=precio,
        badge=badge if badge in BADGES_PRODUCTO else None,
        estado_stock=estado_stock if estado_stock in ESTADOS_STOCK else None,
        categoria_id=_categoria_id_valida(vendor, categoria_id),
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
    badge: str | None = None,
    estado_stock: str | None = None,
    categoria_id: int | None = None,
) -> None:
    """Actualiza los datos de un producto existente.

    Args:
        producto: Producto a actualizar.
        titulo: Nuevo nombre del producto.
        descripcion: Nueva descripción.
        precio: Nuevo precio en la moneda de la tienda (`vendor.moneda`).
        fotos_urls: URLs finales de las fotos del producto (hasta
            `MAX_FOTOS_PRODUCTO`, en orden — la primera queda como portada;
            lista vacía si se quitaron todas).
        activo: Si el producto debe seguir visible en la tienda pública.
        badge: Clave de un badge de `badges_producto_service`, o
            vacío/None para quitarlo. Mismo trato que en `crear_producto`.
        estado_stock: Clave de un estado de `estados_stock_service`, o
            vacío/None para volver a "Normal". Mismo trato que en `crear_producto`.
        categoria_id: Id de una `VendorCategoria` de la misma tienda que
            el producto, o None para quitarle la categoría. Mismo trato
            que en `crear_producto`.
    """
    producto.titulo = titulo.strip()
    producto.descripcion = descripcion.strip()
    producto.precio = precio
    _establecer_fotos_producto(producto, fotos_urls or [])
    producto.activo = activo
    producto.badge = badge if badge in BADGES_PRODUCTO else None
    producto.estado_stock = estado_stock if estado_stock in ESTADOS_STOCK else None
    producto.categoria_id = _categoria_id_valida(producto.vendor, categoria_id)
    db.session.commit()


def eliminar_producto(producto: VendorProduct) -> None:
    """Elimina un producto de forma permanente.

    Args:
        producto: Producto a eliminar.
    """
    db.session.delete(producto)
    db.session.commit()

