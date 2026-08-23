"""Rutas del panel de vendedor (`/vendedor`) — registro, login, perfil y CRUD de productos.

La tienda pública en sí (`<slug>.eservicios.org`) no vive aquí — la
sirve `app/routes/tienda.py` desde el enrutador de subdominios. Este
blueprint es el panel donde el vendedor administra su tienda, siempre
en el dominio principal.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.datastructures import ImmutableMultiDict

from app.models import VendorProduct
from app.services import r2_service
from app.services.auth_service import generar_csrf_token, validar_csrf_token
from app.services.vendor_auth_service import (
    autenticar_vendor,
    cerrar_sesion_vendor,
    iniciar_sesion_vendor,
    requiere_vendor,
    vendor_actual,
)
from app.services.vendor_service import (
    EmailDuplicadoError,
    EmailInvalidoError,
    PasswordActualIncorrectaError,
    PasswordNuevaInvalidaError,
    PerfilInvalidoError,
    SlugDuplicadoError,
    SlugInvalidoError,
    SlugReservadoError,
    actualizar_perfil,
    actualizar_producto,
    cambiar_password,
    crear_producto,
    eliminar_producto,
    listar_productos_de_vendor,
    obtener_producto_de_vendor,
    registrar_vendor,
    slug_disponible,
    validar_formato_slug,
)

vendedor_bp = Blueprint("vendedor", __name__, url_prefix="/vendedor")


@vendedor_bp.context_processor
def inyectar_vendor_actual() -> dict:
    """Expone el vendedor autenticado y el generador de CSRF a las plantillas.

    Returns:
        Diccionario con las claves `vendor` y `csrf_token` para Jinja.
    """
    return {"vendor": vendor_actual(), "csrf_token": generar_csrf_token}


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

        iniciar_sesion_vendor(vendor)
        flash(f'¡Listo! Tu tienda "{vendor.nombre_negocio}" ya está en línea.', "success")
        return redirect(url_for("vendedor.dashboard"))

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
        else:
            iniciar_sesion_vendor(vendor)
            destino = request.args.get("next") or url_for("vendedor.dashboard")
            return redirect(destino)
    return render_template("vendedor/login.html")


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
    )


# --- Perfil: personalización y seguridad ---


@vendedor_bp.route("/perfil", methods=["GET", "POST"])
@requiere_vendor
def perfil():
    """Personalización de la tienda: nombre, WhatsApp, bio, logo y portada."""
    vendor = vendor_actual()
    if request.method == "POST":
        _verificar_csrf()
        nombre_negocio = request.form.get("nombre_negocio", "")
        whatsapp_numero = request.form.get("whatsapp_numero", "")
        bio = request.form.get("bio", "")

        logo_url, error_logo = _subir_imagen_opcional("logo", f"vendors/{vendor.slug}/logo")
        if error_logo:
            flash(error_logo, "error")
            return render_template("vendedor/perfil.html", vendor=vendor)
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
            return render_template("vendedor/perfil.html", vendor=vendor)
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
            )
        except PerfilInvalidoError as exc:
            flash(str(exc), "error")
            return render_template("vendedor/perfil.html", vendor=vendor)

        flash("Perfil actualizado.", "success")
        return redirect(url_for("vendedor.perfil"))
    return render_template("vendedor/perfil.html", vendor=vendor)


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


# --- Productos ---


def _producto_a_valores(producto: VendorProduct | None) -> dict:
    """Convierte un `VendorProduct` (o None) en un dict plano para el formulario.

    Args:
        producto: Producto existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if producto is None:
        return {"titulo": "", "descripcion": "", "precio": "", "foto_url": "", "activo": True}
    return {
        "titulo": producto.titulo,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "foto_url": producto.foto_url or "",
        "activo": producto.activo,
    }


def _leer_datos_producto(form: ImmutableMultiDict) -> tuple[dict, str | None]:
    """Extrae, tipa y valida los campos de texto del formulario de producto.

    La foto se maneja aparte (`request.files`, ver las rutas de abajo) —
    este helper solo se encarga de título, descripción, precio y estado.

    Args:
        form: `request.form` de Flask.

    Returns:
        Tupla `(datos, error)`: `datos` con los valores tipados (misma
        forma que `_producto_a_valores`, sin `foto_url`), y `error` con
        un mensaje si algún campo no es válido, o None si todo está bien.
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
    """Formulario para subir un producto nuevo a la tienda."""
    vendor = vendor_actual()
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_producto(request.form)
        if error:
            flash(error, "error")
            return render_template("vendedor/producto_form.html", producto=None, valores={**datos, "foto_url": ""})

        foto_url, error_foto = _subir_imagen_opcional("foto", f"vendors/{vendor.slug}/productos")
        if error_foto:
            flash(error_foto, "error")
            return render_template("vendedor/producto_form.html", producto=None, valores={**datos, "foto_url": ""})

        crear_producto(
            vendor,
            titulo=datos["titulo"],
            descripcion=datos["descripcion"],
            precio=datos["precio"],
            foto_url=foto_url,
        )
        flash(f'Producto "{datos["titulo"]}" publicado.', "success")
        return redirect(url_for("vendedor.dashboard"))
    return render_template("vendedor/producto_form.html", producto=None, valores=_producto_a_valores(None))


@vendedor_bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@requiere_vendor
def producto_editar(producto_id: int):
    """Formulario para editar un producto existente de la tienda."""
    vendor = vendor_actual()
    producto = obtener_producto_de_vendor(vendor, producto_id)
    if producto is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_producto(request.form)
        if error:
            flash(error, "error")
            return render_template(
                "vendedor/producto_form.html", producto=producto, valores={**datos, "foto_url": producto.foto_url or ""}
            )

        foto_url, error_foto = _subir_imagen_opcional("foto", f"vendors/{vendor.slug}/productos")
        if error_foto:
            flash(error_foto, "error")
            return render_template(
                "vendedor/producto_form.html", producto=producto, valores={**datos, "foto_url": producto.foto_url or ""}
            )
        if foto_url is not None:
            r2_service.eliminar_imagen(producto.foto_url)
        elif request.form.get("quitar_foto") == "on":
            r2_service.eliminar_imagen(producto.foto_url)
            foto_url = None
        else:
            foto_url = producto.foto_url

        actualizar_producto(
            producto,
            titulo=datos["titulo"],
            descripcion=datos["descripcion"],
            precio=datos["precio"],
            foto_url=foto_url,
            activo=datos["activo"],
        )
        flash(f'Producto "{datos["titulo"]}" actualizado.', "success")
        return redirect(url_for("vendedor.dashboard"))
    return render_template(
        "vendedor/producto_form.html", producto=producto, valores=_producto_a_valores(producto)
    )


@vendedor_bp.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@requiere_vendor
def producto_eliminar(producto_id: int):
    """Elimina un producto de la tienda (y su foto en R2, si tenía)."""
    _verificar_csrf()
    producto = obtener_producto_de_vendor(vendor_actual(), producto_id)
    if producto is None:
        abort(404)
    titulo = producto.titulo
    r2_service.eliminar_imagen(producto.foto_url)
    eliminar_producto(producto)
    flash(f'Producto "{titulo}" eliminado.', "success")
    return redirect(url_for("vendedor.dashboard"))
