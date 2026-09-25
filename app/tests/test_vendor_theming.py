"""Tests de la personalización de e-link Plus: acento, plantilla, badges, stock, categorías.

Cubre el bloque "Theming" del split de god-files: los `resolver_*`
(punto único de entrada para cada función Plus, siempre gateados por
`plan_plus_o_prueba_vigente`) y los helpers de color `_contraste_legible`/
`_oscurecer_color`. `routes/tienda.py` y `routes/vendedor.py` son los
únicos consumidores reales (el resto de referencias en el repo son solo
comentarios de documentación).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import PlanVendor, VendorProduct
from app.services.vendor_theming_service import (
    _contraste_legible,
    _oscurecer_color,
    listar_paleta_acento,
    resolver_acento_vendor,
    resolver_badge_producto,
    resolver_categorias_producto,
    resolver_cupon_vendor,
    resolver_disponibilidad_vendor,
    resolver_estado_stock_producto,
    resolver_plantilla_vendor,
)
from app.services.vendor_categoria_service import crear_categoria


def _activar_plus(db, vendor) -> None:
    vendor.plan = PlanVendor.PLUS
    vendor.plan_expira_en = None
    db.session.commit()


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


class TestContrasteLegible:
    """Tests de `_contraste_legible`, la elección de texto claro/oscuro sobre un color."""

    def test_color_claro_devuelve_texto_oscuro(self):
        assert _contraste_legible("#ffffff") == "#111111"

    def test_color_oscuro_devuelve_texto_claro(self):
        assert _contraste_legible("#000000") == "#ffffff"


class TestOscurecerColor:
    """Tests de `_oscurecer_color`, el segundo tono del degradado."""

    def test_oscurece_hacia_el_negro_segun_el_factor(self):
        assert _oscurecer_color("#ffffff", factor=0.5) == "#808080"

    def test_factor_cero_no_cambia_el_color(self):
        assert _oscurecer_color("#2563eb", factor=0) == "#2563eb"


class TestResolverAcentoVendor:
    """Tests de `resolver_acento_vendor`, que nunca devuelve None."""

    def test_sin_color_guardado_usa_el_azul_por_defecto(self, vendor_prueba):
        acento = resolver_acento_vendor(vendor_prueba)

        assert acento["color"] == "#2563eb"
        assert acento["contraste"] in ("#111111", "#ffffff")
        assert acento["gradiente_fin"] != acento["color"]

    def test_plan_gratis_con_color_de_la_paleta_gratis_lo_respeta(self, db, vendor_prueba):
        vendor_prueba.color_acento = "#ec4899"
        db.session.commit()

        acento = resolver_acento_vendor(vendor_prueba)

        assert acento["color"] == "#ec4899"

    def test_plan_gratis_con_color_exclusivo_de_plus_cae_al_default(self, db, vendor_prueba):
        vendor_prueba.color_acento = "#059669"  # verde, solo Plus
        db.session.commit()

        acento = resolver_acento_vendor(vendor_prueba)

        assert acento["color"] == "#2563eb"

    def test_con_plus_vigente_respeta_cualquier_hex_valido(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.color_acento = "#059669"
        db.session.commit()

        acento = resolver_acento_vendor(vendor_prueba)

        assert acento["color"] == "#059669"

    def test_color_con_formato_invalido_cae_al_default(self, db, vendor_prueba):
        vendor_prueba.color_acento = "#zzzzzz"  # 7 chars (cabe en la columna), no es hex válido
        db.session.commit()

        acento = resolver_acento_vendor(vendor_prueba)

        assert acento["color"] == "#2563eb"


class TestResolverCuponVendor:
    """Tests de `resolver_cupon_vendor`."""

    def test_sin_cupon_guardado_devuelve_none(self, vendor_prueba):
        assert resolver_cupon_vendor(vendor_prueba) is None

    def test_con_cupon_pero_sin_plus_devuelve_none(self, db, vendor_prueba):
        vendor_prueba.cupon = "BIENVENIDA10"
        db.session.commit()

        assert resolver_cupon_vendor(vendor_prueba) is None

    def test_con_cupon_y_plus_devuelve_el_texto(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.cupon = "BIENVENIDA10"
        db.session.commit()

        assert resolver_cupon_vendor(vendor_prueba) == "BIENVENIDA10"


class TestListarPaletaAcento:
    """Tests de `listar_paleta_acento`."""

    def test_plan_gratis_devuelve_dos_colores(self):
        paleta = listar_paleta_acento(plan_plus_activo=False)

        assert paleta == ["#2563eb", "#ec4899"]

    def test_plan_plus_devuelve_paleta_completa(self):
        paleta = listar_paleta_acento(plan_plus_activo=True)

        assert len(paleta) == 8
        assert paleta[:2] == ["#2563eb", "#ec4899"]


class TestResolverPlantillaVendor:
    """Tests de `resolver_plantilla_vendor`."""

    def test_sin_plantilla_guardada_devuelve_clasica(self, vendor_prueba):
        assert resolver_plantilla_vendor(vendor_prueba) == "clasica"

    def test_con_plantilla_pero_sin_plus_devuelve_clasica(self, db, vendor_prueba):
        vendor_prueba.plantilla = "editorial"
        db.session.commit()

        assert resolver_plantilla_vendor(vendor_prueba) == "clasica"

    def test_con_plantilla_valida_y_plus_devuelve_la_guardada(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.plantilla = "editorial"
        db.session.commit()

        assert resolver_plantilla_vendor(vendor_prueba) == "editorial"

    def test_plantilla_invalida_con_plus_devuelve_clasica(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.plantilla = "no-existe"  # cabe en la columna, no es una clave válida
        db.session.commit()

        assert resolver_plantilla_vendor(vendor_prueba) == "clasica"


class TestResolverBadgeProducto:
    """Tests de `resolver_badge_producto`."""

    def test_sin_badge_guardado_devuelve_none(self, vendor_prueba, producto_prueba):
        assert resolver_badge_producto(vendor_prueba, producto_prueba) is None

    def test_con_badge_pero_sin_plus_devuelve_none(self, db, vendor_prueba, producto_prueba):
        producto_prueba.badge = "mas_vendido"
        db.session.commit()

        assert resolver_badge_producto(vendor_prueba, producto_prueba) is None

    def test_con_badge_valido_y_plus_devuelve_diccionario(self, db, vendor_prueba, producto_prueba):
        _activar_plus(db, vendor_prueba)
        producto_prueba.badge = "mas_vendido"
        db.session.commit()

        badge = resolver_badge_producto(vendor_prueba, producto_prueba)

        assert badge is not None
        assert badge["clave"] == "mas_vendido"


class TestResolverDisponibilidadVendor:
    """Tests de `resolver_disponibilidad_vendor`."""

    def test_sin_plus_devuelve_none(self, vendor_prueba):
        assert resolver_disponibilidad_vendor(vendor_prueba) is None

    def test_con_plus_devuelve_el_interruptor_guardado(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        vendor_prueba.disponible_ahora = True
        db.session.commit()

        assert resolver_disponibilidad_vendor(vendor_prueba) is True

        vendor_prueba.disponible_ahora = False
        db.session.commit()

        assert resolver_disponibilidad_vendor(vendor_prueba) is False


class TestResolverEstadoStockProducto:
    """Tests de `resolver_estado_stock_producto`."""

    def test_sin_estado_guardado_devuelve_none(self, vendor_prueba, producto_prueba):
        assert resolver_estado_stock_producto(vendor_prueba, producto_prueba) is None

    def test_con_estado_pero_sin_plus_devuelve_none(self, db, vendor_prueba, producto_prueba):
        producto_prueba.estado_stock = "agotado"
        db.session.commit()

        assert resolver_estado_stock_producto(vendor_prueba, producto_prueba) is None

    def test_con_estado_valido_y_plus_devuelve_diccionario(self, db, vendor_prueba, producto_prueba):
        _activar_plus(db, vendor_prueba)
        producto_prueba.estado_stock = "agotado"
        db.session.commit()

        estado = resolver_estado_stock_producto(vendor_prueba, producto_prueba)

        assert estado is not None
        assert estado["clave"] == "agotado"


class TestResolverCategoriasProducto:
    """Tests de `resolver_categorias_producto`."""

    def test_sin_plus_devuelve_lista_vacia(self, db, vendor_prueba):
        crear_categoria(vendor_prueba, nombre="Ropa")

        assert resolver_categorias_producto(vendor_prueba) == []

    def test_con_plus_devuelve_las_categorias_de_la_tienda(self, db, vendor_prueba):
        _activar_plus(db, vendor_prueba)
        crear_categoria(vendor_prueba, nombre="Ropa")
        crear_categoria(vendor_prueba, nombre="Calzado")

        categorias = resolver_categorias_producto(vendor_prueba)

        assert {c.nombre for c in categorias} == {"Ropa", "Calzado"}


class TestRutaPerfilUsaTheming:
    """Sanity check de que el panel sigue funcionando con el bloque ya separado."""

    def test_perfil_con_login_devuelve_200(self, sesion_vendor):
        respuesta = sesion_vendor.get("/vendedor/perfil")

        assert respuesta.status_code == 200
