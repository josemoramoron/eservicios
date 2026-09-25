"""Tests de la funcionalidad "avísame cuando vuelva" sobre productos agotados.

Cubre tanto el servicio (`crear_aviso_producto`, `listar_avisos_de_vendor`,
por ahora en `vendor_service.py`, bloque "Avisos de producto" del split de
god-files) como las dos rutas que lo usan: el panel `/vendedor/avisos`
(protegido por sesión) y el formulario público `/e-link-aviso/enviar`
(sin sesión de vendedor, resuelto por subdominio del Host).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import VendorProduct, VendorProductAviso
from app.services.vendor_aviso_service import AvisoInvalidoError, crear_aviso_producto, listar_avisos_de_vendor
from app.tests.conftest import CSRF_TOKEN_PRUEBA


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


class TestServicioAvisos:
    """Tests de `crear_aviso_producto` y `listar_avisos_de_vendor`."""

    def test_crear_aviso_producto_guarda_aviso(self, db, producto_prueba):
        aviso = crear_aviso_producto(producto_prueba, nombre="Ana Pérez", contacto="ana@example.com")

        assert aviso.id is not None
        assert aviso.vendor_product_id == producto_prueba.id
        assert aviso.nombre == "Ana Pérez"
        assert aviso.contacto == "ana@example.com"

    def test_crear_aviso_producto_recorta_espacios(self, db, producto_prueba):
        aviso = crear_aviso_producto(producto_prueba, nombre="  Ana Pérez  ", contacto="  ana@example.com  ")

        assert aviso.nombre == "Ana Pérez"
        assert aviso.contacto == "ana@example.com"

    def test_crear_aviso_producto_nombre_vacio_lanza_error(self, db, producto_prueba):
        with pytest.raises(AvisoInvalidoError):
            crear_aviso_producto(producto_prueba, nombre="", contacto="ana@example.com")

    def test_crear_aviso_producto_nombre_solo_espacios_lanza_error(self, db, producto_prueba):
        with pytest.raises(AvisoInvalidoError):
            crear_aviso_producto(producto_prueba, nombre="   ", contacto="ana@example.com")

    def test_crear_aviso_producto_contacto_vacio_lanza_error(self, db, producto_prueba):
        with pytest.raises(AvisoInvalidoError):
            crear_aviso_producto(producto_prueba, nombre="Ana Pérez", contacto="")

    def test_crear_aviso_producto_contacto_solo_espacios_lanza_error(self, db, producto_prueba):
        with pytest.raises(AvisoInvalidoError):
            crear_aviso_producto(producto_prueba, nombre="Ana Pérez", contacto="   ")

    def test_crear_aviso_producto_error_no_guarda_nada(self, db, producto_prueba):
        with pytest.raises(AvisoInvalidoError):
            crear_aviso_producto(producto_prueba, nombre="", contacto="ana@example.com")

        assert VendorProductAviso.query.filter_by(vendor_product_id=producto_prueba.id).count() == 0

    def test_listar_avisos_de_vendor_vacio_sin_avisos(self, db, vendor_prueba):
        assert listar_avisos_de_vendor(vendor_prueba) == []

    def test_listar_avisos_de_vendor_devuelve_avisos_de_todos_los_productos(self, db, vendor_prueba):
        producto_1 = _crear_producto(db, vendor_prueba, titulo="Producto 1")
        producto_2 = _crear_producto(db, vendor_prueba, titulo="Producto 2")
        crear_aviso_producto(producto_1, nombre="Ana", contacto="ana@example.com")
        crear_aviso_producto(producto_2, nombre="Beto", contacto="beto@example.com")

        avisos = listar_avisos_de_vendor(vendor_prueba)

        assert len(avisos) == 2
        assert {a.nombre for a in avisos} == {"Ana", "Beto"}

    def test_listar_avisos_de_vendor_mas_recientes_primero(self, db, producto_prueba):
        primero = crear_aviso_producto(producto_prueba, nombre="Primero", contacto="1@example.com")
        segundo = crear_aviso_producto(producto_prueba, nombre="Segundo", contacto="2@example.com")

        avisos = listar_avisos_de_vendor(producto_prueba.vendor)

        assert [a.id for a in avisos] == [segundo.id, primero.id]

    def test_listar_avisos_de_vendor_no_incluye_avisos_de_otro_vendor(
        self, db, vendor_prueba, otro_vendor_prueba
    ):
        producto_propio = _crear_producto(db, vendor_prueba)
        producto_ajeno = _crear_producto(db, otro_vendor_prueba)
        crear_aviso_producto(producto_propio, nombre="Propio", contacto="propio@example.com")
        crear_aviso_producto(producto_ajeno, nombre="Ajeno", contacto="ajeno@example.com")

        avisos = listar_avisos_de_vendor(vendor_prueba)

        assert len(avisos) == 1
        assert avisos[0].nombre == "Propio"


class TestRutasAvisos:
    """Tests del panel `/vendedor/avisos` y del formulario público `/e-link-aviso/enviar`."""

    def test_avisos_panel_sin_login_redirige_a_login(self, client):
        respuesta = client.get("/vendedor/avisos")

        assert respuesta.status_code == 302
        assert "/e-link/login" in respuesta.headers["Location"]

    def test_avisos_panel_muestra_avisos_del_vendor(self, db, sesion_vendor, producto_prueba):
        crear_aviso_producto(producto_prueba, nombre="Ana Pérez", contacto="ana@example.com")

        respuesta = sesion_vendor.get("/vendedor/avisos")

        assert respuesta.status_code == 200
        assert b"Ana P\xc3\xa9rez" in respuesta.data or "Ana Pérez".encode() in respuesta.data

    def _host_tienda(self, vendor) -> str:
        return f"{vendor.slug}.eservicios.org"

    def test_enviar_aviso_publico_csrf_invalido_aborta_400(self, client, producto_prueba):
        respuesta = client.post(
            "/e-link-aviso/enviar",
            data={"producto_id": str(producto_prueba.id), "nombre": "Ana", "contacto": "ana@example.com"},
            headers={"Host": self._host_tienda(producto_prueba.vendor)},
        )

        assert respuesta.status_code == 400

    def test_enviar_aviso_publico_vendor_inexistente_404(self, client):
        with client.session_transaction(headers={"Host": "no-existe-esta-tienda.eservicios.org"}) as sess:
            sess["csrf_token"] = CSRF_TOKEN_PRUEBA

        respuesta = client.post(
            "/e-link-aviso/enviar",
            data={"producto_id": "1", "nombre": "Ana", "contacto": "ana@example.com", "csrf_token": CSRF_TOKEN_PRUEBA},
            headers={"Host": "no-existe-esta-tienda.eservicios.org"},
        )

        assert respuesta.status_code == 404

    def test_enviar_aviso_publico_producto_inexistente_404(self, db, client, producto_prueba):
        with client.session_transaction(headers={"Host": self._host_tienda(producto_prueba.vendor)}) as sess:
            sess["csrf_token"] = CSRF_TOKEN_PRUEBA

        respuesta = client.post(
            "/e-link-aviso/enviar",
            data={
                "producto_id": "999999",
                "nombre": "Ana",
                "contacto": "ana@example.com",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
            headers={"Host": self._host_tienda(producto_prueba.vendor)},
        )

        assert respuesta.status_code == 404

    def test_enviar_aviso_publico_nombre_vacio_flash_error_y_redirige(self, db, client, producto_prueba):
        with client.session_transaction(headers={"Host": self._host_tienda(producto_prueba.vendor)}) as sess:
            sess["csrf_token"] = CSRF_TOKEN_PRUEBA

        respuesta = client.post(
            "/e-link-aviso/enviar",
            data={
                "producto_id": str(producto_prueba.id),
                "nombre": "",
                "contacto": "ana@example.com",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
            headers={"Host": self._host_tienda(producto_prueba.vendor)},
            follow_redirects=False,
        )

        assert respuesta.status_code == 302
        assert VendorProductAviso.query.filter_by(vendor_product_id=producto_prueba.id).count() == 0

    def test_enviar_aviso_publico_exitoso_crea_aviso_y_redirige(self, db, client, producto_prueba):
        with client.session_transaction(headers={"Host": self._host_tienda(producto_prueba.vendor)}) as sess:
            sess["csrf_token"] = CSRF_TOKEN_PRUEBA

        respuesta = client.post(
            "/e-link-aviso/enviar",
            data={
                "producto_id": str(producto_prueba.id),
                "nombre": "Ana Pérez",
                "contacto": "ana@example.com",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
            headers={"Host": self._host_tienda(producto_prueba.vendor)},
            follow_redirects=False,
        )

        assert respuesta.status_code == 302
        avisos = VendorProductAviso.query.filter_by(vendor_product_id=producto_prueba.id).all()
        assert len(avisos) == 1
        assert avisos[0].nombre == "Ana Pérez"
