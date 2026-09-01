"""Rutas del panel de vendedor (`/vendedor`) — registro, login, perfil y CRUD de productos.

La tienda pública en sí (`<slug>.eservicios.org`) no vive aquí — la
sirve `app/routes/tienda.py` desde el enrutador de subdominios. Este
blueprint es el panel donde el vendedor administra su tienda, siempre
en el dominio principal.
"""
from __future__ import annotations

import io
from decimal import Decimal, InvalidOperation

import qrcode
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.datastructures import ImmutableMultiDict

from app.extensions import db
from app.models import Vendor, VendorProduct
from app.services import r2_service
from app.services.auth_service import generar_csrf_token, validar_csrf_token
from app.services.email_service import EnvioCorreoError
from app.services.vendor_auth_service import (
    autenticar_vendor,
    cerrar_sesion_vendor,
    iniciar_sesion_vendor,
    requiere_vendor,
    vendor_actual,
)
from app.services.vendor_email_verificacion_service import (
    ReenvioMuyProntoError,
    asegurar_codigo_vigente,
    generar_y_enviar_codigo,
    reenviar_codigo,
    verificar_codigo,
)
from app.services.badges_producto_service import listar_badges_producto
from app.services.estadisticas_service import resumen_estadisticas
from app.services.estados_stock_service import listar_estados_stock
from app.services.estilos_portada_service import listar_presets_portada
from app.services.monedas_service import listar_monedas
from app.services.plantillas_tienda_service import listar_plantillas_tienda
from app.services.google_auth_service import oauth, obtener_perfil_google
from app.services.vendor_service import (
    DIAS_ENTRE_CAMBIOS_SLUG,
    DIAS_REDIRECCION_SLUG_ANTERIOR,
    MAX_CAMBIOS_SLUG,
    MAX_FOTOS_PRODUCTO,
    CambioSlugMuyRecienteError,
    CategoriaInvalidaError,
    EmailDuplicadoError,
    EmailInvalidoError,
    LimiteCambiosSlugError,
    LinkInvalidoError,
    PasswordActualIncorrectaError,
    PasswordNuevaInvalidaError,
    PerfilInvalidoError,
    SlugDuplicadoError,
    SlugInvalidoError,
    SlugReservadoError,
    SolicitudVerificacionInvalidaError,
    actualizar_categoria,
    actualizar_link,
    actualizar_perfil,
    actualizar_producto,
    cambiar_password,
    cambiar_slug,
    construir_vcard,
    crear_categoria,
    crear_link,
    crear_producto,
    eliminar_categoria,
    eliminar_link,
    eliminar_producto,
    estado_cambio_slug,
    listar_avisos_de_vendor,
    listar_categorias_de_vendor,
    listar_links_de_vendor,
    listar_productos_de_vendor,
    mover_link,
    obtener_categoria_de_vendor,
    obtener_link_de_vendor,
    obtener_producto_de_vendor,
    listar_paleta_acento_sugerida,
    obtener_vendor_por_email,
    obtener_vendor_por_google_id,
    plan_plus_vigente,
    registrar_vendor,
    registrar_vendor_google,
    resolver_acento_vendor,
    slug_disponible,
    solicitar_verificacion_vendedor,
    validar_formato_slug,
    vincular_google,
)

vendedor_bp = Blueprint("vendedor", __name__, url_prefix="/vendedor")


@vendedor_bp.context_processor
def inyectar_vendor_actual() -> dict:
    """Expone el vendedor autenticado, su acento Plus y el generador de CSRF a las plantillas.

    `acento` se calcula acá (no en cada ruta) porque el color de acento
    del vendedor debe verse en todo el panel — nav, botones, tarjetas de
    estadísticas —, no solo en la pantalla de perfil donde se elige.

    Returns:
        Diccionario con las claves `vendor`, `acento` y `csrf_token` para Jinja.
    """
    vendor = vendor_actual()
    return {
        "vendor": vendor,
        "acento": resolver_acento_vendor(vendor) if vendor else None,
        "csrf_token": generar_csrf_token,
    }


def _verificar_csrf() -> None:
    """Aborta la petición con 400 si el token CSRF del form no es válido."""
    if not validar_csrf_token(request.form.get("csrf_token")):
        abort(400, description="Token de seguridad inválido o expirado. Recarga la página e intenta de nuevo.")


def _subir_imagen_opcional(campo: str, carpeta: str) -> tuple[str | None, str | None]:
    """Sube el archivo de `request.files[campo]` a R2, si el usuario adjuntó uno.

    Args:
        campo: Nombre del `<input type="file">` en el formulario.
        carpeta: Prefijo dentro del bucket para esta imagen.

    Returns:
        Tupla `(url, error)`: `url` con la URL pública nueva si se subió
        un archivo (o None si no se adjuntó ninguno), y `error` con el
        mensaje a mostrar si la subida falló por tipo o tamaño inválido.
    """
    archivo = request.files.get(campo)
    if not archivo or not archivo.filename:
        return None, None
    try:
        return r2_service.subir_imagen(archivo, carpeta=carpeta), None
    except (r2_service.ArchivoInvalidoError, r2_service.ArchivoDemasiadoGrandeError) as exc:
        return None, str(exc)


def _parsear_lista_ids(valor: str) -> list[int]:
    """Convierte un CSV de ids (de un input hidden armado por JS) en una lista de enteros.

    Ignora en silencio cualquier token vacío o no numérico — este campo
    lo arma `producto_fotos.js`, no lo escribe el vendedor directamente,
    pero igual nunca debe poder tumbar el guardado del producto por un
    valor inesperado.

    Args:
        valor: Contenido crudo del input hidden, ej. "3,1,2".

    Returns:
        Lista de ids como enteros, en el mismo orden que venían.
    """
    ids = []
    for token in valor.split(","):
        token = token.strip()
        if token.isdigit():
            ids.append(int(token))
    return ids


