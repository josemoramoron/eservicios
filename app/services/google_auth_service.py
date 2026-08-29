"""Cliente OAuth de Google para "Iniciar sesión con Google" del vendedor.

Usa Authlib (`authlib.integrations.flask_client.OAuth`), que se encarga
del intercambio de código por token y de la protección CSRF propia del
flujo OAuth (parámetro `state`, guardado en la sesión de Flask) — no
hace falta manejar eso a mano, solo llamar a
`oauth.google.authorize_redirect(...)` y `oauth.google.authorize_access_token()`
desde las rutas (ver `app/routes/vendedor.py`, `/vendedor/auth/google*`).

El perfil del usuario se pide explícitamente al endpoint de `userinfo`
de Google (`obtener_perfil_google`) en vez de depender del parseo
automático del `id_token` (que exige manejar un `nonce`) — es el camino
más simple y estable entre versiones de Authlib.

Requiere `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` en la configuración
(ver `config.py`) — se generan en Google Cloud Console. Ver el docstring
de esas dos claves en `config.py` para los pasos exactos.
"""
from __future__ import annotations

from authlib.integrations.flask_client import OAuth

oauth = OAuth()


def configurar_oauth_google(app) -> None:
    """Registra el cliente OAuth de Google en la instancia de Flask.

    Se llama una sola vez desde `create_app` (`app/__init__.py`), después
    de que `app.config` ya tiene `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
    cargados. Si esas dos claves están vacías (todavía no configuradas),
    el registro igual se completa sin error — el fallo ocurre recién si
    alguien intenta usar el botón de Google, no al arrancar la app.

    Args:
        app: Instancia de Flask ya configurada.
    """
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def obtener_perfil_google(token: dict) -> dict:
    """Obtiene el perfil del usuario autenticado desde el endpoint `userinfo` de Google.

    Args:
        token: Token devuelto por `oauth.google.authorize_access_token()`.

    Returns:
        Diccionario con, al menos, `sub` (id estable de la cuenta de
        Google), `email`, `email_verified` y `name`.
    """
    return oauth.google.userinfo(token=token)
