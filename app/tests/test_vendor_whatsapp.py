"""Tests de los links de WhatsApp y el vCard de la tienda.

Cubre el bloque "WhatsApp/vCard" del split de god-files: los helpers de
`construir_whatsapp_href`/`href_whatsapp_*`/`construir_mensaje_consulta_multiple`
(mensajes de WhatsApp prellenados, siempre armados en el servidor, nunca
en el template ni en JS) y `construir_vcard`/`_escapar_texto_vcard` (el
archivo .vcf que el vendedor descarga junto al QR), más la ruta
`/vendedor/contacto.vcf` que usa `construir_vcard`.
"""
from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

import pytest

from app.models import PlanVendor, VendorProduct
from app.services.vendor_whatsapp_service import (
    _escapar_texto_vcard,
    _membrete_trazabilidad,
    construir_mensaje_consulta_multiple,
    construir_vcard,
    construir_whatsapp_href,
    href_whatsapp_producto,
    href_whatsapp_soporte_pago,
    href_whatsapp_tienda,
    resolver_consulta_multiple_habilitada,
)


def _crear_producto(db, vendor, *, titulo: str = "Producto de prueba") -> VendorProduct:
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo,
        descripcion="Descripción de prueba",
        precio=Decimal("10.00"),
    )
    db.session.add(producto)
    db.session.commit()
    return producto


@pytest.fixture
def producto_prueba(db, vendor_prueba):
    """Producto descartable de `vendor_prueba` (se borra en cascada con el vendor)."""
    return _crear_producto(db, vendor_prueba)


class TestConstruirWhatsappHref:
    """Tests de `construir_whatsapp_href`, el helper base de todos los links `wa.me`."""

    def test_arma_url_wa_me_con_numero(self):
        href = construir_whatsapp_href("+50212345678", "Hola")

        assert href.startswith("https://wa.me/+50212345678?text=")

    def test_codifica_el_mensaje_como_url(self):
        mensaje = "Hola, ¿cómo estás? / precio & disponibilidad"

        href = construir_whatsapp_href("+50212345678", mensaje)

        assert href == f"https://wa.me/+50212345678?text={quote(mensaje)}"


class TestMembreteTrazabilidad:
    """Tests del membrete "— vía <slug>.eservicios.org" agregado a todo mensaje."""

    def test_incluye_el_slug_del_vendor(self, vendor_prueba):
        membrete = _membrete_trazabilidad(vendor_prueba)

        assert f"{vendor_prueba.slug}.eservicios.org" in membrete
        assert membrete.startswith("\n\n")


class TestHrefWhatsappTienda:
    """Tests de `href_whatsapp_tienda`, el botón general de contacto de la tienda."""

    def test_incluye_nombre_del_negocio_y_membrete(self, vendor_prueba):
        href = href_whatsapp_tienda(vendor_prueba)

        assert href.startswith(f"https://wa.me/{vendor_prueba.whatsapp_numero}?text=")
        assert quote(vendor_prueba.nombre_negocio) in href
        assert quote(vendor_prueba.slug) in href


class TestHrefWhatsappProducto:
    """Tests de `href_whatsapp_producto`, el botón de consulta de un producto puntual."""

    def test_incluye_titulo_del_producto_y_membrete(self, vendor_prueba, producto_prueba):
        href = href_whatsapp_producto(vendor_prueba, producto_prueba)

        assert href.startswith(f"https://wa.me/{vendor_prueba.whatsapp_numero}?text=")
        assert quote(producto_prueba.titulo) in href
        assert quote(vendor_prueba.slug) in href


class TestHrefWhatsappSoportePago:
    """Tests de `href_whatsapp_soporte_pago`, el link fijo de soporte de eServicios (no del vendedor)."""

    def test_usa_solo_digitos_del_numero_de_soporte(self):
        href = href_whatsapp_soporte_pago()

        numero = href.removeprefix("https://wa.me/").split("?text=")[0]
        assert numero.isdigit()
        assert len(numero) > 5

    def test_no_depende_del_vendor(self):
        # A propósito no recibe ningún Vendor: es el contacto general de
        # eServicios, no el `whatsapp_numero` de una tienda.
        href_1 = href_whatsapp_soporte_pago()
        href_2 = href_whatsapp_soporte_pago()

        assert href_1 == href_2