def _resolver_fotos_producto(vendor, producto: VendorProduct | None) -> tuple[list[str], str | None, str | None]:
    """Resuelve la galería final de fotos de un producto tras guardar el formulario.

    Las fotos existentes se reordenan (o se quitan) según lo que haya
    armado el drag-and-drop / los botones ‹ › del formulario
    (`producto_fotos.js`), leído de los inputs hidden `orden_fotos`
    (ids en el orden final) y `fotos_a_quitar` (ids a borrar). Las fotos
    nuevas (`foto_nueva_1`..`foto_nueva_N`) se suben a R2 y se agregan
    al final, hasta completar `MAX_FOTOS_PRODUCTO` — cualquier foto
    nueva de más allá del máximo se ignora (no se sube) y se avisa con
    una advertencia no bloqueante, en vez de rechazar todo el guardado.

    Args:
        vendor: Tienda dueña del producto (para la carpeta de R2).
        producto: Producto existente (para sus fotos actuales), o None
            si es un producto nuevo (parte sin fotos existentes).

    Returns:
        Tupla `(urls, error, advertencia)`: `urls` con la lista final de
        fotos en orden, máximo `MAX_FOTOS_PRODUCTO`; `error` con el
        mensaje a mostrar si alguna subida falló por tipo o tamaño
        inválido (en ese caso `urls` es una lista vacía y no se debe
        usar, y no se guarda nada); `advertencia` con un mensaje no
        bloqueante si se ignoraron fotos nuevas por exceso de cantidad.
    """
    fotos_existentes = {foto.id: foto.url for foto in producto.fotos} if producto is not None else {}
    ids_a_quitar = set(_parsear_lista_ids(request.form.get("fotos_a_quitar", "")))
    orden_ids = _parsear_lista_ids(request.form.get("orden_fotos", ""))

    resultado: list[str] = []
    ids_usados: set[int] = set()
    for foto_id in orden_ids:
        if foto_id in ids_a_quitar or foto_id in ids_usados:
            continue
        url = fotos_existentes.get(foto_id)
        if url:
            resultado.append(url)
            ids_usados.add(foto_id)

    fotos_omitidas = False
    for i in range(1, MAX_FOTOS_PRODUCTO + 1):
        archivo = request.files.get(f"foto_nueva_{i}")
        if not archivo or not archivo.filename:
            continue
        if len(resultado) >= MAX_FOTOS_PRODUCTO:
            fotos_omitidas = True
            continue
        url_nueva, error = _subir_imagen_opcional(f"foto_nueva_{i}", f"vendors/{vendor.slug}/productos")
        if error:
            return [], error, None
        if url_nueva is not None:
            resultado.append(url_nueva)

    urls_finales = set(resultado)
    for foto_id, url in fotos_existentes.items():
        if url not in urls_finales:
            r2_service.eliminar_imagen(url)

    advertencia = (
        f"Se ignoraron algunas fotos nuevas porque ya llegaste al máximo de {MAX_FOTOS_PRODUCTO}."
        if fotos_omitidas
        else None
    )
    return resultado, None, advertencia


# --- Registro y autenticación ---


