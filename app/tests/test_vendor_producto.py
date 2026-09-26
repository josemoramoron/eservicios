"""Tests de caracterización para el bloque "Productos" de vendor_service.py.

Escritos ANTES de mover nada (metodología "tests por bloque,
intercalado" que venimos usando en todo el split de vendor_service.py):
corren contra el código actual, sin tocar nada, para fijar el
comportamiento de hoy como baseline antes de renombrar el archivo a
vendor_producto_service.py (este es el último bloque — con este,
vendor_service.py como god-file desaparece del todo).

Cubre: listar_productos_de_vendor, listar_productos_activos,
obtener_producto_de_vendor, crear_producto, actualizar_producto,
eliminar_producto (y de forma indirecta, a través de estas, los
helpers privados _establecer_fotos_producto y _categoria_id_valida).
"""
from __future__ import annotations

from decimal import Decimal

from app.models import VendorCategoria, VendorProduct
from app.services.vendor_producto_service import (
    MAX_FOTOS_PRODUCTO,
    actualizar_producto,
    crear_producto,
    eliminar_producto,
    listar_productos_activos,
    listar_productos_de_vendor,
    obtener_producto_de_vendor,
)


def _crear_producto_directo(db, vendor, *, titulo="Producto de prueba", activo=True, precio="10.00"):
    """Crea un VendorProduct directo (sin pasar por crear_producto), para
    tests de las funciones de lectura que no necesitan ejercitar el CRUD."""
    producto = VendorProduct(
        vendor_id=vendor.id,
        titulo=titulo,
        descripcion="Descripción de prueba",
        precio=Decimal(precio),
        activo=activo,
    )
    db.session.add(producto)
    db.session.commit()
    return producto


def _crear_categoria(db, vendor, *, nombre="Categoría de prueba"):
    """Crea una VendorCategoria descartable para probar categoria_id."""
    categoria = VendorCategoria(vendor_id=vendor.id, nombre=nombre)
    db.session.add(categoria)
    db.session.commit()
    return categoria


class TestListarProductosDeVendor:
    """listar_productos_de_vendor: todos los productos (activos e
    inactivos) de una tienda, para el panel."""

    def test_devuelve_lista_vacia_sin_productos(self, db, vendor_prueba):
        assert listar_productos_de_vendor(vendor_prueba) == []

    def test_incluye_activos_e_inactivos(self, db, vendor_prueba):
        activo = _crear_producto_directo(db, vendor_prueba, titulo="Activo", activo=True)
        inactivo = _crear_producto_directo(db, vendor_prueba, titulo="Inactivo", activo=False)

        resultado = listar_productos_de_vendor(vendor_prueba)

        ids = {p.id for p in resultado}
        assert ids == {activo.id, inactivo.id}

    def test_orden_descendente_por_id(self, db, vendor_prueba):
        primero = _crear_producto_directo(db, vendor_prueba, titulo="Primero")
        segundo = _crear_producto_directo(db, vendor_prueba, titulo="Segundo")

        resultado = listar_productos_de_vendor(vendor_prueba)

        assert [p.id for p in resultado] == [segundo.id, primero.id]

    def test_no_incluye_productos_de_otro_vendor(self, db, vendor_prueba, otro_vendor_prueba):
        _crear_producto_directo(db, otro_vendor_prueba, titulo="Ajeno")

        assert listar_productos_de_vendor(vendor_prueba) == []


class TestListarProductosActivos:
    """listar_productos_activos: solo los activos, para la tienda pública."""

    def test_devuelve_lista_vacia_sin_productos(self, db, vendor_prueba):
        assert listar_productos_activos(vendor_prueba) == []

    def test_excluye_inactivos(self, db, vendor_prueba):
        activo = _crear_producto_directo(db, vendor_prueba, titulo="Activo", activo=True)
        _crear_producto_directo(db, vendor_prueba, titulo="Inactivo", activo=False)

        resultado = listar_productos_activos(vendor_prueba)

        assert [p.id for p in resultado] == [activo.id]

    def test_orden_descendente_por_id(self, db, vendor_prueba):
        primero = _crear_producto_directo(db, vendor_prueba, titulo="Primero")
        segundo = _crear_producto_directo(db, vendor_prueba, titulo="Segundo")

        resultado = listar_productos_activos(vendor_prueba)

        assert [p.id for p in resultado] == [segundo.id, primero.id]

    def test_no_incluye_productos_de_otro_vendor(self, db, vendor_prueba, otro_vendor_prueba):
        _crear_producto_directo(db, otro_vendor_prueba, titulo="Ajeno")

        assert listar_productos_activos(vendor_prueba) == []


