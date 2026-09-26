"""Tests de personalización del perfil, verificación, plan Plus y contraseña.

Cubre el bloque "Perfil/Plan Plus" del split de god-files:
`actualizar_perfil` (personalización de la tienda), las dos solicitudes
que mandan correo de aviso a eServicios (`solicitar_verificacion_vendedor`,
`solicitar_plan_plus`), todo el chequeo de vigencia de plan
(`plan_plus_vigente`, `prueba_plus_*`, `plan_plus_o_prueba_vigente`,
`activar_prueba_plus`), la tabla de precios (`planes_plus_con_precio`) y
`cambiar_password` — ya separado en `vendor_perfil_service.py`.

`solicitar_verificacion_vendedor`/`solicitar_plan_plus` mandan un correo
de aviso a eServicios con `enviar_correo` (SMTP real vía Brevo) — acá se
reemplaza siempre con un doble de prueba (`monkeypatch`), nunca se toca
la red. Se prueba tanto el envío exitoso (el correo se llama con los
datos correctos) como el fallo (`EnvioCorreoError`): en ambos casos la
solicitud debe quedar guardada igual, porque el error de correo solo se
loggea y no debe romper el flujo del vendedor (ver el docstring de
ambas funciones en `vendor_service.py`).

No hay tests de ruta acá a propósito: las rutas de `/vendedor/perfil/*`
dependen de subida de imágenes a R2 y de CSRF — fuera de alcance de esta
pasada de caracterización, que se enfoca en la lógica de negocio pura.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models import PlanVendor
from app.services.email_service import EnvioCorreoError
from app.services.vendor_perfil_service import (
    DIAS_PRUEBA_PLUS,
    MESES_PLAN_SOLICITABLES,
    PasswordActualIncorrectaError,
    PasswordNuevaInvalidaError,
    PerfilInvalidoError,
    PruebaPlusInvalidaError,
    SolicitudPlanInvalidaError,
    SolicitudVerificacionInvalidaError,
    activar_prueba_plus,
    actualizar_perfil,
    cambiar_password,
    plan_plus_o_prueba_vigente,
    plan_plus_vigente,
    planes_plus_con_precio,
    prueba_plus_disponible,
    prueba_plus_expira_en,
    prueba_plus_vigente,
    solicitar_plan_plus,
    solicitar_verificacion_vendedor,
)


def _activar_plus(db, vendor, *, dias_restantes: int | None = None) -> None:
    """Pone `vendor` en plan Plus. `dias_restantes=None` = sin vencimiento."""
    vendor.plan = PlanVendor.PLUS
    vendor.plan_expira_en = (
        None if dias_restantes is None else datetime.utcnow() + timedelta(days=dias_restantes)
    )
    db.session.commit()


def _correo_falso(monkeypatch, *, falla: bool = False):
    """Reemplaza `enviar_correo` por un doble que registra sus llamadas.

    Nunca toca la red. Si `falla=True`, simula un `EnvioCorreoError`
    (SMTP caído, credenciales inválidas, etc.) — igual que el real,
    para probar que ese fallo no rompe el flujo del vendedor.
    """
    llamadas = []

    def _fake(destinatario, asunto, cuerpo_texto, cuerpo_html=None):
        llamadas.append(
            {
                "destinatario": destinatario,
                "asunto": asunto,
                "cuerpo_texto": cuerpo_texto,
                "cuerpo_html": cuerpo_html,
            }
        )
        if falla:
            raise EnvioCorreoError("SMTP caído (simulado en el test).")

    monkeypatch.setattr("app.services.vendor_perfil_service.enviar_correo", _fake)
    return llamadas


class TestActualizarPerfil:
    """Tests de `actualizar_perfil`."""

    def test_actualiza_campos_basicos(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="  Tienda Nueva  ",
            whatsapp_numero="  +50212345678  ",
            bio="  Una bio corta  ",
            logo_url="https://r2.example.com/logo.png",
            banner_url="https://r2.example.com/banner.png",
        )

        assert vendor_prueba.nombre_negocio == "Tienda Nueva"
        assert vendor_prueba.whatsapp_numero == "+50212345678"
        assert vendor_prueba.bio == "Una bio corta"
        assert vendor_prueba.logo_url == "https://r2.example.com/logo.png"
        assert vendor_prueba.banner_url == "https://r2.example.com/banner.png"

    def test_nombre_vacio_lanza_error(self, vendor_prueba):
        with pytest.raises(PerfilInvalidoError):
            actualizar_perfil(
                vendor_prueba,
                nombre_negocio="   ",
                whatsapp_numero="+50212345678",
                bio="",
                logo_url=None,
                banner_url=None,
            )

    def test_whatsapp_vacio_lanza_error(self, vendor_prueba):
        with pytest.raises(PerfilInvalidoError):
            actualizar_perfil(
                vendor_prueba,
                nombre_negocio="Tienda",
                whatsapp_numero="   ",
                bio="",
                logo_url=None,
                banner_url=None,
            )

    def test_bio_vacia_guarda_none(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="   ",
            logo_url=None,
            banner_url=None,
        )
        assert vendor_prueba.bio is None

    def test_color_valido_se_guarda(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            color_acento="#059669",
        )
        assert vendor_prueba.color_acento == "#059669"

    def test_color_invalido_se_ignora(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            color_acento="no-es-un-color",
        )
        assert vendor_prueba.color_acento is None

    def test_plantilla_valida_se_guarda(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            plantilla="editorial",
        )
        assert vendor_prueba.plantilla == "editorial"

    def test_plantilla_invalida_se_ignora(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            plantilla="no-existe",
        )
        assert vendor_prueba.plantilla is None

    def test_moneda_valida_se_guarda(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            moneda="cop",
        )
        assert vendor_prueba.moneda == "cop"

    def test_moneda_invalida_conserva_la_actual(self, db, vendor_prueba):
        moneda_original = vendor_prueba.moneda
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            moneda="no-existe",
        )
        assert vendor_prueba.moneda == moneda_original

    def test_cupon_vacio_guarda_none(self, db, vendor_prueba):
        vendor_prueba.cupon = "VIEJO10"
        db.session.commit()

        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            cupon="  ",
        )
        assert vendor_prueba.cupon is None

    def test_disponible_ahora_se_guarda_tal_cual(self, db, vendor_prueba):
        actualizar_perfil(
            vendor_prueba,
            nombre_negocio="Tienda",
            whatsapp_numero="+50212345678",
            bio="",
            logo_url=None,
            banner_url=None,
            disponible_ahora=False,
        )
        assert vendor_prueba.disponible_ahora is False


class TestSolicitarVerificacionVendedor:
    """Tests de `solicitar_verificacion_vendedor`."""

    def test_mensaje_vacio_lanza_error(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        with pytest.raises(SolicitudVerificacionInvalidaError):
            solicitar_verificacion_vendedor(vendor_prueba, mensaje="   ")

    def test_tienda_ya_verificada_lanza_error(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.verificado = True
        db.session.commit()

        with pytest.raises(SolicitudVerificacionInvalidaError):
            solicitar_verificacion_vendedor(vendor_prueba, mensaje="Vendo hace 5 años")

    def test_sin_plus_lanza_error(self, db, vendor_prueba):
        with pytest.raises(SolicitudVerificacionInvalidaError):
            solicitar_verificacion_vendedor(vendor_prueba, mensaje="Vendo hace 5 años")

    def test_exitoso_guarda_solicitud_y_manda_correo(self, db, vendor_prueba, monkeypatch):
        _activar_plus(db, vendor_prueba)
        llamadas = _correo_falso(monkeypatch)

        solicitar_verificacion_vendedor(
            vendor_prueba, mensaje="Vendo hace 5 años", documento_url="https://r2.example.com/doc.jpg"
        )

        assert vendor_prueba.solicitud_verificacion_mensaje == "Vendo hace 5 años"
        assert vendor_prueba.solicitud_verificacion_documento_url == "https://r2.example.com/doc.jpg"
        assert vendor_prueba.solicitud_verificacion_en is not None
        assert len(llamadas) == 1
        assert llamadas[0]["destinatario"] == "info@eservicios.org"

    def test_documento_url_none_conserva_el_anterior(self, db, vendor_prueba, monkeypatch):
        _activar_plus(db, vendor_prueba)
        _correo_falso(monkeypatch)
        solicitar_verificacion_vendedor(
            vendor_prueba, mensaje="Primer intento", documento_url="https://r2.example.com/doc1.jpg"
        )

        solicitar_verificacion_vendedor(vendor_prueba, mensaje="Reenvío sin documento nuevo")

        assert vendor_prueba.solicitud_verificacion_mensaje == "Reenvío sin documento nuevo"
        assert vendor_prueba.solicitud_verificacion_documento_url == "https://r2.example.com/doc1.jpg"

    def test_error_de_envio_no_rompe_la_solicitud(self, db, vendor_prueba, monkeypatch):
        _activar_plus(db, vendor_prueba)
        _correo_falso(monkeypatch, falla=True)

        solicitar_verificacion_vendedor(vendor_prueba, mensaje="Vendo hace 5 años")

        assert vendor_prueba.solicitud_verificacion_mensaje == "Vendo hace 5 años"


class TestSolicitarPlanPlus:
    """Tests de `solicitar_plan_plus`."""

    def test_meses_invalidos_lanza_error(self, vendor_prueba):
        with pytest.raises(SolicitudPlanInvalidaError):
            solicitar_plan_plus(
                vendor_prueba, meses=2, mensaje="Pago móvil", comprobante_url="https://r2.example.com/c.jpg"
            )

    def test_mensaje_vacio_lanza_error(self, vendor_prueba):
        with pytest.raises(SolicitudPlanInvalidaError):
            solicitar_plan_plus(
                vendor_prueba, meses=1, mensaje="   ", comprobante_url="https://r2.example.com/c.jpg"
            )

    def test_comprobante_vacio_lanza_error(self, vendor_prueba):
        with pytest.raises(SolicitudPlanInvalidaError):
            solicitar_plan_plus(vendor_prueba, meses=1, mensaje="Pago móvil", comprobante_url="")

    def test_exitoso_guarda_solicitud_y_manda_correo(self, db, vendor_prueba, monkeypatch):
        llamadas = _correo_falso(monkeypatch)

        solicitar_plan_plus(
            vendor_prueba, meses=3, mensaje="Pago móvil, ref 123", comprobante_url="https://r2.example.com/c.jpg"
        )

        assert vendor_prueba.solicitud_plan_meses == 3
        assert vendor_prueba.solicitud_plan_mensaje == "Pago móvil, ref 123"
        assert vendor_prueba.solicitud_plan_comprobante_url == "https://r2.example.com/c.jpg"
        assert vendor_prueba.solicitud_plan_en is not None
        assert len(llamadas) == 1
        assert llamadas[0]["destinatario"] == "info@eservicios.org"

    def test_error_de_envio_no_rompe_la_solicitud(self, db, vendor_prueba, monkeypatch):
        _correo_falso(monkeypatch, falla=True)

        solicitar_plan_plus(
            vendor_prueba, meses=1, mensaje="Pago móvil", comprobante_url="https://r2.example.com/c.jpg"
        )

        assert vendor_prueba.solicitud_plan_meses == 1


class TestPlanPlusVigente:
    """Tests de `plan_plus_vigente`."""

    def test_plan_free_no_vigente(self, vendor_prueba):
        assert plan_plus_vigente(vendor_prueba) is False

    def test_plan_plus_sin_fecha_de_vencimiento_vigente(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba, dias_restantes=None)
        assert plan_plus_vigente(vendor_prueba) is True

    def test_plan_plus_con_fecha_futura_vigente(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba, dias_restantes=10)
        assert plan_plus_vigente(vendor_prueba) is True

    def test_plan_plus_con_fecha_pasada_no_vigente(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba, dias_restantes=-1)
        assert plan_plus_vigente(vendor_prueba) is False


class TestPlanesPlusConPrecio:
    """Tests de `planes_plus_con_precio`."""

    def test_devuelve_una_entrada_por_cada_duracion(self):
        planes = planes_plus_con_precio()
        assert {p["meses"] for p in planes} == MESES_PLAN_SOLICITABLES
        assert [p["meses"] for p in planes] == sorted(MESES_PLAN_SOLICITABLES)

    def test_plan_de_1_mes_sin_ahorro(self):
        planes = planes_plus_con_precio()
        plan_1_mes = next(p for p in planes if p["meses"] == 1)
        assert plan_1_mes["ahorro_pct"] is None
        assert plan_1_mes["destacado"] is False

    def test_plan_de_12_meses_destacado_y_con_ahorro(self):
        planes = planes_plus_con_precio()
        plan_12_meses = next(p for p in planes if p["meses"] == 12)
        assert plan_12_meses["destacado"] is True
        assert plan_12_meses["ahorro_pct"] > 0


class TestPruebaPlusExpiraEn:
    """Tests de `prueba_plus_expira_en`."""

    def test_nunca_activada_devuelve_none(self, vendor_prueba):
        assert prueba_plus_expira_en(vendor_prueba) is None

    def test_activada_devuelve_fecha_mas_dias_de_prueba(self, db, vendor_prueba):
        ahora = datetime.utcnow()
        vendor_prueba.prueba_plus_activada_en = ahora
        db.session.commit()

        esperado = ahora + timedelta(days=DIAS_PRUEBA_PLUS)
        assert abs((prueba_plus_expira_en(vendor_prueba) - esperado).total_seconds()) < 1


class TestPruebaPlusVigente:
    """Tests de `prueba_plus_vigente`."""

    def test_nunca_activada_no_vigente(self, vendor_prueba):
        assert prueba_plus_vigente(vendor_prueba) is False

    def test_activada_recientemente_vigente(self, db, vendor_prueba):
        vendor_prueba.prueba_plus_activada_en = datetime.utcnow()
        db.session.commit()
        assert prueba_plus_vigente(vendor_prueba) is True

    def test_activada_hace_mas_de_los_dias_de_prueba_no_vigente(self, db, vendor_prueba):
        vendor_prueba.prueba_plus_activada_en = datetime.utcnow() - timedelta(days=DIAS_PRUEBA_PLUS + 1)
        db.session.commit()
        assert prueba_plus_vigente(vendor_prueba) is False


class TestPruebaPlusDisponible:
    """Tests de `prueba_plus_disponible`."""

    def test_nunca_activada_disponible(self, vendor_prueba):
        assert prueba_plus_disponible(vendor_prueba) is True

    def test_ya_usada_no_disponible_aunque_ya_haya_vencido(self, db, vendor_prueba):
        vendor_prueba.prueba_plus_activada_en = datetime.utcnow() - timedelta(days=DIAS_PRUEBA_PLUS + 1)
        db.session.commit()
        assert prueba_plus_disponible(vendor_prueba) is False


class TestPlanPlusOPruebaVigente:
    """Tests de `plan_plus_o_prueba_vigente`."""

    def test_sin_plan_ni_prueba_false(self, vendor_prueba):
        assert plan_plus_o_prueba_vigente(vendor_prueba) is False

    def test_con_plan_plus_vigente_true(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        assert plan_plus_o_prueba_vigente(vendor_prueba) is True

    def test_con_prueba_vigente_true(self, db, vendor_prueba):
        vendor_prueba.prueba_plus_activada_en = datetime.utcnow()
        db.session.commit()
        assert plan_plus_o_prueba_vigente(vendor_prueba) is True


class TestActivarPruebaPlus:
    """Tests de `activar_prueba_plus`."""

    def test_activa_la_prueba(self, db, vendor_prueba):
        assert vendor_prueba.prueba_plus_activada_en is None
        activar_prueba_plus(vendor_prueba)
        assert vendor_prueba.prueba_plus_activada_en is not None

    def test_ya_usada_lanza_error(self, db, vendor_prueba):
        activar_prueba_plus(vendor_prueba)
        with pytest.raises(PruebaPlusInvalidaError):
            activar_prueba_plus(vendor_prueba)

    def test_con_plus_real_vigente_lanza_error(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        with pytest.raises(PruebaPlusInvalidaError):
            activar_prueba_plus(vendor_prueba)


class TestCambiarPassword:
    """Tests de `cambiar_password`."""

    def test_cambia_la_password_correctamente(self, db, vendor_prueba):
        cambiar_password(vendor_prueba, password_actual="clave-de-prueba-123", password_nueva="nueva-clave-456")
        assert vendor_prueba.check_password("nueva-clave-456") is True

    def test_password_actual_incorrecta_lanza_error(self, vendor_prueba):
        with pytest.raises(PasswordActualIncorrectaError):
            cambiar_password(vendor_prueba, password_actual="clave-equivocada", password_nueva="nueva-clave-456")

    def test_password_nueva_muy_corta_lanza_error(self, vendor_prueba):
        with pytest.raises(PasswordNuevaInvalidaError):
            cambiar_password(vendor_prueba, password_actual="clave-de-prueba-123", password_nueva="corta")

    def test_sin_password_previa_crea_una_ignorando_la_actual(self, db, vendor_prueba):
        vendor_prueba.password_hash = None
        db.session.commit()

        cambiar_password(vendor_prueba, password_actual="lo-que-sea", password_nueva="nueva-clave-456")

        assert vendor_prueba.check_password("nueva-clave-456") is True