@vendedor_bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Formulario de registro de una tienda nueva (plan gratis)."""
    if vendor_actual() is not None:
        return redirect(url_for("vendedor.dashboard"))

    valores = {
        "email": "",
        "slug": "",
        "nombre_negocio": "",
        "whatsapp_numero": "",
        "bio": "",
    }
    if request.method == "POST":
        _verificar_csrf()
        valores = {
            "email": request.form.get("email", "").strip(),
            "slug": request.form.get("slug", "").strip().lower(),
            "nombre_negocio": request.form.get("nombre_negocio", "").strip(),
            "whatsapp_numero": request.form.get("whatsapp_numero", "").strip(),
            "bio": request.form.get("bio", "").strip(),
        }
        password = request.form.get("password", "")
        password_confirmacion = request.form.get("password_confirmacion", "")

        if not valores["email"]:
            flash("Escribe tu correo, o usa \"Continuar con Google\".", "error")
            return render_template("vendedor/registro.html", valores=valores)
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
            return render_template("vendedor/registro.html", valores=valores)
        if password != password_confirmacion:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("vendedor/registro.html", valores=valores)
        if not valores["nombre_negocio"]:
            flash("El nombre de la tienda es obligatorio.", "error")
            return render_template("vendedor/registro.html", valores=valores)
        if not valores["whatsapp_numero"]:
            flash("El número de WhatsApp es obligatorio.", "error")
            return render_template("vendedor/registro.html", valores=valores)

        try:
            vendor = registrar_vendor(
                email=valores["email"],
                password=password,
                slug=valores["slug"],
                nombre_negocio=valores["nombre_negocio"],
                whatsapp_numero=valores["whatsapp_numero"],
                bio=valores["bio"],
            )
        except (
            EmailInvalidoError,
            EmailDuplicadoError,
            SlugInvalidoError,
            SlugReservadoError,
            SlugDuplicadoError,
        ) as exc:
            flash(str(exc), "error")
            return render_template("vendedor/registro.html", valores=valores)

        try:
            generar_y_enviar_codigo(vendor)
        except EnvioCorreoError as error:
            flash(str(error), "error")
        session["vendor_pendiente_id"] = vendor.id
        flash(f'¡Listo! Tu tienda "{vendor.nombre_negocio}" ya está en línea.', "success")
        return redirect(url_for("vendedor.verificar_email"))

    return render_template("vendedor/registro.html", valores=valores)


@vendedor_bp.route("/registro/verificar-slug")
def verificar_slug():
    """Endpoint AJAX: valida formato y disponibilidad de un slug en vivo.

    Returns:
        JSON `{"disponible": bool, "error": str | None}` para pintar el
        chequeo en tiempo real del formulario de registro.
    """
    slug = request.args.get("slug", "")
    try:
        slug_normalizado = validar_formato_slug(slug)
    except SlugInvalidoError as exc:
        return {"disponible": False, "error": str(exc)}
    if not slug_disponible(slug_normalizado):
        return {"disponible": False, "error": "Ese subdominio ya está en uso."}
    return {"disponible": True, "error": None}


@vendedor_bp.route("/login", methods=["GET", "POST"])
def login():
    """Formulario de inicio de sesión del panel de vendedor."""
    if vendor_actual() is not None:
        return redirect(url_for("vendedor.dashboard"))
    if request.method == "POST":
        _verificar_csrf()
        vendor = autenticar_vendor(request.form.get("email", ""), request.form.get("password", ""))
        if vendor is None:
            flash("Correo o contraseña incorrectos.", "error")
        elif not vendor.email_verificado:
            try:
                asegurar_codigo_vigente(vendor)
            except EnvioCorreoError as error:
                flash(str(error), "error")
            session["vendor_pendiente_id"] = vendor.id
            return redirect(url_for("vendedor.verificar_email"))
        else:
            iniciar_sesion_vendor(vendor)
            destino = request.args.get("next") or url_for("vendedor.dashboard")
            return redirect(destino)
    return render_template("vendedor/login.html")


@vendedor_bp.route("/auth/google")
def auth_google():
    """Inicia el flujo de "Iniciar sesión con Google" (sirve tanto para registro como para login).

    En `registro.html` este endpoint es también el `formaction` del botón
    "Continuar con Google", que vive dentro del mismo `<form>` que el
    subdominio/nombre/WhatsApp/bio — al enviarse con `formmethod="get"`,
    el navegador manda esos campos ya escritos como query string. Se
    guardan en `session["registro_datos_previos"]` para no perderlos en
    el ir-y-volver a Google, y `auth_google_callback` los recupera para
    no volver a pedirlos en `registro_completar_google`.
    """
    if vendor_actual() is not None:
        return redirect(url_for("vendedor.dashboard"))

    datos_previos = {
        campo: request.args.get(campo, "").strip()
        for campo in ("slug", "nombre_negocio", "whatsapp_numero", "bio")
    }
    if any(datos_previos.values()):
        session["registro_datos_previos"] = datos_previos

    redirect_uri = url_for("vendedor.auth_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@vendedor_bp.route("/auth/google/callback")
def auth_google_callback():
    """Callback de Google: abre sesión si la cuenta ya existe, o manda a completar el registro.

    Si el correo que devuelve Google ya tenía una tienda registrada por
    contraseña, la vincula (`vincular_google`) en vez de crear una
    cuenta duplicada. Si no existe ninguna tienda con ese correo ni con
    ese `google_id`, guarda el perfil en `session["google_pendiente"]`
    y manda a `registro_completar_google` a pedir los datos que Google
    no entrega (subdominio, nombre de la tienda, WhatsApp).
    """
    try:
        token = oauth.google.authorize_access_token()
        perfil = obtener_perfil_google(token)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo del intercambio OAuth termina igual: de vuelta al login.
        current_app.logger.warning("Fallo el login con Google: %s", exc)
        flash("No se pudo completar el inicio de sesión con Google. Intenta de nuevo.", "error")
        return redirect(url_for("vendedor.login"))

    google_id = perfil.get("sub", "")
    email = (perfil.get("email") or "").strip().lower()
    if not google_id or not email or not perfil.get("email_verified"):
        flash("No se pudo confirmar tu cuenta de Google. Intenta de nuevo.", "error")
        return redirect(url_for("vendedor.login"))

    # Se saca de la sesión sin importar qué rama siga después: si el
    # vendor ya existe (login directo) estos datos ya no aplican, y no
    # deben quedar arrastrados a un futuro registro con otra cuenta.
    datos_previos = session.pop("registro_datos_previos", None) or {}

    vendor = obtener_vendor_por_google_id(google_id)
    if vendor is None:
        vendor = obtener_vendor_por_email(email)
        if vendor is not None:
            vincular_google(vendor, google_id)

    if vendor is not None:
        if not vendor.activo:
            flash("Tu tienda está suspendida. Contacta al soporte de eServicios.", "error")
            return redirect(url_for("vendedor.login"))
        iniciar_sesion_vendor(vendor)
        flash(f'¡Bienvenido de nuevo, {vendor.nombre_negocio}!', "success")
        return redirect(url_for("vendedor.dashboard"))

    session["google_pendiente"] = {
        "google_id": google_id,
        "email": email,
        "nombre_sugerido": datos_previos.get("nombre_negocio") or perfil.get("name", ""),
        "slug_sugerido": datos_previos.get("slug", ""),
        "whatsapp_sugerido": datos_previos.get("whatsapp_numero", ""),
        "bio_sugerida": datos_previos.get("bio", ""),
    }
    return redirect(url_for("vendedor.registro_completar_google"))


@vendedor_bp.route("/registro/completar-google", methods=["GET", "POST"])
def registro_completar_google():
    """Último paso del registro con Google: elegir subdominio, nombre de tienda y WhatsApp.

    Depende de `session["google_pendiente"]`, guardada por
    `auth_google_callback` cuando Google confirmó una cuenta que
    todavía no existe en eServicios — el correo ya viene verificado por
    Google, así que este paso no pasa por `verificar_email`.
    """
    if vendor_actual() is not None:
        return redirect(url_for("vendedor.dashboard"))
    pendiente = session.get("google_pendiente")
    if not pendiente:
        return redirect(url_for("vendedor.registro"))

    valores = {
        "slug": pendiente.get("slug_sugerido", ""),
        "nombre_negocio": pendiente.get("nombre_sugerido", ""),
        "whatsapp_numero": pendiente.get("whatsapp_sugerido", ""),
        "bio": pendiente.get("bio_sugerida", ""),
    }
    if request.method == "POST":
        _verificar_csrf()
        valores = {
            "slug": request.form.get("slug", "").strip().lower(),
            "nombre_negocio": request.form.get("nombre_negocio", "").strip(),
            "whatsapp_numero": request.form.get("whatsapp_numero", "").strip(),
            "bio": request.form.get("bio", "").strip(),
        }
        if not request.form.get("acepta_terminos"):
            flash("Debes aceptar los Términos y condiciones.", "error")
            return render_template("vendedor/registro_completar_google.html", valores=valores, email=pendiente["email"])
        if not valores["nombre_negocio"]:
            flash("El nombre de la tienda es obligatorio.", "error")
            return render_template("vendedor/registro_completar_google.html", valores=valores, email=pendiente["email"])
        if not valores["whatsapp_numero"]:
            flash("El número de WhatsApp es obligatorio.", "error")
            return render_template("vendedor/registro_completar_google.html", valores=valores, email=pendiente["email"])

        try:
            vendor = registrar_vendor_google(
                google_id=pendiente["google_id"],
                email=pendiente["email"],
                slug=valores["slug"],
                nombre_negocio=valores["nombre_negocio"],
                whatsapp_numero=valores["whatsapp_numero"],
                bio=valores["bio"],
            )
        except (SlugInvalidoError, SlugReservadoError, SlugDuplicadoError, EmailDuplicadoError) as exc:
            flash(str(exc), "error")
            return render_template("vendedor/registro_completar_google.html", valores=valores, email=pendiente["email"])

        session.pop("google_pendiente", None)
        iniciar_sesion_vendor(vendor)
        flash(f'¡Listo! Tu tienda "{vendor.nombre_negocio}" ya está en línea.', "success")
        return redirect(url_for("vendedor.dashboard"))

    return render_template("vendedor/registro_completar_google.html", valores=valores, email=pendiente["email"])


@vendedor_bp.route("/verificar-email", methods=["GET", "POST"])
def verificar_email():
    """Pantalla de verificación del código de 6 dígitos enviado por correo.

    Depende de `session["vendor_pendiente_id"]`, guardada en el registro
    o en el login de un vendedor que todavía no verificó su correo — no
    otorga sesión completa (`iniciar_sesion_vendor`) hasta que el código
    sea correcto.
    """
    vendor_id = session.get("vendor_pendiente_id")
    if vendor_id is None:
        return redirect(url_for("vendedor.login"))
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None or vendor.email_verificado:
        session.pop("vendor_pendiente_id", None)
        return redirect(url_for("vendedor.login"))

    if request.method == "POST":
        _verificar_csrf()
        if verificar_codigo(vendor, request.form.get("codigo", "")):
            session.pop("vendor_pendiente_id", None)
            iniciar_sesion_vendor(vendor)
            flash("¡Correo verificado! Bienvenido a tu panel.", "success")
            return redirect(url_for("vendedor.dashboard"))
        flash("Ese código no es correcto o ya venció. Intenta de nuevo o pide uno nuevo.", "error")

    return render_template("vendedor/verificar_email.html", email=vendor.email)


@vendedor_bp.route("/verificar-email/reenviar", methods=["POST"])
def verificar_email_reenviar():
    """Reenvía el código de verificación al vendedor con sesión pendiente."""
    _verificar_csrf()
    vendor_id = session.get("vendor_pendiente_id")
    if vendor_id is None:
        return redirect(url_for("vendedor.login"))
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None or vendor.email_verificado:
        session.pop("vendor_pendiente_id", None)
        return redirect(url_for("vendedor.login"))

    try:
        reenviar_codigo(vendor)
        flash("Te enviamos un código nuevo a tu correo.", "success")
    except ReenvioMuyProntoError as error:
        flash(str(error), "error")
    except EnvioCorreoError as error:
        flash(str(error), "error")
    return redirect(url_for("vendedor.verificar_email"))


@vendedor_bp.route("/logout", methods=["POST"])
def logout():
    """Cierra la sesión del panel de vendedor."""
    _verificar_csrf()
    cerrar_sesion_vendor()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("vendedor.login"))


# --- Dashboard ---


@vendedor_bp.route("/")
@requiere_vendor
def dashboard():
    """Portada del panel: link de la tienda y lista de productos."""
    vendor = vendor_actual()
    return render_template(
        "vendedor/dashboard.html",
        productos=listar_productos_de_vendor(vendor),
        estadisticas=resumen_estadisticas(vendor),
    )


@vendedor_bp.route("/qr.png")
@requiere_vendor
def qr_tienda():
    """PNG del código QR que apunta a la tienda pública del vendedor.

    Se genera al vuelo en cada pedido (no se guarda en R2 ni en ningún
    otro lado) para que nunca quede desactualizado si el vendedor
    cambia de subdominio (ver `vendor_service.cambiar_slug`) —
    regenerarlo es prácticamente gratis, así que no vale la pena cargar
    con el problema de invalidar una versión guardada.

    Returns:
        Respuesta con la imagen PNG del QR (`image/png`).
    """
    vendor = vendor_actual()
    url_tienda = f"https://{vendor.slug}.{current_app.config['SITE_DOMAIN']}"
    imagen_qr = qrcode.make(url_tienda, box_size=10, border=2)
    buffer = io.BytesIO()
    imagen_qr.save(buffer, format="PNG")
    return Response(buffer.getvalue(), mimetype="image/png")


@vendedor_bp.route("/contacto.vcf")
@requiere_vendor
def contacto_vcard():
    """Archivo vCard (.vcf) con los datos de contacto de la tienda, para guardar junto al QR.

    Returns:
        Respuesta `text/vcard` con el archivo listo para descargar, para
        que el vendedor lo comparta y sus clientes guarden la tienda
        como contacto de un toque.
    """
    vendor = vendor_actual()
    contenido = construir_vcard(vendor)
    return Response(
        contenido,
        mimetype="text/vcard",
        headers={"Content-Disposition": f'attachment; filename="{vendor.slug}.vcf"'},
    )


# --- Perfil: personalización y seguridad ---


@vendedor_bp.route("/perfil", methods=["GET", "POST"])
@requiere_vendor
def perfil():
    """Personalización de la tienda: nombre, WhatsApp, bio, moneda, logo, portada, estilo, acento, plantilla y cupón."""
    vendor = vendor_actual()
    plan_plus_activo = plan_plus_vigente(vendor)
    if request.method == "POST":
        _verificar_csrf()
        nombre_negocio = request.form.get("nombre_negocio", "")
        whatsapp_numero = request.form.get("whatsapp_numero", "")
        bio = request.form.get("bio", "")
        # Gratis para cualquier plan (a diferencia de plantilla/color_acento/
        # disponible_ahora abajo) — siempre viene del <select> cerrado del
        # formulario, sin gateo por plan_plus_activo (ver monedas_service).
        moneda = request.form.get("moneda", "")
        estilo_portada = request.form.get("estilo_portada", "")
        # Igual que estilo_portada: un radio cerrado, no texto libre — el
        # gateo real por plan Plus ocurre en tiempo de render
        # (resolver_plantilla_vendor), no acá. Se guarda tal cual llegue
        # aunque el vendedor no tenga Plus vigente en este momento.
        plantilla = request.form.get("plantilla", "")

        # El selector de color solo se envía (y solo puede cambiarse) si el
        # vendedor tiene Plus vigente — ver plan_plus_activo/plantilla. Si el
        # campo no llega (input deshabilitado/ausente) se conserva el valor
        # actual en vez de borrarlo; el checkbox "quitar" es la única forma
        # de limpiarlo, y solo aparece en el formulario cuando hay Plus.
        if request.form.get("quitar_color_acento") == "on":
            color_acento = None
        elif "color_acento" in request.form and plan_plus_activo:
            color_acento = request.form.get("color_acento", "").strip()
        else:
            color_acento = vendor.color_acento

        # El interruptor de disponibilidad (punto 15) solo se muestra en
        # el formulario si hay Plus vigente — mismo criterio que
        # color_acento/plantilla: si no está en el formulario, se
        # conserva el valor actual en vez de resetearlo a False.
        if plan_plus_activo:
            disponible_ahora = request.form.get("disponible_ahora") == "on"
        else:
            disponible_ahora = vendor.disponible_ahora

        # El campo del cupón (punto 16) sigue el mismo criterio que
        # disponible_ahora/color_acento/plantilla: solo se muestra (y
        # solo puede cambiarse) en el formulario si hay Plus vigente; si
        # no llega, se conserva el valor actual en vez de borrarlo.
        if plan_plus_activo:
            cupon = request.form.get("cupon", "")
        else:
            cupon = vendor.cupon or ""

        logo_url, error_logo = _subir_imagen_opcional("logo", f"vendors/{vendor.slug}/logo")
        if error_logo:
            flash(error_logo, "error")
            return render_template(
                "vendedor/perfil.html",
                vendor=vendor,
                presets=listar_presets_portada(),
                plantillas=listar_plantillas_tienda(),
                paleta_acento=listar_paleta_acento_sugerida(),
                plan_plus_activo=plan_plus_activo,
                monedas=listar_monedas(),
            )
        if logo_url is not None:
            r2_service.eliminar_imagen(vendor.logo_url)
        elif request.form.get("quitar_logo") == "on":
            r2_service.eliminar_imagen(vendor.logo_url)
            logo_url = None
        else:
            logo_url = vendor.logo_url

        banner_url, error_banner = _subir_imagen_opcional("banner", f"vendors/{vendor.slug}/banner")
        if error_banner:
            flash(error_banner, "error")
            return render_template(
                "vendedor/perfil.html",
                vendor=vendor,
                presets=listar_presets_portada(),
                plantillas=listar_plantillas_tienda(),
                paleta_acento=listar_paleta_acento_sugerida(),
                plan_plus_activo=plan_plus_activo,
                monedas=listar_monedas(),
            )
        if banner_url is not None:
            r2_service.eliminar_imagen(vendor.banner_url)
        elif request.form.get("quitar_banner") == "on":
            r2_service.eliminar_imagen(vendor.banner_url)
            banner_url = None
        else:
            banner_url = vendor.banner_url

        try:
            actualizar_perfil(
                vendor,
                nombre_negocio=nombre_negocio,
                whatsapp_numero=whatsapp_numero,
                bio=bio,
                logo_url=logo_url,
                banner_url=banner_url,
                estilo_portada=estilo_portada,
                color_acento=color_acento,
                plantilla=plantilla,
                disponible_ahora=disponible_ahora,
                moneda=moneda,
                cupon=cupon,
            )
        except PerfilInvalidoError as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/perfil.html",
                vendor=vendor,
                presets=listar_presets_portada(),
                plantillas=listar_plantillas_tienda(),
                paleta_acento=listar_paleta_acento_sugerida(),
                plan_plus_activo=plan_plus_activo,
                monedas=listar_monedas(),
            )

        flash("Perfil actualizado.", "success")
        return redirect(url_for("vendedor.perfil"))
    return render_template(
        "vendedor/perfil.html",
        vendor=vendor,
        presets=listar_presets_portada(),
        plantillas=listar_plantillas_tienda(),
        paleta_acento=listar_paleta_acento_sugerida(),
        plan_plus_activo=plan_plus_activo,
        monedas=listar_monedas(),
    )


@vendedor_bp.route("/perfil/password", methods=["POST"])
@requiere_vendor
def perfil_password():
    """Cambia la contraseña del vendedor (sección de seguridad del perfil)."""
    _verificar_csrf()
    vendor = vendor_actual()
    password_actual = request.form.get("password_actual", "")
    password_nueva = request.form.get("password_nueva", "")
    password_nueva_confirmacion = request.form.get("password_nueva_confirmacion", "")

    if password_nueva != password_nueva_confirmacion:
        flash("Las contraseñas nuevas no coinciden.", "error")
        return redirect(url_for("vendedor.perfil"))

    try:
        cambiar_password(vendor, password_actual=password_actual, password_nueva=password_nueva)
    except (PasswordActualIncorrectaError, PasswordNuevaInvalidaError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("vendedor.perfil"))

    flash("Contraseña actualizada.", "success")
    return redirect(url_for("vendedor.perfil"))


@vendedor_bp.route("/perfil/slug", methods=["GET", "POST"])
@requiere_vendor
def perfil_slug():
    """Pantalla dedicada para cambiar el subdominio de la tienda.

    Separada a propósito de `/vendedor/perfil` (que edita nombre, bio,
    logo y portada sin fricción): cambiar el slug afecta enlaces que el
    vendedor ya haya compartido, así que exige reescribir el nuevo
    subdominio para confirmar, y respeta los límites de seguridad de
    `vendor_service.cambiar_slug` (máximo `MAX_CAMBIOS_SLUG` cambios,
    mínimo `DIAS_ENTRE_CAMBIOS_SLUG` días entre uno y otro).
    """
    vendor = vendor_actual()
    if request.method == "POST":
        _verificar_csrf()
        nuevo_slug = request.form.get("nuevo_slug", "")
        confirmacion = request.form.get("confirmar_nuevo_slug", "")

        if nuevo_slug.strip().lower() != confirmacion.strip().lower():
            flash("Debes reescribir el nuevo subdominio exactamente igual para confirmar.", "error")
            return render_template(
                "vendedor/perfil_slug.html",
                vendor=vendor,
                estado=estado_cambio_slug(vendor),
                valor_intentado=nuevo_slug,
                dias_redireccion=DIAS_REDIRECCION_SLUG_ANTERIOR,
                dias_entre_cambios=DIAS_ENTRE_CAMBIOS_SLUG,
                max_cambios=MAX_CAMBIOS_SLUG,
            )

        try:
            slug_final = cambiar_slug(vendor, nuevo_slug=nuevo_slug)
        except (
            SlugInvalidoError,
            SlugReservadoError,
            SlugDuplicadoError,
            LimiteCambiosSlugError,
            CambioSlugMuyRecienteError,
        ) as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/perfil_slug.html",
                vendor=vendor,
                estado=estado_cambio_slug(vendor),
                valor_intentado=nuevo_slug,
                dias_redireccion=DIAS_REDIRECCION_SLUG_ANTERIOR,
                dias_entre_cambios=DIAS_ENTRE_CAMBIOS_SLUG,
                max_cambios=MAX_CAMBIOS_SLUG,
            )

        flash(
            f"Listo, tu tienda ahora es {slug_final}.eservicios.org. "
            f"El enlace anterior va a seguir funcionando (redirigiendo al nuevo) por "
            f"{DIAS_REDIRECCION_SLUG_ANTERIOR} días.",
            "success",
        )
        return redirect(url_for("vendedor.perfil"))

    return render_template(
        "vendedor/perfil_slug.html",
        vendor=vendor,
        estado=estado_cambio_slug(vendor),
        valor_intentado="",
        dias_redireccion=DIAS_REDIRECCION_SLUG_ANTERIOR,
        dias_entre_cambios=DIAS_ENTRE_CAMBIOS_SLUG,
        max_cambios=MAX_CAMBIOS_SLUG,
    )


@vendedor_bp.route("/perfil/verificacion", methods=["GET", "POST"])
@requiere_vendor
def perfil_verificacion():
    """Pantalla dedicada para solicitar (o revisar el estado de) la insignia "Vendedor verificado".

    Separada de `/vendedor/perfil` por el mismo motivo que
    `/vendedor/perfil/slug`: es un flujo propio (explicación + documento
    opcional de respaldo), no una casilla más del formulario de
    personalización.

    **Solicitarla requiere plan Plus vigente** (decisión de Jose,
    2026-08-31) — a diferencia del badge en sí, que sigue siendo gratis
    para cualquier plan una vez otorgado (`vendor.verificado` se lee
    directo en las plantillas, sin ningún resolver de gating). Si la
    tienda ya está verificada, se muestra ese estado sin importar el
    plan. Si tiene una solicitud pendiente, se muestra igual aunque el
    Plus haya vencido después de enviarla (no se le "cancela" la
    revisión por eso) — pero para reenviarla o mandar una nueva hace
    falta Plus vigente en ese momento, chequeo real en
    `vendor_service.solicitar_verificacion_vendedor`.
    """
    vendor = vendor_actual()
    plan_plus_activo = plan_plus_vigente(vendor)
    if request.method == "POST":
        _verificar_csrf()
        if not plan_plus_activo:
            flash("Solicitar la verificación es una función de e-link Plus.", "error")
            return render_template(
                "vendedor/perfil_verificacion.html", vendor=vendor, plan_plus_activo=plan_plus_activo
            )
        mensaje = request.form.get("mensaje", "")

        documento_url, error_documento = _subir_imagen_opcional(
            "documento", f"vendors/{vendor.slug}/verificacion"
        )
        if error_documento:
            flash(error_documento, "error")
            return render_template(
                "vendedor/perfil_verificacion.html", vendor=vendor, plan_plus_activo=plan_plus_activo
            )

        documento_anterior = vendor.solicitud_verificacion_documento_url
        try:
            solicitar_verificacion_vendedor(vendor, mensaje=mensaje, documento_url=documento_url)
        except SolicitudVerificacionInvalidaError as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/perfil_verificacion.html", vendor=vendor, plan_plus_activo=plan_plus_activo
            )

        if documento_url is not None and documento_anterior:
            # Se adjuntó un documento nuevo reemplazando uno de un envío
            # anterior — se borra el viejo para no dejarlo huérfano en R2
            # (mismo criterio que logo/portada en perfil()).
            r2_service.eliminar_imagen(documento_anterior)

        flash("Solicitud enviada. El equipo de eServicios la va a revisar pronto.", "success")
        return redirect(url_for("vendedor.perfil_verificacion"))
    return render_template(
        "vendedor/perfil_verificacion.html", vendor=vendor, plan_plus_activo=plan_plus_activo
    )


# --- Productos ---


def _fotos_valores(producto: VendorProduct | None) -> list[dict]:
    """Fotos actuales de un producto, para pintar la lista reordenable del formulario.

    A diferencia de la versión anterior (lista fija de 5 posiciones con
    huecos), ahora es una lista de longitud variable con el id de cada
    foto — el id es lo que `producto_fotos.js` necesita para armar los
    inputs hidden `orden_fotos`/`fotos_a_quitar` al arrastrar o quitar.

    Args:
        producto: Producto existente, o None para un formulario vacío.

    Returns:
        Lista de dicts `{"id": int, "url": str}`, en el orden guardado
        (`VendorProductFoto.orden`) — la primera es la portada.
    """
    if producto is None:
        return []
    return [{"id": foto.id, "url": foto.url} for foto in producto.fotos]


def _producto_a_valores(producto: VendorProduct | None) -> dict:
    """Convierte un `VendorProduct` (o None) en un dict plano para el formulario.

    Args:
        producto: Producto existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if producto is None:
        return {
            "titulo": "",
            "descripcion": "",
            "precio": "",
            "fotos": _fotos_valores(None),
            "activo": True,
            "badge": None,
            "estado_stock": None,
            "categoria_id": None,
        }
    return {
        "titulo": producto.titulo,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "fotos": _fotos_valores(producto),
        "activo": producto.activo,
        "badge": producto.badge,
        "estado_stock": producto.estado_stock,
        "categoria_id": producto.categoria_id,
    }


