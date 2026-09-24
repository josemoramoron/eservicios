"""Tests de caracterización del bloque "Categorías" de vendor_service.py / vendedor.py.

Se escriben ANTES de partir esos dos god-files (ver .clinerules /
claude/auditoria-deuda-tecnica-2026-09.md) — documentan el
comportamiento actual de este bloque para poder mover el código con
confianza y detectar cualquier regresión. Cuando el split de
"Categorías" a sus propios módulos esté hecho, estos mismos tests
deben seguir pasando sin cambiarles una línea.
"""
from app.models import VendorCategoria
from app.services.vendor_categoria_service import (
    CategoriaInvalidaError,
    actualizar_categoria,
    crear_categoria,
    eliminar_categoria,
    listar_categorias_de_vendor,
    obtener_categoria_de_vendor,
)
from app.tests.conftest import CSRF_TOKEN_PRUEBA


class TestServicioCategorias:
    """Tests directos de las funciones de app/services/vendor_service.py."""

    def test_listar_categorias_vacio_al_inicio(self, db, vendor_prueba):
        assert listar_categorias_de_vendor(vendor_prueba) == []

    def test_crear_categoria_la_agrega_a_la_lista(self, db, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="Electrodomésticos")
        assert categoria.nombre == "Electrodomésticos"
        assert categoria.vendor_id == vendor_prueba.id
        assert categoria.orden == 0
        assert listar_categorias_de_vendor(vendor_prueba) == [categoria]

    def test_crear_categoria_incrementa_orden(self, db, vendor_prueba):
        primera = crear_categoria(vendor_prueba, nombre="Ropa")
        segunda = crear_categoria(vendor_prueba, nombre="Zapatos")
        assert primera.orden == 0
        assert segunda.orden == 1

    def test_crear_categoria_nombre_vacio_lanza_error(self, db, vendor_prueba):
        try:
            crear_categoria(vendor_prueba, nombre="   ")
            assert False, "debía lanzar CategoriaInvalidaError"
        except CategoriaInvalidaError:
            pass
        assert listar_categorias_de_vendor(vendor_prueba) == []

    def test_crear_categoria_nombre_duplicado_lanza_error(self, db, vendor_prueba):
        crear_categoria(vendor_prueba, nombre="Hogar")
        try:
            crear_categoria(vendor_prueba, nombre="hogar")  # sin distinguir mayúsculas
            assert False, "debía lanzar CategoriaInvalidaError"
        except CategoriaInvalidaError:
            pass
        assert len(listar_categorias_de_vendor(vendor_prueba)) == 1

    def test_crear_categoria_mismo_nombre_en_otra_tienda_no_choca(self, db, vendor_prueba, otro_vendor_prueba):
        crear_categoria(vendor_prueba, nombre="Bebidas")
        # El nombre solo debe ser único DENTRO de la misma tienda.
        otra = crear_categoria(otro_vendor_prueba, nombre="Bebidas")
        assert otra.nombre == "Bebidas"

    def test_obtener_categoria_de_vendor_devuelve_none_si_es_de_otra_tienda(
        self, db, vendor_prueba, otro_vendor_prueba
    ):
        categoria = crear_categoria(vendor_prueba, nombre="Muebles")
        assert obtener_categoria_de_vendor(otro_vendor_prueba, categoria.id) is None
        assert obtener_categoria_de_vendor(vendor_prueba, categoria.id) == categoria

    def test_actualizar_categoria_renombra(self, db, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="Antes")
        actualizar_categoria(categoria, nombre="Después")
        assert categoria.nombre == "Después"

    def test_actualizar_categoria_nombre_vacio_lanza_error(self, db, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="Original")
        try:
            actualizar_categoria(categoria, nombre="")
            assert False, "debía lanzar CategoriaInvalidaError"
        except CategoriaInvalidaError:
            pass
        assert categoria.nombre == "Original"

    def test_actualizar_categoria_nombre_duplicado_lanza_error(self, db, vendor_prueba):
        crear_categoria(vendor_prueba, nombre="Uno")
        dos = crear_categoria(vendor_prueba, nombre="Dos")
        try:
            actualizar_categoria(dos, nombre="uno")
            assert False, "debía lanzar CategoriaInvalidaError"
        except CategoriaInvalidaError:
            pass
        assert dos.nombre == "Dos"

    def test_eliminar_categoria_la_saca_de_la_lista(self, db, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="Temporal")
        eliminar_categoria(categoria)
        assert listar_categorias_de_vendor(vendor_prueba) == []
        assert db.session.get(VendorCategoria, categoria.id) is None


class TestRutasCategorias:
    """Tests de las rutas /vendedor/categorias* (app/routes/vendedor.py)."""

    def test_categorias_sin_login_redirige_a_login(self, client):
        respuesta = client.get("/vendedor/categorias")
        assert respuesta.status_code == 302
        # url_for("vendedor.login") resuelve a "/e-link/login" (URL de
        # marca canónica desde el 2026-09-11, ver app/__init__.py) y no
        # a "/vendedor/login" — aunque ese endpoint interno siga
        # llamándose "vendedor.login".
        assert "/e-link/login" in respuesta.headers["Location"]

    def test_categorias_con_login_devuelve_200(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.get("/vendedor/categorias")
        assert respuesta.status_code == 200

    def test_categoria_nueva_sin_csrf_da_400(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post("/vendedor/categorias/nueva", data={"nombre": "Sin CSRF"})
        assert respuesta.status_code == 400
        assert listar_categorias_de_vendor(vendor_prueba) == []

    def test_categoria_nueva_crea_y_redirige(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/categorias/nueva",
            data={"nombre": "Creada por test", "csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].endswith("/vendedor/categorias")
        categorias = listar_categorias_de_vendor(vendor_prueba)
        assert len(categorias) == 1
        assert categorias[0].nombre == "Creada por test"

    def test_categoria_nueva_nombre_vacio_no_crea_nada(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/categorias/nueva",
            data={"nombre": "", "csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 200  # re-renderiza el formulario con el error
        assert listar_categorias_de_vendor(vendor_prueba) == []

    def test_categoria_editar_renombra(self, db, sesion_vendor, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="Nombre viejo")
        respuesta = sesion_vendor.post(
            f"/vendedor/categorias/{categoria.id}/editar",
            data={"nombre": "Nombre nuevo", "csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 302
        assert db.session.get(VendorCategoria, categoria.id).nombre == "Nombre nuevo"

    def test_categoria_editar_de_otra_tienda_da_404(self, db, sesion_vendor, otro_vendor_prueba):
        categoria_ajena = crear_categoria(otro_vendor_prueba, nombre="No es mía")
        respuesta = sesion_vendor.get(f"/vendedor/categorias/{categoria_ajena.id}/editar")
        assert respuesta.status_code == 404

    def test_categoria_eliminar_la_borra(self, db, sesion_vendor, vendor_prueba):
        categoria = crear_categoria(vendor_prueba, nombre="A borrar")
        respuesta = sesion_vendor.post(
            f"/vendedor/categorias/{categoria.id}/eliminar",
            data={"csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 302
        assert listar_categorias_de_vendor(vendor_prueba) == []

    def test_categoria_eliminar_de_otra_tienda_da_404(self, db, sesion_vendor, otro_vendor_prueba):
        categoria_ajena = crear_categoria(otro_vendor_prueba, nombre="No es mía")
        respuesta = sesion_vendor.post(
            f"/vendedor/categorias/{categoria_ajena.id}/eliminar",
            data={"csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 404
        # Sigue existiendo, no se borró.
        assert listar_categorias_de_vendor(otro_vendor_prueba) == [categoria_ajena]
