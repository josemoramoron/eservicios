"""Administración de tiendas de vendedor (e-link) desde el panel `/admin`.

Separado de `vendor_service.py` a propósito: ese módulo es el
autoservicio del propio vendedor sobre SU tienda (siempre recibe un
`Vendor` ya resuelto por sesión); este módulo es para el equipo de
eServicios operando sobre CUALQUIER tienda desde el panel de admin
(buscar, suspender, reactivar, restablecer contraseña, eliminar de
forma permanente). Ver `claude/spec-tiendas-vendedor.md` en el
proyecto para el diseño completo de esta sección del panel.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import PlanVendor, TipoEventoVendor, Vendor, VendorEvento, VendorReporte
from app.services.estadisticas_service import DIAS_VENTANA_ESTADISTICAS
from app.services.r2_service import eliminar_imagen

# Duración aproximada de un "mes" de plan Plus, en días. Se usa una
# constante fija (en vez de dateutil.relativedelta) para no agregar una
# dependencia nueva solo por esto — la imprecisión (28-31 días reales por
# mes calendario) es aceptable para un alta manual hecha por el equipo de
# eServicios, que ya revisa la fecha resultante antes de confirmar.
DIAS_POR_MES_PLUS = 30

# Valores aceptados en el filtro `estado` de `listar_vendors_admin` y en
# el query string `?estado=` de la lista del panel.
ESTADO_ACTIVOS = "activos"
ESTADO_SUSPENDIDOS = "suspendidos"


def listar_vendors_admin(*, busqueda: str | None = None, estado: str | None = None) -> list[Vendor]:
    """Lista tiendas de vendedor para el panel de admin, con búsqueda y filtro de estado.

    Args:
        busqueda: Texto a buscar (sin distinguir mayúsculas) contra el
            nombre de la tienda, el subdominio o el email del vendedor.
            None o cadena vacía para no filtrar.
        estado: `ESTADO_ACTIVOS`, `ESTADO_SUSPENDIDOS`, o None/otro
            valor para no filtrar por estado.

    Returns:
        Lista de `Vendor`, más recientes primero.
    """
    query = Vendor.query
    if busqueda:
        texto = f"%{busqueda.strip()}%"
        query = query.filter(
            or_(
                Vendor.nombre_negocio.ilike(texto),
                Vendor.slug.ilike(texto),
                Vendor.email.ilike(texto),
            )
        )
    if estado == ESTADO_ACTIVOS:
        query = query.filter_by(activo=True)
    elif estado == ESTADO_SUSPENDIDOS:
        query = query.filter_by(activo=False)
    return query.order_by(Vendor.creado_en.desc()).all()


def obtener_vendor_por_id(vendor_id: int) -> Vendor | None:
    """Busca una tienda por id, sin restricción de dueño (uso exclusivo del panel de admin).

    Args:
        vendor_id: Id de la tienda buscada.

    Returns:
        El `Vendor` si existe, o None.
    """
    return db.session.get(Vendor, vendor_id)


def estadisticas_globales() -> dict:
    """Resume el conjunto de tiendas de vendedor, para la portada de la sección.

    Returns:
        Diccionario con `total`, `activos`, `suspendidos` (conteo de
        tiendas), y `vistas`/`clics_whatsapp` (suma de todas las
        tiendas en los últimos `dias` días — misma ventana que
        `estadisticas_service.resumen_estadisticas`, para que los
        números sean comparables).
    """
    desde = datetime.utcnow() - timedelta(days=DIAS_VENTANA_ESTADISTICAS)
    total = Vendor.query.count()
    activos = Vendor.query.filter_by(activo=True).count()
    base = VendorEvento.query.filter(VendorEvento.creado_en >= desde)
    return {
        "total": total,
        "activos": activos,
        "suspendidos": total - activos,
        "vistas": base.filter(VendorEvento.tipo == TipoEventoVendor.VISTA).count(),
        "clics_whatsapp": base.filter(VendorEvento.tipo == TipoEventoVendor.CLIC_WHATSAPP).count(),
        "dias": DIAS_VENTANA_ESTADISTICAS,
    }


def suspender_vendor(vendor: Vendor) -> None:
    """Suspende una tienda (`activo=False`).

    Una tienda suspendida deja de responder en su subdominio (se
    muestra `tienda/no_disponible.html`, ver `subdominio_service.
    resolver_vendor_inactivo_por_host`) y el vendedor ya no puede
    iniciar sesión en `/vendedor/login` (`vendor_auth_service.
    autenticar_vendor` exige `activo=True`) — reversible en cualquier
    momento con `reactivar_vendor`.

    Args:
        vendor: Tienda a suspender.
    """
    vendor.activo = False
    db.session.commit()


def reactivar_vendor(vendor: Vendor) -> None:
    """Reactiva una tienda suspendida (`activo=True`).

    Args:
        vendor: Tienda a reactivar.
    """
    vendor.activo = True
    db.session.commit()


def cambiar_plan_vendor(vendor: Vendor, *, plan: PlanVendor, meses: int | None = None) -> None:
    """Cambia el plan de una tienda de forma manual desde el panel de admin.

    Es el checkout manual: el equipo de eServicios confirma un pago (por
    fuera del sistema, ver `claude/roadmap-monetizacion-e-link.md`) y
    aplica el cambio aquí — todavía no hay pago automático (PayPal/Stripe)
    ni generador de códigos promocionales.

    Args:
        vendor: Tienda a la que se le cambia el plan.
        plan: Nuevo plan (`PlanVendor.FREE` o `PlanVendor.PLUS`).
        meses: Cantidad de meses de vigencia a otorgar. Obligatorio (y
            debe ser un entero positivo) cuando `plan` es `PLUS`;
            ignorado cuando `plan` es `FREE`. Si la tienda ya tenía Plus
            vigente, los meses se suman a partir de su fecha de
            vencimiento actual (no desde hoy), para no descontar tiempo
            ya pagado en una renovación anticipada; si ya había vencido
            (o nunca tuvo Plus), se cuentan desde ahora.

    Raises:
        ValueError: Si `plan` es `PLUS` y `meses` no es un entero positivo.
    """
    if plan == PlanVendor.PLUS:
        if not meses or meses <= 0:
            raise ValueError("meses debe ser un entero positivo para otorgar el plan Plus.")
        ahora = datetime.utcnow()
        vigente = vendor.plan_expira_en if (vendor.plan_expira_en and vendor.plan_expira_en > ahora) else ahora
        vendor.plan_expira_en = vigente + timedelta(days=DIAS_POR_MES_PLUS * meses)
        vendor.plan = PlanVendor.PLUS
    else:
        vendor.plan = PlanVendor.FREE
        vendor.plan_expira_en = None
    db.session.commit()


def restablecer_password_vendor(vendor: Vendor) -> str:
    """Genera una contraseña temporal nueva para el vendedor y la aplica de inmediato.

    Pensado para cuando un vendedor pierde acceso a su cuenta y le pide
    ayuda al equipo de eServicios. La contraseña generada no queda
    guardada en ningún lado en texto plano (se hashea igual que
    cualquier otra) — el llamador es responsable de mostrarla una sola
    vez al admin para que se la pase al vendedor por un canal seguro.

    Args:
        vendor: Tienda cuya contraseña se va a restablecer.

    Returns:
        La contraseña temporal en texto plano (única vez que existe fuera del hash).
    """
    password_temporal = secrets.token_urlsafe(9)
    vendor.set_password(password_temporal)
    db.session.commit()
    return password_temporal


def eliminar_vendor_permanente(vendor: Vendor) -> None:
    """Elimina una tienda de vendedor de forma permanente e irreversible.

    Borra, en este orden: (1) todas las imágenes de la tienda en
    Cloudflare R2 — logo, portada y cada foto de cada producto (el
    borrado en R2 falla en silencio por diseño, ver `r2_service.
    eliminar_imagen`, así que un objeto ya ausente en el bucket no
    interrumpe el resto); (2) los eventos de mini-analítica
    (`VendorEvento`) y los reportes de moderación (`VendorReporte`) de
    la tienda, que hay que borrar a mano porque `Vendor` no declara una
    relación de cascada hacia ninguno de los dos (a diferencia de
    `productos`, `links` y `slugs_anteriores`, que sí tienen
    `cascade="all, delete-orphan"` y se borran solos al borrar el
    `Vendor`); y (3) la fila de `Vendor` en sí, que arrastra en cascada
    sus productos (y las fotos de galería de cada uno), enlaces, e
    historial de subdominios.

    El llamador es responsable de pedir una confirmación fuerte antes
    de invocar esta función (ver `admin.vendedor_eliminar`, que exige
    reescribir el slug de la tienda) — no hay forma de deshacer esto.

    Args:
        vendor: Tienda a eliminar.
    """
    imagenes_a_borrar = []
    if vendor.logo_url:
        imagenes_a_borrar.append(vendor.logo_url)
    if vendor.banner_url:
        imagenes_a_borrar.append(vendor.banner_url)
    for producto in vendor.productos:
        for foto in producto.fotos:
            imagenes_a_borrar.append(foto.url)

    for url in imagenes_a_borrar:
        eliminar_imagen(url)

    VendorEvento.query.filter_by(vendor_id=vendor.id).delete(synchronize_session=False)
    VendorReporte.query.filter_by(vendor_id=vendor.id).delete(synchronize_session=False)
    db.session.delete(vendor)
    db.session.commit()