def _leer_datos_producto(form: ImmutableMultiDict) -> tuple[dict, str | None]:
    """Extrae, tipa y valida los campos de texto del formulario de producto.

    Las fotos se manejan aparte (`request.files`, ver `_resolver_fotos_producto`
    y las rutas de abajo) — este helper solo se encarga de título,
    descripción, precio y estado.

    Args:
        form: `request.form` de Flask.

    Returns:
        Tupla `(datos, error)`: `datos` con los valores tipados (título,
        descripción, precio, activo — sin `fotos`), y `error` con un
        mensaje si algún campo no es válido, o None si todo está bien.
    """
    titulo = form.get("titulo", "").strip()
    if not titulo:
        return {**_producto_a_valores(None)}, "El título es obligatorio."

    precio_raw = form.get("precio", "").strip()
    try:
        precio = Decimal(precio_raw)
    except InvalidOperation:
        return {**_producto_a_valores(None), "titulo": titulo}, f'"{precio_raw}" no es un precio válido.'
    if precio < 0:
        return {**_producto_a_valores(None), "titulo": titulo}, "El precio no puede ser negativo."

    datos = {
        "titulo": titulo,
        "descripcion": form.get("descripcion", "").strip(),
        "precio": precio,
        "activo": form.get("activo") == "on",
    }
    return datos, None