class TestResolverConsultaMultipleHabilitada:
    """Tests de la puerta de la consulta combinada de varios productos (e-link Plus)."""

    def test_false_para_tienda_sin_plus(self, vendor_prueba):
        assert resolver_consulta_multiple_habilitada(vendor_prueba) is False

    def test_true_con_plan_plus_vigente(self, db, vendor_prueba):
        vendor_prueba.plan = PlanVendor.PLUS
        vendor_prueba.plan_expira_en = None
        db.session.commit()

        assert resolver_consulta_multiple_habilitada(vendor_prueba) is True

    def test_true_con_prueba_plus_vigente(self, db, vendor_prueba):
        from datetime import datetime

        vendor_prueba.prueba_plus_activada_en = datetime.utcnow()
        db.session.commit()

        assert resolver_consulta_multiple_habilitada(vendor_prueba) is True

    def test_false_con_plan_plus_vencido_y_sin_prueba(self, db, vendor_prueba):
        from datetime import datetime, timedelta

        vendor_prueba.plan = PlanVendor.PLUS
        vendor_prueba.plan_expira_en = datetime.utcnow() - timedelta(days=1)
        db.session.commit()

        assert resolver_consulta_multiple_habilitada(vendor_prueba) is False


class TestConstruirMensajeConsultaMultiple:
    """Tests del mensaje combinado de varios productos seleccionados."""

    def test_lista_un_producto_por_linea(self, db, vendor_prueba):
        producto_1 = _crear_producto(db, vendor_prueba, titulo="Producto 1")
        producto_2 = _crear_producto(db, vendor_prueba, titulo="Producto 2")

        mensaje = construir_mensaje_consulta_multiple(vendor_prueba, [producto_1, producto_2])

        assert "- Producto 1" in mensaje
        assert "- Producto 2" in mensaje
        assert vendor_prueba.nombre_negocio in mensaje

    def test_incluye_membrete_de_trazabilidad(self, db, vendor_prueba, producto_prueba):
        mensaje = construir_mensaje_consulta_multiple(vendor_prueba, [producto_prueba])

        assert f"{vendor_prueba.slug}.eservicios.org" in mensaje


class TestEscaparTextoVcard:
    """Tests del escape de caracteres especiales del formato vCard."""

    def test_escapa_backslash_punto_y_coma_coma_y_salto_de_linea(self):
        assert _escapar_texto_vcard("a\\b;c,d\ne") == "a\\\\b\\;c\\,d\\ne"

    def test_texto_sin_caracteres_especiales_no_cambia(self):
        assert _escapar_texto_vcard("Texto normal") == "Texto normal"


class TestConstruirVcard:
    """Tests del contenido del archivo vCard (.vcf) de la tienda."""

    def test_incluye_campos_basicos(self, vendor_prueba):
        vcard = construir_vcard(vendor_prueba)

        assert vcard.startswith("BEGIN:VCARD\r\nVERSION:3.0\r\n")
        assert f"FN:{vendor_prueba.nombre_negocio}" in vcard
        assert f"TEL;TYPE=CELL:{vendor_prueba.whatsapp_numero}" in vcard
        assert f"URL:https://{vendor_prueba.slug}.eservicios.org" in vcard
        assert vcard.endswith("END:VCARD")

    def test_sin_bio_no_incluye_note(self, db, vendor_prueba):
        vendor_prueba.bio = None
        db.session.commit()

        vcard = construir_vcard(vendor_prueba)

        assert "NOTE:" not in vcard

    def test_con_bio_incluye_note_escapado(self, db, vendor_prueba):
        vendor_prueba.bio = "Ropa; accesorios, más"
        db.session.commit()

        vcard = construir_vcard(vendor_prueba)

        assert "NOTE:Ropa\\; accesorios\\, más" in vcard


class TestRutaContactoVcard:
    """Tests de la ruta `/vendedor/contacto.vcf`."""

    def test_sin_login_redirige_a_login(self, client):
        respuesta = client.get("/vendedor/contacto.vcf")

        assert respuesta.status_code == 302
        assert "/e-link/login" in respuesta.headers["Location"]

    def test_con_login_descarga_vcard(self, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.get("/vendedor/contacto.vcf")

        assert respuesta.status_code == 200
        assert respuesta.mimetype == "text/vcard"
        assert f'filename="{vendor_prueba.slug}.vcf"' in respuesta.headers["Content-Disposition"]
        assert b"BEGIN:VCARD" in respuesta.data