class TestObtenerProductoDeVendor:
    """obtener_producto_de_vendor: busca por id verificando pertenencia."""

    def test_encuentra_producto_propio(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)

        resultado = obtener_producto_de_vendor(vendor_prueba, producto.id)

        assert resultado is not None
        assert resultado.id == producto.id

    def test_none_si_no_existe(self, db, vendor_prueba):
        assert obtener_producto_de_vendor(vendor_prueba, 999999) is None

    def test_none_si_pertenece_a_otro_vendor(self, db, vendor_prueba, otro_vendor_prueba):
        producto_ajeno = _crear_producto_directo(db, otro_vendor_prueba)

        assert obtener_producto_de_vendor(vendor_prueba, producto_ajeno.id) is None


class TestCrearProducto:
    """crear_producto: alta directa, sin moderación (activo de inmediato)."""

    def test_crea_con_datos_minimos(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Silla de oficina",
            descripcion="Cómoda y ajustable",
            precio=Decimal("150.00"),
        )

        assert producto.id is not None
        assert producto.vendor_id == vendor_prueba.id
        assert producto.titulo == "Silla de oficina"
        assert producto.descripcion == "Cómoda y ajustable"
        assert producto.precio == Decimal("150.00")
        assert producto.activo is True
        assert producto.badge is None
        assert producto.estado_stock is None
        assert producto.categoria_id is None
        assert producto.foto_url is None
        assert producto.fotos == []

    def test_recorta_espacios_en_titulo_y_descripcion(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="  Mesa de centro  ",
            descripcion="  De madera  ",
            precio=Decimal("80.00"),
        )

        assert producto.titulo == "Mesa de centro"
        assert producto.descripcion == "De madera"

    def test_badge_valido_se_guarda(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            badge="oferta",
        )

        assert producto.badge == "oferta"

    def test_badge_invalido_se_descarta(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            badge="no_existe",
        )

        assert producto.badge is None

    def test_estado_stock_valido_se_guarda(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            estado_stock="agotado",
        )

        assert producto.estado_stock == "agotado"

    def test_estado_stock_invalido_se_descarta(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            estado_stock="no_existe",
        )

        assert producto.estado_stock is None

    def test_categoria_propia_se_guarda(self, db, vendor_prueba):
        categoria = _crear_categoria(db, vendor_prueba)

        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            categoria_id=categoria.id,
        )

        assert producto.categoria_id == categoria.id

    def test_categoria_de_otro_vendor_se_descarta(self, db, vendor_prueba, otro_vendor_prueba):
        categoria_ajena = _crear_categoria(db, otro_vendor_prueba)

        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            categoria_id=categoria_ajena.id,
        )

        assert producto.categoria_id is None

    def test_categoria_inexistente_se_descarta(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            categoria_id=999999,
        )

        assert producto.categoria_id is None

    def test_fotos_se_guardan_en_orden(self, db, vendor_prueba):
        urls = ["https://x/1.jpg", "https://x/2.jpg", "https://x/3.jpg"]

        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            fotos_urls=urls,
        )

        assert [f.url for f in sorted(producto.fotos, key=lambda f: f.orden)] == urls
        assert [f.orden for f in sorted(producto.fotos, key=lambda f: f.orden)] == [0, 1, 2]

    def test_foto_url_es_la_primera_foto(self, db, vendor_prueba):
        urls = ["https://x/1.jpg", "https://x/2.jpg"]

        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            fotos_urls=urls,
        )

        assert producto.foto_url == "https://x/1.jpg"

    def test_fotos_se_truncan_a_max_fotos_producto(self, db, vendor_prueba):
        urls = [f"https://x/{i}.jpg" for i in range(MAX_FOTOS_PRODUCTO + 3)]

        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            fotos_urls=urls,
        )

        assert len(producto.fotos) == MAX_FOTOS_PRODUCTO
        assert [f.url for f in sorted(producto.fotos, key=lambda f: f.orden)] == urls[:MAX_FOTOS_PRODUCTO]

    def test_sin_fotos_foto_url_es_none(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
            fotos_urls=[],
        )

        assert producto.foto_url is None
        assert producto.fotos == []

    def test_queda_activo_de_inmediato(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Lámpara",
            descripcion="LED",
            precio=Decimal("25.00"),
        )

        assert producto.activo is True