@vendedor_bp.route("/productos/nuevo", methods=["GET", "POST"])
@requiere_vendor
def producto_nuevo():
    """Formulario para subir un producto nuevo a la tienda (hasta 5 fotos)."""
    vendor = vendor_actual()
    plan_plus_activo = plan_plus_vigente(vendor)
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_producto(request.form)
        # El selector de badge/estado de stock/categoría (puntos 14, 17 y
        # 18) solo se muestra/acepta con Plus vigente — igual que
        # color_acento en el perfil. Un producto nuevo no tiene valor
        # previo que preservar, así que sin Plus simplemente no se guarda
        # ninguno.
        badge = request.form.get("badge", "") if plan_plus_activo else ""
        estado_stock = request.form.get("estado_stock", "") if plan_plus_activo else ""
        categoria_id_raw = request.form.get("categoria_id", "") if plan_plus_activo else ""
        categoria_id = int(categoria_id_raw) if categoria_id_raw.isdigit() else None
        if error:
            flash(error, "error")
            return render_template(
                "vendedor/producto_form.html",
                producto=None,
                valores={
                    **datos,
                    "fotos": _fotos_valores(None),
                    "badge": badge or None,
                    "estado_stock": estado_stock or None,
                    "categoria_id": categoria_id,
                },
                max_fotos=MAX_FOTOS_PRODUCTO,
                plan_plus_activo=plan_plus_activo,
                badges=listar_badges_producto(),
                estados_stock=listar_estados_stock(),
                categorias=listar_categorias_de_vendor(vendor),
            )

        fotos_urls, error_fotos, advertencia_fotos = _resolver_fotos_producto(vendor, None)
        if error_fotos:
            flash(error_fotos, "error")
            return render_template(
                "vendedor/producto_form.html",
                producto=None,
                valores={
                    **datos,
                    "fotos": _fotos_valores(None),
                    "badge": badge or None,
                    "estado_stock": estado_stock or None,
                    "categoria_id": categoria_id,
                },
                max_fotos=MAX_FOTOS_PRODUCTO,
                plan_plus_activo=plan_plus_activo,
                badges=listar_badges_producto(),
                estados_stock=listar_estados_stock(),
                categorias=listar_categorias_de_vendor(vendor),
            )

        crear_producto(
            vendor,
            titulo=datos["titulo"],
            descripcion=datos["descripcion"],
            precio=datos["precio"],
            fotos_urls=fotos_urls,
            badge=badge,
            estado_stock=estado_stock,
            categoria_id=categoria_id,
        )
        if advertencia_fotos:
            flash(advertencia_fotos, "error")
        flash(f'Producto "{datos["titulo"]}" publicado.', "success")
        return redirect(url_for("vendedor.dashboard"))
    return render_template(
        "vendedor/producto_form.html",
        producto=None,
        valores=_producto_a_valores(None),
        max_fotos=MAX_FOTOS_PRODUCTO,
        plan_plus_activo=plan_plus_activo,
        badges=listar_badges_producto(),
        estados_stock=listar_estados_stock(),
        categorias=listar_categorias_de_vendor(vendor),
    )


