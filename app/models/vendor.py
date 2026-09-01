"""Modelo de vendedor (tienda con subdominio propio, tipo Linktree/Beacons).

Autenticación y perfil de la tienda viven en el mismo modelo, igual que
`AdminUser` — no hace falta separar cuenta de perfil mientras cada
vendedor tenga una sola tienda. El vendedor se registra gratis y elige
el nombre de su subdominio (`slug`, ej. `mitienda.eservicios.org`).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class PlanVendor(str, enum.Enum):
    """Plan de la tienda del vendedor."""

    FREE = "free"
    # "e-link Plus": plan de pago (ver claude/roadmap-monetizacion-e-link.md,
    # Fase 2). Su vigencia se controla con `Vendor.plan_expira_en`, no con
    # este enum — una tienda puede quedar con `plan == PLUS` mientras un
    # proceso de vencimiento programado (aún no implementado) la baja a
    # FREE cuando `plan_expira_en` ya pasó.
    PLUS = "plus"


class Vendor(db.Model):
    """Vendedor con tienda pública propia en un subdominio (`<slug>.eservicios.org`).

    Corre en paralelo al catálogo maestro (`Category`/`Offering`, curado
    por el equipo de eServicios): cada `Vendor` administra sus propios
    `VendorProduct` y `VendorLink` de forma autogestionada, sin
    moderación por ahora. Ver `claude/spec-tiendas-vendedor.md` en el
    proyecto para el diseño completo.
    """

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Nullable: una cuenta creada por "Iniciar sesión con Google" (ver
    # google_id abajo y app/services/google_auth_service.py) no tiene
    # contraseña propia — check_password() ya contempla este caso.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    nombre_negocio: Mapped[str] = mapped_column(String(150), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_numero: Mapped[str] = mapped_column(String(30), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Preset de color elegido para el banner/avatar de respaldo cuando no
    # hay logo_url/banner_url propios (ver app/services/estilos_portada_service.py).
    # None = usa el placeholder genérico de siempre (acento compartido).
    estilo_portada: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Color de acento propio de la tienda ("#rrggbb"), función de e-link
    # Plus (roadmap, Fase 2, punto 12) — reemplaza el --color-accent
    # compartido en la tienda pública y en el panel del propio vendedor
    # cuando el plan Plus está vigente (ver vendor_service.resolver_acento_vendor).
    # Se guarda aunque el plan no esté vigente en este momento (ej. Plus
    # vencido), para que el vendedor no tenga que volver a elegirlo si
    # renueva — la aplicación real siempre se resuelve en tiempo de
    # render, nunca solo por la presencia de este valor.
    color_acento: Mapped[str | None] = mapped_column(String(7), nullable=True)
    # Plantilla visual de la tienda pública (layout + par tipográfico),
    # función de e-link Plus (roadmap, Fase 2, punto 13) — ver
    # app/services/plantillas_tienda_service.py para las claves válidas.
    # None = plantilla "Clásica" (la de siempre, gratis para todos). Igual
    # que color_acento, se guarda aunque el plan no esté vigente en este
    # momento; la aplicación real siempre se resuelve en tiempo de render
    # (ver vendor_service.resolver_plantilla_vendor).
    plantilla: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Indicador manual "Disponible ahora" / "Fuera de horario", función de
    # e-link Plus (roadmap, Fase 2, punto 15) — el vendedor lo prende/apaga
    # a mano desde /vendedor/perfil (sin horarios ni zona horaria
    # calculados automáticamente, decisión explícita de Jose). True por
    # defecto (una tienda nueva empieza mostrándose disponible). El
    # indicador solo se muestra en la tienda pública mientras el plan Plus
    # esté vigente (ver vendor_service.resolver_disponibilidad_vendor) —
    # el valor igual se conserva si el plan vence, listo para reactivarse.
    disponible_ahora: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Código de cupón/descuento, texto libre y corto (ej. "VERANO10"),
    # función de e-link Plus (roadmap, Fase 2, punto 16) — se muestra en
    # la tienda pública debajo del botón de WhatsApp, dentro de un marco
    # con la etiqueta fija "CUPÓN" al lado, y el cliente lo copia con un
    # toque (ver app/static/js/copiar_cupon.js). NO es un sistema de
    # descuentos real: no calcula ningún porcentaje ni ajusta ningún
    # precio — es solo el texto que el vendedor define para que el
    # cliente lo mencione al escribir por WhatsApp, y el vendedor lo
    # honra a mano, igual que el resto de e-link no tiene checkout real.
    # None = sin cupón activo (no se muestra nada). Igual que
    # color_acento/plantilla, se guarda aunque el plan no esté vigente en
    # este momento, para no perderlo si el vendedor renueva Plus — la
    # aplicación real siempre se resuelve en tiempo de render (ver
    # vendor_service.resolver_cupon_vendor).
    cupon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Insignia "Vendedor verificado por eServicios" — señal de confianza,
    # no de personalización visual, así que a diferencia de color_acento/
    # plantilla/badge/disponible_ahora NO depende del plan Plus: gratis
    # para cualquier tienda (roadmap, Fase 2, punto 21 — clasificación
    # explícita de Jose, distinta de la de los demás puntos de esa fase).
    # Se activa/desactiva a mano por el equipo de eServicios desde el
    # panel de admin (ver vendor_admin_service.marcar_verificado /
    # quitar_verificacion) — no hay verificación automática todavía.
    verificado: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Solicitud de verificación pendiente de revisión — el vendedor la
    # envía desde /vendedor/perfil/verificacion con un mensaje y,
    # opcionalmente, una foto de un documento de respaldo subida a R2
    # (ver vendor_service.solicitar_verificacion_vendedor). Los 3 campos
    # son nullable a propósito: None/None/None = sin solicitud activa.
    # solicitud_verificacion_en no-None = hay una solicitud pendiente de
    # revisión. El equipo de eServicios la aprueba (vendor_admin_service.
    # marcar_verificado, que limpia estos 3 campos y otorga `verificado`)
    # o la rechaza (vendor_admin_service.rechazar_solicitud_verificacion,
    # que los limpia igual pero sin tocar `verificado`) desde
    # /admin/vendedores/<id>. Reenviar mientras hay una pendiente
    # simplemente la reemplaza — no hace falta esperar una respuesta
    # para corregir o completar lo ya enviado.
    solicitud_verificacion_mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    solicitud_verificacion_documento_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    solicitud_verificacion_en: Mapped[datetime | None] = mapped_column(nullable=True)
    # Moneda en la que se muestran los precios de los productos de la
    # tienda (código en minúsculas — "usd", "ves", "cop", "mxn", "pen",
    # "eur" — ver app/services/monedas_service.py para las claves
    # válidas). A diferencia de color_acento/plantilla/badge/
    # disponible_ahora (Fase 2, e-link Plus), esta función es GRATIS
    # para cualquier plan (decisión explícita de Jose, roadmap Fase 2,
    # punto 20) — no depende de plan_plus_vigente, se lee directo en las
    # plantillas de la tienda pública y del panel, sin ningún resolver
    # de gating. Al registrarse se sugiere una moneda a partir del
    # código de país del WhatsApp (ver vendor_service.registrar_vendor /
    # monedas_service.detectar_moneda_por_whatsapp); "usd" si no hay
    # coincidencia. El vendedor la cambia libremente después desde
    # /vendedor/perfil. No implica conversión automática de precios: el
    # número cargado en cada producto se muestra tal cual, solo cambia
    # el símbolo.
    moneda: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    plan: Mapped[PlanVendor] = mapped_column(
        SqlEnum(PlanVendor, name="plan_vendor"), default=PlanVendor.FREE, nullable=False
    )
    # Fecha hasta la que el plan Plus está vigente. None cuando el plan es
    # FREE, o cuando Plus se otorgó sin fecha de vencimiento (caso especial,
    # no usado por el alta manual de admin — ver
    # vendor_admin_service.cambiar_plan_vendor). No se usa para decidir el
    # plan actual en tiempo real: `plan` es la fuente de verdad hasta que
    # exista el proceso de vencimiento automático (roadmap, Fase 2-bis).
    plan_expira_en: Mapped[datetime | None] = mapped_column(nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    # Verificación de correo (código de 6 dígitos, enviado vía Brevo — ver
    # app/services/email_service.py y app/services/vendor_email_verificacion_service.py).
    # Mientras email_verificado sea False, el vendedor no puede entrar al
    # panel (ver requiere_email_verificado / rutas /vendedor/verificar-email).
    email_verificado: Mapped[bool] = mapped_column(default=False, nullable=False)
    codigo_verificacion_email: Mapped[str | None] = mapped_column(String(6), nullable=True)
    codigo_verificacion_expira_en: Mapped[datetime | None] = mapped_column(nullable=True)

    # "Iniciar sesión con Google" (ver app/services/google_auth_service.py y
    # las rutas /vendedor/auth/google*). Guarda el claim "sub" del perfil
    # de Google — un id estable de la cuenta, distinto del correo (el
    # correo se puede cambiar en Google; el sub no). Una tienda registrada
    # con contraseña puede vincular su Google más tarde con el mismo
    # correo (ver vendor_service.vincular_google) — por eso es nullable:
    # no toda tienda tiene una cuenta de Google vinculada.
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    productos: Mapped[list["VendorProduct"]] = relationship(  # noqa: F821
        back_populates="vendor", cascade="all, delete-orphan", order_by="VendorProduct.id.desc()"
    )
    links: Mapped[list["VendorLink"]] = relationship(  # noqa: F821
        back_populates="vendor", cascade="all, delete-orphan", order_by="VendorLink.orden"
    )
    categorias: Mapped[list["VendorCategoria"]] = relationship(  # noqa: F821
        back_populates="vendor", cascade="all, delete-orphan", order_by="VendorCategoria.orden"
    )
    slugs_anteriores: Mapped[list["VendorSlugHistorial"]] = relationship(  # noqa: F821
        back_populates="vendor",
        cascade="all, delete-orphan",
        order_by="VendorSlugHistorial.creado_en.desc()",
    )

    def set_password(self, password: str) -> None:
        """Genera y guarda el hash de una contraseña nueva.

        Args:
            password: Contraseña en texto plano a hashear.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica una contraseña contra el hash guardado.

        Args:
            password: Contraseña en texto plano a verificar.

        Returns:
            True si la contraseña coincide con el hash guardado. Siempre
            False si la cuenta no tiene contraseña (registrada solo con
            Google — ver `google_id`), sin lanzar ningún error.
        """
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug de la tienda.
        """
        return f"<Vendor {self.slug}>"