class TestActualizarProducto:
    """actualizar_producto: reemplaza los datos de un producto existente."""

    def test_actualiza_titulo_descripcion_precio(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba, titulo="Antes")

        actualizar_producto(
            producto,
            titulo="  Después  ",
            descripcion="  Nueva descripción  ",
            precio=Decimal("99.99"),
            fotos_urls=None,
            activo=True,
        )

        assert producto.titulo == "Después"
        assert producto.descripcion == "Nueva descripción"
        assert producto.precio == Decimal("99.99")

    def test_puede_desactivar(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba, activo=True)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=False,
        )

        assert producto.activo is False

    def test_puede_reactivar(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba, activo=False)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
        )

        assert producto.activo is True

    def test_badge_invalido_se_descarta(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            badge="no_existe",
        )

        assert producto.badge is None

    def test_badge_valido_se_guarda(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            badge="nuevo",
        )

        assert producto.badge == "nuevo"

    def test_estado_stock_valido_se_guarda(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            estado_stock="pocas_unidades",
        )

        assert producto.estado_stock == "pocas_unidades"

    def test_estado_stock_invalido_se_descarta(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            estado_stock="no_existe",
        )

        assert producto.estado_stock is None

    def test_categoria_propia_se_guarda(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)
        categoria = _crear_categoria(db, vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            categoria_id=categoria.id,
        )

        assert producto.categoria_id == categoria.id

    def test_categoria_de_otro_vendor_se_descarta(self, db, vendor_prueba, otro_vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)
        categoria_ajena = _crear_categoria(db, otro_vendor_prueba)

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
            categoria_id=categoria_ajena.id,
        )

        assert producto.categoria_id is None

    def test_reemplaza_fotos_existentes(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Original",
            descripcion="Descripción",
            precio=Decimal("10.00"),
            fotos_urls=["https://x/vieja.jpg"],
        )

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=["https://x/nueva1.jpg", "https://x/nueva2.jpg"],
            activo=True,
        )

        urls = [f.url for f in sorted(producto.fotos, key=lambda f: f.orden)]
        assert urls == ["https://x/nueva1.jpg", "https://x/nueva2.jpg"]
        assert producto.foto_url == "https://x/nueva1.jpg"

    def test_fotos_none_deja_galeria_vacia(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Original",
            descripcion="Descripción",
            precio=Decimal("10.00"),
            fotos_urls=["https://x/vieja.jpg"],
        )

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=None,
            activo=True,
        )

        assert producto.fotos == []
        assert producto.foto_url is None

    def test_fotos_se_truncan_a_max_fotos_producto(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)
        urls = [f"https://x/{i}.jpg" for i in range(MAX_FOTOS_PRODUCTO + 2)]

        actualizar_producto(
            producto,
            titulo=producto.titulo,
            descripcion=producto.descripcion,
            precio=producto.precio,
            fotos_urls=urls,
            activo=True,
        )

        assert len(producto.fotos) == MAX_FOTOS_PRODUCTO


class TestEliminarProducto:
    """eliminar_producto: borrado permanente."""

    def test_borra_el_producto(self, db, vendor_prueba):
        producto = _crear_producto_directo(db, vendor_prueba)
        producto_id = producto.id

        eliminar_producto(producto)

        assert db.session.get(VendorProduct, producto_id) is None

    def test_borra_tambien_sus_fotos(self, db, vendor_prueba):
        producto = crear_producto(
            vendor_prueba,
            titulo="Con fotos",
            descripcion="Descripción",
            precio=Decimal("10.00"),
            fotos_urls=["https://x/1.jpg", "https://x/2.jpg"],
        )
        producto_id = producto.id

        eliminar_producto(producto)

        from app.models import VendorProductFoto

        assert VendorProductFoto.query.filter_by(vendor_product_id=producto_id).all() == []