@vendedor_bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@requiere_vendor
def producto_editar(producto_id: int):
    """Formulario para editar un producto existente de la tienda (hasta 5 fotos)."""
    vendor = vendor_actual()
    plan_plus_activo = plan_plus_vigente(vendor)
    producto = obtener_producto_de_vendor(vendor, producto_id)
    if producto is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_producto(request.form)
        # Igual que en producto_nuevo: badge/estado de stock/categoría
        # solo pueden cambiarse con Plus vigente. Sin Plus se conserva el
        # valor que el producto ya tenía en vez de borrarlo (mismo
        # criterio que color_acento).
        if plan_plus_activo:
            badge = request.form.get("badge", "")
            estado_stock = request.form.get("estado_stock", "")
            categoria_id_raw = request.form.get("categoria_id", "")
            categoria_id = int(categoria_id_raw) if categoria_id_raw.isdigit() else None
        else:
            badge = producto.badge or ""
            estado_stock = producto.estado_stock or ""
            categoria_id = producto.categoria_id
        if error:
            flash(error, "error")
            return render_template(
                "vendedor/producto_form.html",
                producto=producto,
                valores={
                    **datos,
                    "fotos": _fotos_valores(producto),
                    "badge": badge or None,
                    "estado_stock": estado_stock or None,
                    "categoria_id": categoria_id,
                },
                max_fotos=MAX_FOTOS_PRODUCTO,
                plan_plus_activo=plan_plus_activo,
                badges=listar_badges_producto(),
                estados_stock=listar_estados_stock(),
                categorias=listar_categorias_de_vendor(vendor),
            )

        fotos_urls, error_fotos, advertencia_fotos = _resolver_fotos_producto(vendor, producto)
        if error_fotos:
            flash(error_fotos, "error")
            return render_template(
                "vendedor/producto_form.html",
                producto=producto,
                valores={
                    **datos,
                    "fotos": _fotos_valores(producto),
                    "badge": badge or None,
                    "estado_stock": estado_stock or None,
                    "categoria_id": categoria_id,
                },
                max_fotos=MAX_FOTOS_PRODUCTO,
                plan_plus_activo=plan_plus_activo,
                badges=listar_badges_producto(),
                estados_stock=listar_estados_stock(),
                categorias=listar_categorias_de_vendor(vendor),
            )

        actualizar_producto(
            producto,
            titulo=datos["titulo"],
            descripcion=datos["descripcion"],
            precio=datos["precio"],
            fotos_urls=fotos_urls,
            activo=datos["activo"],
            badge=badge,
            estado_stock=estado_stock,
            categoria_id=categoria_id,
        )
        if advertencia_fotos:
            flash(advertencia_fotos, "error")
        flash(f'Producto "{datos["titulo"]}" actualizado.', "success")
        return redirect(url_for("vendedor.dashboard"))
    return render_template(
        "vendedor/producto_form.html",
        producto=producto,
        valores=_producto_a_valores(producto),
        max_fotos=MAX_FOTOS_PRODUCTO,
        plan_plus_activo=plan_plus_activo,
        badges=listar_badges_producto(),
        estados_stock=listar_estados_stock(),
        categorias=listar_categorias_de_vendor(vendor),
    )


