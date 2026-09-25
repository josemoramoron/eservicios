"""Tests de caracterización del bloque "Enlaces" de vendor_service.py / vendedor.py.

Mismo criterio que test_vendor_categorias.py: se escriben ANTES de
mover este código a su propio módulo, para documentar el
comportamiento actual y detectar cualquier regresión durante el split.
"""
from app.models import VendorLink
from app.services.vendor_link_service import (
    LinkInvalidoError,
    REDES_RAPIDAS_LINK,
    actualizar_link,
    construir_url_red_social,
    crear_link,
    eliminar_link,
    listar_links_activos,
    listar_links_de_vendor,
    mover_link,
    nombre_red_rapida,
    obtener_link_de_vendor,
)
from app.tests.conftest import CSRF_TOKEN_PRUEBA


class TestServicioLinks:
    """Tests directos de las funciones de app/services/vendor_service.py."""

    def test_listar_links_vacio_al_inicio(self, db, vendor_prueba):
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_crear_link_lo_agrega_a_la_lista(self, db, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Mi Instagram", url="https://instagram.com/algo")
        assert link.titulo == "Mi Instagram"
        assert link.url == "https://instagram.com/algo"
        assert link.activo is True
        assert link.orden == 0
        assert listar_links_de_vendor(vendor_prueba) == [link]

    def test_crear_link_incrementa_orden(self, db, vendor_prueba):
        primero = crear_link(vendor_prueba, titulo="Uno", url="https://ejemplo.com/1")
        segundo = crear_link(vendor_prueba, titulo="Dos", url="https://ejemplo.com/2")
        assert primero.orden == 0
        assert segundo.orden == 1

    def test_crear_link_titulo_vacio_lanza_error(self, db, vendor_prueba):
        try:
            crear_link(vendor_prueba, titulo="   ", url="https://ejemplo.com")
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_crear_link_url_sin_http_lanza_error(self, db, vendor_prueba):
        try:
            crear_link(vendor_prueba, titulo="Sitio", url="ejemplo.com")
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_listar_links_activos_excluye_inactivos(self, db, vendor_prueba):
        activo = crear_link(vendor_prueba, titulo="Activo", url="https://ejemplo.com/a")
        inactivo = crear_link(vendor_prueba, titulo="Inactivo", url="https://ejemplo.com/b")
        actualizar_link(inactivo, titulo=inactivo.titulo, url=inactivo.url, activo=False)
        assert listar_links_activos(vendor_prueba) == [activo]
        # El listado completo (para el panel) sigue mostrando ambos.
        assert len(listar_links_de_vendor(vendor_prueba)) == 2

    def test_obtener_link_de_vendor_devuelve_none_si_es_de_otra_tienda(
        self, db, vendor_prueba, otro_vendor_prueba
    ):
        link = crear_link(vendor_prueba, titulo="Mío", url="https://ejemplo.com")
        assert obtener_link_de_vendor(otro_vendor_prueba, link.id) is None
        assert obtener_link_de_vendor(vendor_prueba, link.id) == link

    def test_actualizar_link_cambia_titulo_url_y_activo(self, db, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Antes", url="https://ejemplo.com/antes")
        actualizar_link(link, titulo="Después", url="https://ejemplo.com/despues", activo=False)
        assert link.titulo == "Después"
        assert link.url == "https://ejemplo.com/despues"
        assert link.activo is False

    def test_actualizar_link_titulo_vacio_lanza_error(self, db, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Original", url="https://ejemplo.com")
        try:
            actualizar_link(link, titulo="", url="https://ejemplo.com", activo=True)
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass
        assert link.titulo == "Original"

    def test_actualizar_link_url_invalida_lanza_error(self, db, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Original", url="https://ejemplo.com")
        try:
            actualizar_link(link, titulo="Original", url="ftp://no-vale", activo=True)
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass
        assert link.url == "https://ejemplo.com"

    def test_eliminar_link_lo_saca_de_la_lista(self, db, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Temporal", url="https://ejemplo.com")
        eliminar_link(link)
        assert listar_links_de_vendor(vendor_prueba) == []
        assert db.session.get(VendorLink, link.id) is None

    def test_mover_link_arriba_intercambia_orden(self, db, vendor_prueba):
        primero = crear_link(vendor_prueba, titulo="Primero", url="https://ejemplo.com/1")
        segundo = crear_link(vendor_prueba, titulo="Segundo", url="https://ejemplo.com/2")
        mover_link(vendor_prueba, segundo, direccion="arriba")
        assert primero.orden == 1
        assert segundo.orden == 0
        assert listar_links_de_vendor(vendor_prueba) == [segundo, primero]

    def test_mover_link_primero_hacia_arriba_no_hace_nada(self, db, vendor_prueba):
        primero = crear_link(vendor_prueba, titulo="Primero", url="https://ejemplo.com/1")
        crear_link(vendor_prueba, titulo="Segundo", url="https://ejemplo.com/2")
        mover_link(vendor_prueba, primero, direccion="arriba")
        assert primero.orden == 0  # sin cambios, ya estaba en el tope

    def test_construir_url_red_social_con_usuario(self):
        assert construir_url_red_social("instagram", "@josemoramoron") == "https://instagram.com/josemoramoron"

    def test_construir_url_red_social_con_url_completa(self):
        url = "https://instagram.com/ya-copiado"
        assert construir_url_red_social("instagram", url) == url

    def test_construir_url_red_social_clave_no_reconocida_lanza_error(self):
        try:
            construir_url_red_social("red-inventada", "usuario")
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass

    def test_construir_url_red_social_valor_vacio_lanza_error(self):
        try:
            construir_url_red_social("instagram", "   ")
            assert False, "debía lanzar LinkInvalidoError"
        except LinkInvalidoError:
            pass

    def test_nombre_red_rapida_conocida_y_desconocida(self):
        assert nombre_red_rapida("instagram") == "Instagram"
        assert nombre_red_rapida("red-inventada") is None

    def test_redes_rapidas_link_no_esta_vacia(self):
        # Caracteriza que la lista de redes del selector rápido existe y
        # trae al menos las principales — no se movió ni se filtró nada.
        claves = dict(REDES_RAPIDAS_LINK)
        assert "instagram" in claves
        assert "tiktok" in claves


class TestRutasLinks:
    """Tests de las rutas /vendedor/enlaces* (app/routes/vendedor.py)."""

    def test_enlaces_sin_login_redirige_a_login(self, client):
        respuesta = client.get("/vendedor/enlaces")
        assert respuesta.status_code == 302
        assert "/e-link/login" in respuesta.headers["Location"]

    def test_enlaces_con_login_devuelve_200(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.get("/vendedor/enlaces")
        assert respuesta.status_code == 200

    def test_enlace_nuevo_sin_csrf_da_400(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/enlaces/nuevo", data={"red": "otro", "titulo": "X", "url": "https://ejemplo.com"}
        )
        assert respuesta.status_code == 400
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_enlace_nuevo_otro_crea_con_url_tal_cual(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/enlaces/nuevo",
            data={
                "red": "otro",
                "titulo": "Mi sitio",
                "url": "https://mi-sitio.com",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
        )
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].endswith("/vendedor/enlaces")
        links = listar_links_de_vendor(vendor_prueba)
        assert len(links) == 1
        assert links[0].titulo == "Mi sitio"
        assert links[0].url == "https://mi-sitio.com"

    def test_enlace_nuevo_red_rapida_arma_url_y_autocompleta_titulo(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/enlaces/nuevo",
            data={
                "red": "instagram",
                "titulo": "",
                "usuario": "@josemoramoron",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
        )
        assert respuesta.status_code == 302
        links = listar_links_de_vendor(vendor_prueba)
        assert len(links) == 1
        assert links[0].url == "https://instagram.com/josemoramoron"
        assert links[0].titulo == "Instagram"  # autocompletado por nombre_red_rapida

    def test_enlace_nuevo_url_invalida_no_crea_nada(self, db, sesion_vendor, vendor_prueba):
        respuesta = sesion_vendor.post(
            "/vendedor/enlaces/nuevo",
            data={"red": "otro", "titulo": "X", "url": "no-es-una-url", "csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 200  # re-renderiza el formulario con el error
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_enlace_editar_actualiza(self, db, sesion_vendor, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="Antes", url="https://ejemplo.com/antes")
        respuesta = sesion_vendor.post(
            f"/vendedor/enlaces/{link.id}/editar",
            data={
                "titulo": "Después",
                "url": "https://ejemplo.com/despues",
                "activo": "on",
                "csrf_token": CSRF_TOKEN_PRUEBA,
            },
        )
        assert respuesta.status_code == 302
        actualizado = db.session.get(VendorLink, link.id)
        assert actualizado.titulo == "Después"
        assert actualizado.url == "https://ejemplo.com/despues"

    def test_enlace_editar_de_otra_tienda_da_404(self, db, sesion_vendor, otro_vendor_prueba):
        link_ajeno = crear_link(otro_vendor_prueba, titulo="No es mío", url="https://ejemplo.com")
        respuesta = sesion_vendor.get(f"/vendedor/enlaces/{link_ajeno.id}/editar")
        assert respuesta.status_code == 404

    def test_enlace_eliminar_lo_borra(self, db, sesion_vendor, vendor_prueba):
        link = crear_link(vendor_prueba, titulo="A borrar", url="https://ejemplo.com")
        respuesta = sesion_vendor.post(
            f"/vendedor/enlaces/{link.id}/eliminar", data={"csrf_token": CSRF_TOKEN_PRUEBA}
        )
        assert respuesta.status_code == 302
        assert listar_links_de_vendor(vendor_prueba) == []

    def test_enlace_eliminar_de_otra_tienda_da_404(self, db, sesion_vendor, otro_vendor_prueba):
        link_ajeno = crear_link(otro_vendor_prueba, titulo="No es mío", url="https://ejemplo.com")
        respuesta = sesion_vendor.post(
            f"/vendedor/enlaces/{link_ajeno.id}/eliminar", data={"csrf_token": CSRF_TOKEN_PRUEBA}
        )
        assert respuesta.status_code == 404
        assert listar_links_de_vendor(otro_vendor_prueba) == [link_ajeno]

    def test_enlace_mover_arriba_reordena(self, db, sesion_vendor, vendor_prueba):
        primero = crear_link(vendor_prueba, titulo="Primero", url="https://ejemplo.com/1")
        segundo = crear_link(vendor_prueba, titulo="Segundo", url="https://ejemplo.com/2")
        respuesta = sesion_vendor.post(
            f"/vendedor/enlaces/{segundo.id}/mover?direccion=arriba",
            data={"csrf_token": CSRF_TOKEN_PRUEBA},
        )
        assert respuesta.status_code == 302
        assert listar_links_de_vendor(vendor_prueba) == [segundo, primero]
