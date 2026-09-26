"""Tests del registro de tiendas, el manejo de subdominio (slug) y el login con Google.

Cubre el bloque "Registro + Google OAuth" del split de god-files:
`registrar_vendor`/`registrar_vendor_google` (alta de una tienda, con o
sin contraseña), el ciclo de vida del slug (`validar_formato_slug`,
`slug_disponible`, `cambiar_slug`, `estado_cambio_slug`), la
vinculación de una cuenta de Google a una tienda existente
(`vincular_google`) y los tres lookups de tienda (`obtener_vendor_por_slug`,
`obtener_vendor_por_slug_activo`, `obtener_vendor_por_email`,
`obtener_vendor_por_google_id`) — ya separado en `vendor_registro_service.py`.

No hay tests de ruta acá a propósito: `/vendedor/registro` y el
callback de Google (`auth_google_callback`) dependen de envío de correo
y del flujo OAuth completo — fuera de alcance de esta pasada de
caracterización, que se enfoca en la lógica de negocio pura.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.models import ReservedSlug, VendorSlugHistorial
from app.services.vendor_registro_service import (
    DIAS_ENTRE_CAMBIOS_SLUG,
    MAX_CAMBIOS_SLUG,
    CambioSlugMuyRecienteError,
    EmailDuplicadoError,
    EmailInvalidoError,
    LimiteCambiosSlugError,
    SlugDuplicadoError,
    SlugInvalidoError,
    SlugReservadoError,
    cambiar_slug,
    estado_cambio_slug,
    obtener_vendor_por_email,
    obtener_vendor_por_google_id,
    obtener_vendor_por_slug,
    obtener_vendor_por_slug_activo,
    registrar_vendor,
    registrar_vendor_google,
    slug_disponible,
    validar_formato_slug,
    vincular_google,
)


def _datos_unicos() -> dict[str, str]:
    """Datos de alta con email/slug garantizados libres (sufijo aleatorio)."""
    sufijo = uuid.uuid4().hex[:8]
    return {
        "email": f"nuevo-{sufijo}@eservicios-test.local",
        "slug": f"nuevo-{sufijo}",
        "nombre_negocio": "Tienda nueva de prueba",
        # Prefijo "58" (Venezuela, ver monedas_service) sin "+" — así el
        # test de moneda sugerida no cae siempre en el default "usd".
        "whatsapp_numero": "58212345678",
    }


@pytest.fixture
def slug_reservado(db):
    """Una palabra reservada descartable, borrada al terminar."""
    reservado = ReservedSlug(palabra=f"reservado-{uuid.uuid4().hex[:8]}")
    db.session.add(reservado)
    db.session.commit()
    yield reservado
    db.session.delete(reservado)
    db.session.commit()


def _agregar_historial(db, vendor, *, dias_hasta_expirar: int, dias_de_antiguedad: int = 0) -> VendorSlugHistorial:
    """Crea un `VendorSlugHistorial` para `vendor`, con la antigüedad que pida el test."""
    historial = VendorSlugHistorial(
        vendor_id=vendor.id,
        slug_anterior=f"viejo-{uuid.uuid4().hex[:8]}",
        expira_en=datetime.utcnow() + timedelta(days=dias_hasta_expirar),
    )
    db.session.add(historial)
    db.session.commit()
    if dias_de_antiguedad:
        historial.creado_en = datetime.utcnow() - timedelta(days=dias_de_antiguedad)
        db.session.commit()
    return historial


class TestValidarFormatoSlug:
    """Tests de `validar_formato_slug`."""

    def test_normaliza_mayusculas_y_espacios(self):
        assert validar_formato_slug("  MiTienda123  ") == "mitienda123"

    def test_muy_corto_lanza_error(self):
        with pytest.raises(SlugInvalidoError):
            validar_formato_slug("ab")

    def test_muy_largo_lanza_error(self):
        with pytest.raises(SlugInvalidoError):
            validar_formato_slug("a" * 64)

    def test_empieza_con_guion_lanza_error(self):
        with pytest.raises(SlugInvalidoError):
            validar_formato_slug("-tienda")

    def test_termina_con_guion_lanza_error(self):
        with pytest.raises(SlugInvalidoError):
            validar_formato_slug("tienda-")

    def test_caracteres_no_permitidos_lanza_error(self):
        with pytest.raises(SlugInvalidoError):
            validar_formato_slug("mi_tienda!")

    def test_guiones_en_medio_son_validos(self):
        assert validar_formato_slug("mi-tienda-linda") == "mi-tienda-linda"


class TestSlugDisponible:
    """Tests de `slug_disponible`."""

    def test_libre_esta_disponible(self, db):
        assert slug_disponible(f"libre-{uuid.uuid4().hex[:8]}") is True

    def test_reservado_no_esta_disponible(self, slug_reservado):
        assert slug_disponible(slug_reservado.palabra) is False

    def test_en_uso_por_una_tienda_no_esta_disponible(self, vendor_prueba):
        assert slug_disponible(vendor_prueba.slug) is False

    def test_con_redireccion_vigente_no_esta_disponible(self, db, vendor_prueba):
        historial = _agregar_historial(db, vendor_prueba, dias_hasta_expirar=10)

        assert slug_disponible(historial.slug_anterior) is False

    def test_con_redireccion_vencida_si_esta_disponible(self, db, vendor_prueba):
        historial = _agregar_historial(db, vendor_prueba, dias_hasta_expirar=-1)

        assert slug_disponible(historial.slug_anterior) is True


class TestRegistrarVendor:
    """Tests de `registrar_vendor` (alta con correo y contraseña)."""

    def test_crea_vendor_con_datos_normalizados(self, db):
        datos = _datos_unicos()
        vendor = registrar_vendor(
            email=f"  {datos['email'].upper()}  ",
            password="clave-segura-123",
            slug=f"  {datos['slug'].upper()}  ",
            nombre_negocio=datos["nombre_negocio"],
            whatsapp_numero=datos["whatsapp_numero"],
        )

        assert vendor.id is not None
        assert vendor.email == datos["email"]
        assert vendor.slug == datos["slug"]
        assert vendor.check_password("clave-segura-123") is True

        db.session.delete(vendor)
        db.session.commit()

    def test_sugiere_moneda_por_codigo_de_pais_whatsapp(self, db):
        datos = _datos_unicos()
        vendor = registrar_vendor(
            email=datos["email"],
            password="clave-segura-123",
            slug=datos["slug"],
            nombre_negocio=datos["nombre_negocio"],
            whatsapp_numero="58212345678",  # Venezuela
        )

        assert vendor.moneda == "ves"

        db.session.delete(vendor)
        db.session.commit()

    def test_email_invalido_lanza_error(self):
        datos = _datos_unicos()
        with pytest.raises(EmailInvalidoError):
            registrar_vendor(
                email="no-es-un-correo",
                password="clave-segura-123",
                slug=datos["slug"],
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )

    def test_email_duplicado_lanza_error(self, vendor_prueba):
        datos = _datos_unicos()
        with pytest.raises(EmailDuplicadoError):
            registrar_vendor(
                email=vendor_prueba.email,
                password="clave-segura-123",
                slug=datos["slug"],
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )

    def test_slug_reservado_lanza_error(self, slug_reservado):
        datos = _datos_unicos()
        with pytest.raises(SlugReservadoError):
            registrar_vendor(
                email=datos["email"],
                password="clave-segura-123",
                slug=slug_reservado.palabra,
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )

    def test_slug_duplicado_lanza_error(self, vendor_prueba):
        datos = _datos_unicos()
        with pytest.raises(SlugDuplicadoError):
            registrar_vendor(
                email=datos["email"],
                password="clave-segura-123",
                slug=vendor_prueba.slug,
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )


class TestObtenerVendorPorGoogleId:
    """Tests de `obtener_vendor_por_google_id`."""

    def test_sin_coincidencia_devuelve_none(self, db):
        assert obtener_vendor_por_google_id(f"google-{uuid.uuid4().hex}") is None

    def test_con_coincidencia_devuelve_el_vendor(self, db, vendor_prueba):
        vendor_prueba.google_id = f"google-{uuid.uuid4().hex}"
        db.session.commit()

        assert obtener_vendor_por_google_id(vendor_prueba.google_id) is vendor_prueba


class TestVincularGoogle:
    """Tests de `vincular_google`."""

    def test_vincula_y_marca_email_verificado(self, db, vendor_prueba):
        vendor_prueba.email_verificado = False
        db.session.commit()
        nuevo_google_id = f"google-{uuid.uuid4().hex}"

        vincular_google(vendor_prueba, nuevo_google_id)

        assert vendor_prueba.google_id == nuevo_google_id
        assert vendor_prueba.email_verificado is True


class TestRegistrarVendorGoogle:
    """Tests de `registrar_vendor_google` (alta sin contraseña, vía Google)."""

    def test_crea_vendor_sin_password_y_verificado(self, db):
        datos = _datos_unicos()
        vendor = registrar_vendor_google(
            google_id=f"google-{uuid.uuid4().hex}",
            email=datos["email"],
            slug=datos["slug"],
            nombre_negocio=datos["nombre_negocio"],
            whatsapp_numero=datos["whatsapp_numero"],
        )

        assert vendor.password_hash is None
        assert vendor.email_verificado is True
        assert vendor.check_password("cualquier-cosa") is False
        assert vendor.moneda == "ves"

        db.session.delete(vendor)
        db.session.commit()

    def test_email_duplicado_lanza_error(self, vendor_prueba):
        with pytest.raises(EmailDuplicadoError):
            registrar_vendor_google(
                google_id=f"google-{uuid.uuid4().hex}",
                email=vendor_prueba.email,
                slug=f"otro-{uuid.uuid4().hex[:8]}",
                nombre_negocio="Otra tienda",
                whatsapp_numero="58212345678",
            )

    def test_slug_duplicado_lanza_error(self, vendor_prueba):
        datos = _datos_unicos()
        with pytest.raises(SlugDuplicadoError):
            registrar_vendor_google(
                google_id=f"google-{uuid.uuid4().hex}",
                email=datos["email"],
                slug=vendor_prueba.slug,
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )

    def test_slug_reservado_lanza_error(self, slug_reservado):
        datos = _datos_unicos()
        with pytest.raises(SlugReservadoError):
            registrar_vendor_google(
                google_id=f"google-{uuid.uuid4().hex}",
                email=datos["email"],
                slug=slug_reservado.palabra,
                nombre_negocio=datos["nombre_negocio"],
                whatsapp_numero=datos["whatsapp_numero"],
            )


class TestObtenerVendorPorSlugActivo:
    """Tests de `obtener_vendor_por_slug_activo` (usado por la tienda pública)."""

    def test_encuentra_tienda_activa(self, vendor_prueba):
        assert obtener_vendor_por_slug_activo(vendor_prueba.slug) is vendor_prueba

    def test_es_insensible_a_mayusculas(self, vendor_prueba):
        assert obtener_vendor_por_slug_activo(vendor_prueba.slug.upper()) is vendor_prueba

    def test_no_encuentra_tienda_inactiva(self, db, vendor_prueba):
        vendor_prueba.activo = False
        db.session.commit()

        assert obtener_vendor_por_slug_activo(vendor_prueba.slug) is None

    def test_sin_coincidencia_devuelve_none(self, db):
        assert obtener_vendor_por_slug_activo(f"no-existe-{uuid.uuid4().hex[:8]}") is None


class TestObtenerVendorPorSlug:
    """Tests de `obtener_vendor_por_slug` (a diferencia de la anterior, incluye inactivas)."""

    def test_encuentra_tienda_inactiva_tambien(self, db, vendor_prueba):
        vendor_prueba.activo = False
        db.session.commit()

        assert obtener_vendor_por_slug(vendor_prueba.slug) is vendor_prueba

    def test_sin_coincidencia_devuelve_none(self, db):
        assert obtener_vendor_por_slug(f"no-existe-{uuid.uuid4().hex[:8]}") is None


class TestObtenerVendorPorEmail:
    """Tests de `obtener_vendor_por_email`."""

    def test_encuentra_por_email_normalizado(self, vendor_prueba):
        assert obtener_vendor_por_email(f"  {vendor_prueba.email.upper()}  ") is vendor_prueba

    def test_sin_coincidencia_devuelve_none(self, db):
        assert obtener_vendor_por_email(f"no-existe-{uuid.uuid4().hex[:8]}@x.com") is None


class TestEstadoCambioSlug:
    """Tests de `estado_cambio_slug`."""

    def test_sin_cambios_previos(self, vendor_prueba):
        estado = estado_cambio_slug(vendor_prueba)

        assert estado["cambios_usados"] == 0
        assert estado["cambios_restantes"] == MAX_CAMBIOS_SLUG
        assert estado["puede_cambiar_ahora"] is True
        assert estado["proxima_fecha_disponible"] is None

    def test_con_un_cambio_reciente_no_puede_cambiar_ahora(self, db, vendor_prueba):
        _agregar_historial(db, vendor_prueba, dias_hasta_expirar=30)

        estado = estado_cambio_slug(vendor_prueba)

        assert estado["cambios_usados"] == 1
        assert estado["cambios_restantes"] == MAX_CAMBIOS_SLUG - 1
        assert estado["puede_cambiar_ahora"] is False
        assert estado["proxima_fecha_disponible"] is not None

    def test_con_cambio_antiguo_ya_puede_cambiar(self, db, vendor_prueba):
        _agregar_historial(db, vendor_prueba, dias_hasta_expirar=1, dias_de_antiguedad=DIAS_ENTRE_CAMBIOS_SLUG + 1)

        estado = estado_cambio_slug(vendor_prueba)

        assert estado["puede_cambiar_ahora"] is True
        assert estado["proxima_fecha_disponible"] is None

    def test_agotados_los_cambios(self, db, vendor_prueba):
        for _ in range(MAX_CAMBIOS_SLUG):
            _agregar_historial(db, vendor_prueba, dias_hasta_expirar=1, dias_de_antiguedad=DIAS_ENTRE_CAMBIOS_SLUG + 1)

        estado = estado_cambio_slug(vendor_prueba)

        assert estado["cambios_restantes"] == 0
        assert estado["puede_cambiar_ahora"] is False
        assert estado["proxima_fecha_disponible"] is None


class TestCambiarSlug:
    """Tests de `cambiar_slug`."""

    def test_cambia_el_slug_y_crea_historial(self, db, vendor_prueba):
        slug_anterior = vendor_prueba.slug
        nuevo_slug = f"nuevo-{uuid.uuid4().hex[:8]}"

        resultado = cambiar_slug(vendor_prueba, nuevo_slug=nuevo_slug)

        assert resultado == nuevo_slug
        assert vendor_prueba.slug == nuevo_slug
        historial = VendorSlugHistorial.query.filter_by(vendor_id=vendor_prueba.id).one()
        assert historial.slug_anterior == slug_anterior

    def test_formato_invalido_lanza_error(self, vendor_prueba):
        with pytest.raises(SlugInvalidoError):
            cambiar_slug(vendor_prueba, nuevo_slug="ab")

    def test_mismo_slug_actual_lanza_error(self, vendor_prueba):
        with pytest.raises(SlugInvalidoError):
            cambiar_slug(vendor_prueba, nuevo_slug=vendor_prueba.slug)

    def test_slug_reservado_lanza_error(self, vendor_prueba, slug_reservado):
        with pytest.raises(SlugReservadoError):
            cambiar_slug(vendor_prueba, nuevo_slug=slug_reservado.palabra)

    def test_slug_en_uso_por_otra_tienda_lanza_error(self, vendor_prueba, otro_vendor_prueba):
        with pytest.raises(SlugDuplicadoError):
            cambiar_slug(vendor_prueba, nuevo_slug=otro_vendor_prueba.slug)

    def test_slug_con_redireccion_vigente_lanza_error(self, db, vendor_prueba, otro_vendor_prueba):
        historial = _agregar_historial(db, otro_vendor_prueba, dias_hasta_expirar=10)

        with pytest.raises(SlugDuplicadoError):
            cambiar_slug(vendor_prueba, nuevo_slug=historial.slug_anterior)

    def test_agotados_los_cambios_lanza_error(self, db, vendor_prueba):
        for _ in range(MAX_CAMBIOS_SLUG):
            _agregar_historial(db, vendor_prueba, dias_hasta_expirar=1, dias_de_antiguedad=DIAS_ENTRE_CAMBIOS_SLUG + 1)

        with pytest.raises(LimiteCambiosSlugError):
            cambiar_slug(vendor_prueba, nuevo_slug=f"otronuevo-{uuid.uuid4().hex[:8]}")

    def test_cambio_muy_reciente_lanza_error(self, db, vendor_prueba):
        _agregar_historial(db, vendor_prueba, dias_hasta_expirar=1)

        with pytest.raises(CambioSlugMuyRecienteError):
            cambiar_slug(vendor_prueba, nuevo_slug=f"otronuevo-{uuid.uuid4().hex[:8]}")