@vendedor_bp.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@requiere_vendor
def producto_eliminar(producto_id: int):
    """Elimina un producto de la tienda (y todas sus fotos en R2, si tenía)."""
    _verificar_csrf()
    producto = obtener_producto_de_vendor(vendor_actual(), producto_id)
    if producto is None:
        abort(404)
    titulo = producto.titulo
    for foto in producto.fotos:
        r2_service.eliminar_imagen(foto.url)
    eliminar_producto(producto)
    flash(f'Producto "{titulo}" eliminado.', "success")
    return redirect(url_for("vendedor.dashboard"))


# --- Enlaces personalizados (estilo Linktree) ---


def _link_a_valores(link) -> dict:
    """Convierte un `VendorLink` (o None) en un dict plano para el formulario.

    Args:
        link: Enlace existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if link is None:
        return {"titulo": "", "url": "", "activo": True}
    return {"titulo": link.titulo, "url": link.url, "activo": link.activo}


@vendedor_bp.route("/enlaces")
@requiere_vendor
def enlaces():
    """Lista los enlaces personalizados de la tienda del vendedor."""
    return render_template("vendedor/enlaces.html", links=listar_links_de_vendor(vendor_actual()))


@vendedor_bp.route("/enlaces/nuevo", methods=["GET", "POST"])
@requiere_vendor
def enlace_nuevo():
    """Formulario para agregar un enlace nuevo a la tienda."""
    if request.method == "POST":
        _verificar_csrf()
        titulo = request.form.get("titulo", "")
        url = request.form.get("url", "")
        try:
            crear_link(vendor_actual(), titulo=titulo, url=url)
        except LinkInvalidoError as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/enlace_form.html", link=None, valores={"titulo": titulo, "url": url, "activo": True}
            )
        flash(f'Enlace "{titulo}" agregado.', "success")
        return redirect(url_for("vendedor.enlaces"))
    return render_template("vendedor/enlace_form.html", link=None, valores=_link_a_valores(None))


@vendedor_bp.route("/enlaces/<int:link_id>/editar", methods=["GET", "POST"])
@requiere_vendor
def enlace_editar(link_id: int):
    """Formulario para editar un enlace existente de la tienda."""
    vendor = vendor_actual()
    link = obtener_link_de_vendor(vendor, link_id)
    if link is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        titulo = request.form.get("titulo", "")
        url = request.form.get("url", "")
        activo = request.form.get("activo") == "on"
        try:
            actualizar_link(link, titulo=titulo, url=url, activo=activo)
        except LinkInvalidoError as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/enlace_form.html", link=link, valores={"titulo": titulo, "url": url, "activo": activo}
            )
        flash(f'Enlace "{titulo}" actualizado.', "success")
        return redirect(url_for("vendedor.enlaces"))
    return render_template("vendedor/enlace_form.html", link=link, valores=_link_a_valores(link))


@vendedor_bp.route("/enlaces/<int:link_id>/eliminar", methods=["POST"])
@requiere_vendor
def enlace_eliminar(link_id: int):
    """Elimina un enlace de la tienda."""
    _verificar_csrf()
    link = obtener_link_de_vendor(vendor_actual(), link_id)
    if link is None:
        abort(404)
    titulo = link.titulo
    eliminar_link(link)
    flash(f'Enlace "{titulo}" eliminado.', "success")
    return redirect(url_for("vendedor.enlaces"))


@vendedor_bp.route("/enlaces/<int:link_id>/mover", methods=["POST"])
@requiere_vendor
def enlace_mover(link_id: int):
    """Sube o baja un enlace un puesto en el orden de la tienda."""
    _verificar_csrf()
    vendor = vendor_actual()
    link = obtener_link_de_vendor(vendor, link_id)
    if link is None:
        abort(404)
    direccion = request.args.get("direccion", "")
    if direccion in ("arriba", "abajo"):
        mover_link(vendor, link, direccion=direccion)
    return redirect(url_for("vendedor.enlaces"))


# --- Categorías de producto (punto 18) ---


def _categoria_a_valores(categoria) -> dict:
    """Convierte una `VendorCategoria` (o None) en un dict plano para el formulario.

    Args:
        categoria: Categoría existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if categoria is None:
        return {"nombre": ""}
    return {"nombre": categoria.nombre}


