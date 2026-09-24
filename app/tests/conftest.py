"""Configuración base para los tests de eServicios.

Mismo patrón que app/tests/conftest.py de Ceiba21 (proyecto hermano):
corre contra la BD real de dev de esta laptop (eservicios_dev en
localhost:5433, ver .clinerules), no una BD de test aparte. Cada
fixture que crea datos (vendor_prueba, otro_vendor_prueba) los borra al
terminar, así que no deja residuos en eservicios_dev entre corridas.
"""
import uuid

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Vendor

# Token fijo para no depender de generar_csrf_token() en cada test que
# hace POST a una ruta protegida por _verificar_csrf() — sesion_vendor
# lo escribe directo en la sesión y el test lo manda tal cual en el form.
CSRF_TOKEN_PRUEBA = "csrf-token-de-prueba"


@pytest.fixture(scope="session")
def app():
    """Crea la app Flask en modo testing, contra la BD de dev de esta laptop."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            # :5433 porque en esta laptop el cluster nativo de Postgres no
            # está en el puerto default 5432 (ocupado por el contenedor
            # Docker de FVA) — mismo criterio que el conftest.py de
            # Ceiba21, proyecto hermano.
            "SQLALCHEMY_DATABASE_URI": "postgresql://webmaster:postgres123@localhost:5433/eservicios_dev",
        }
    )
    yield app


@pytest.fixture(scope="function")
def client(app):
    """Cliente HTTP para hacer peticiones de prueba."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Acceso a la base de datos en tests, dentro de un app_context."""
    with app.app_context():
        yield _db


def _crear_vendor_prueba(db, *, activo: bool = True, email_verificado: bool = True) -> Vendor:
    """Crea y guarda un Vendor descartable con datos únicos por llamada.

    Args:
        db: Sesión de base de datos (fixture `db`).
        activo: Valor de `Vendor.activo`.
        email_verificado: Valor de `Vendor.email_verificado`.

    Returns:
        El `Vendor` recién creado y ya en la base de datos.
    """
    sufijo = uuid.uuid4().hex[:8]
    vendor = Vendor(
        email=f"test-{sufijo}@eservicios-test.local",
        slug=f"test-{sufijo}",
        nombre_negocio="Tienda de prueba",
        whatsapp_numero="+50212345678",
        activo=activo,
        email_verificado=email_verificado,
    )
    vendor.set_password("clave-de-prueba-123")
    db.session.add(vendor)
    db.session.commit()
    return vendor


@pytest.fixture
def vendor_prueba(db):
    """Vendor descartable para un test, borrado al terminar.

    `cascade="all, delete-orphan"` en Vendor.categorias/links/productos
    (ver app/models/vendor.py) hace que borrar el vendor limpie también
    todo lo que el test haya creado debajo de él, sin borrarlo a mano
    uno por uno.
    """
    vendor = _crear_vendor_prueba(db)
    yield vendor
    db.session.delete(vendor)
    db.session.commit()


@pytest.fixture
def otro_vendor_prueba(db):
    """Un segundo Vendor descartable, para probar que un vendedor no
    puede leer/editar/borrar datos de la tienda de otro (chequeos de
    pertenencia como `obtener_categoria_de_vendor`)."""
    vendor = _crear_vendor_prueba(db)
    yield vendor
    db.session.delete(vendor)
    db.session.commit()


@pytest.fixture
def sesion_vendor(client, vendor_prueba):
    """Cliente HTTP con la sesión de `vendor_prueba` ya iniciada.

    Escribe `vendor_id` y `csrf_token` directo en la sesión de Flask
    (mismo mecanismo que `vendor_auth_service.iniciar_sesion_vendor` /
    `auth_service.generar_csrf_token`) en vez de pasar por el formulario
    de login — más rápido y no depende de que el login funcione para
    poder probar otras rutas del panel.
    """
    with client.session_transaction() as sess:
        sess["vendor_id"] = vendor_prueba.id
        sess["csrf_token"] = CSRF_TOKEN_PRUEBA
    return client