@vendedor_bp.route("/categorias")
@requiere_vendor
def categorias():
    """Lista las categorías de producto de la tienda del vendedor."""
    return render_template(
        "vendedor/categorias.html", categorias=listar_categorias_de_vendor(vendor_actual())
    )


@vendedor_bp.route("/categorias/nueva", methods=["GET", "POST"])
@requiere_vendor
def categoria_nueva():
    """Formulario para agregar una categoría nueva a la tienda."""
    if request.method == "POST":
        _verificar_csrf()
        nombre = request.form.get("nombre", "")
        try:
            crear_categoria(vendor_actual(), nombre=nombre)
        except CategoriaInvalidaError as exc:
            flash(str(exc), "error")
            return render_template("vendedor/categoria_form.html", categoria=None, valores={"nombre": nombre})
        flash(f'Categoría "{nombre}" agregada.', "success")
        return redirect(url_for("vendedor.categorias"))
    return render_template("vendedor/categoria_form.html", categoria=None, valores=_categoria_a_valores(None))


@vendedor_bp.route("/categorias/<int:categoria_id>/editar", methods=["GET", "POST"])
@requiere_vendor
def categoria_editar(categoria_id: int):
    """Formulario para editar una categoría existente de la tienda."""
    vendor = vendor_actual()
    categoria = obtener_categoria_de_vendor(vendor, categoria_id)
    if categoria is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        nombre = request.form.get("nombre", "")
        try:
            actualizar_categoria(categoria, nombre=nombre)
        except CategoriaInvalidaError as exc:
            flash(str(exc), "error")
            return render_template(
                "vendedor/categoria_form.html", categoria=categoria, valores={"nombre": nombre}
            )
        flash(f'Categoría "{nombre}" actualizada.', "success")
        return redirect(url_for("vendedor.categorias"))
    return render_template(
        "vendedor/categoria_form.html", categoria=categoria, valores=_categoria_a_valores(categoria)
    )


@vendedor_bp.route("/categorias/<int:categoria_id>/eliminar", methods=["POST"])
@requiere_vendor
def categoria_eliminar(categoria_id: int):
    """Elimina una categoría de la tienda (los productos que la tenían quedan sin categoría)."""
    _verificar_csrf()
    categoria = obtener_categoria_de_vendor(vendor_actual(), categoria_id)
    if categoria is None:
        abort(404)
    nombre = categoria.nombre
    eliminar_categoria(categoria)
    flash(f'Categoría "{nombre}" eliminada.', "success")
    return redirect(url_for("vendedor.categorias"))


# --- Avisos "avísame cuando vuelva" (punto 17) ---


@vendedor_bp.route("/avisos")
@requiere_vendor
def avisos():
    """Lista los pedidos de "avísame cuando vuelva" recibidos en todos los productos de la tienda."""
    return render_template("vendedor/avisos.html", avisos=listar_avisos_de_vendor(vendor_actual()))
