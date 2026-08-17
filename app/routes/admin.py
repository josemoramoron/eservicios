"""Rutas del panel de administración (`/admin`) — CRUD del catálogo."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.datastructures import ImmutableMultiDict

from app.models import Category, Offering, TipoOffering
from app.services.auth_service import (
    admin_actual,
    autenticar,
    cerrar_sesion_admin,
    generar_csrf_token,
    iniciar_sesion_admin,
    requiere_admin,
    validar_csrf_token,
)
from app.services.catalogo_service import (
    CategoriaConOfertasError,
    SlugDuplicadoError,
    actualizar_categoria,
    actualizar_oferta,
    crear_categoria,
    crear_oferta,
    eliminar_categoria,
    eliminar_oferta,
    listar_categorias,
    listar_todas_las_ofertas,
    obtener_categoria_por_id,
    obtener_oferta_por_id,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.context_processor
def inyectar_admin_actual() -> dict:
    """Expone el admin autenticado y el generador de CSRF a las plantillas.

    Returns:
        Diccionario con las claves `admin` y `csrf_token` para Jinja.
    """
    return {"admin": admin_actual(), "csrf_token": generar_csrf_token}


def _verificar_csrf() -> None:
    """Aborta la petición con 400 si el token CSRF del form no es válido."""
    if not validar_csrf_token(request.form.get("csrf_token")):
        abort(400, description="Token de seguridad inválido o expirado. Recarga la página e intenta de nuevo.")


# --- Autenticación ---


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Formulario de inicio de sesión del panel."""
    if admin_actual() is not None:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        _verificar_csrf()
        admin = autenticar(request.form.get("email", ""), request.form.get("password", ""))
        if admin is None:
            flash("Correo o contraseña incorrectos.", "error")
        else:
            iniciar_sesion_admin(admin)
            destino = request.args.get("next") or url_for("admin.dashboard")
            return redirect(destino)
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
def logout():
    """Cierra la sesión del panel."""
    _verificar_csrf()
    cerrar_sesion_admin()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("admin.login"))


# --- Dashboard ---


@admin_bp.route("/")
@requiere_admin
def dashboard():
    """Portada del panel con conteos rápidos."""
    return render_template(
        "admin/dashboard.html",
        total_categorias=len(listar_categorias()),
        total_ofertas=len(listar_todas_las_ofertas()),
    )


# --- Categorías ---


def _categoria_a_valores(categoria: Category | None) -> dict:
    """Convierte una `Category` (o None) en un dict plano para el formulario.

    Args:
        categoria: Categoría existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if categoria is None:
        return {"nombre": "", "slug": "", "descripcion": "", "orden": 0, "imagen_url": ""}
    return {
        "nombre": categoria.nombre,
        "slug": categoria.slug,
        "descripcion": categoria.descripcion or "",
        "orden": categoria.orden,
        "imagen_url": categoria.imagen_url or "",
    }


def _leer_datos_categoria(form: ImmutableMultiDict) -> dict:
    """Extrae y tipa los campos del formulario de categoría.

    Args:
        form: `request.form` de Flask.

    Returns:
        Diccionario con los valores tipados listos para `catalogo_service`.
    """
    try:
        orden = int(form.get("orden", "0") or 0)
    except ValueError:
        orden = 0
    return {
        "nombre": form.get("nombre", "").strip(),
        "slug": form.get("slug", "").strip().lower(),
        "descripcion": form.get("descripcion", "").strip(),
        "orden": orden,
        "imagen_url": form.get("imagen_url", "").strip(),
    }


@admin_bp.route("/categorias")
@requiere_admin
def categorias_lista():
    """Lista todas las categorías del catálogo."""
    return render_template("admin/categorias_lista.html", categorias=listar_categorias())


@admin_bp.route("/categorias/nueva", methods=["GET", "POST"])
@requiere_admin
def categoria_nueva():
    """Formulario para crear una categoría nueva."""
    if request.method == "POST":
        _verificar_csrf()
        datos = _leer_datos_categoria(request.form)
        try:
            crear_categoria(datos)
        except SlugDuplicadoError as exc:
            flash(str(exc), "error")
            return render_template("admin/categoria_form.html", categoria=None, valores=datos)
        flash(f'Categoría "{datos["nombre"]}" creada.', "success")
        return redirect(url_for("admin.categorias_lista"))
    return render_template("admin/categoria_form.html", categoria=None, valores=_categoria_a_valores(None))


@admin_bp.route("/categorias/<int:categoria_id>/editar", methods=["GET", "POST"])
@requiere_admin
def categoria_editar(categoria_id: int):
    """Formulario para editar una categoría existente."""
    categoria = obtener_categoria_por_id(categoria_id)
    if categoria is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        datos = _leer_datos_categoria(request.form)
        try:
            actualizar_categoria(categoria, datos)
        except SlugDuplicadoError as exc:
            flash(str(exc), "error")
            return render_template("admin/categoria_form.html", categoria=categoria, valores=datos)
        flash(f'Categoría "{datos["nombre"]}" actualizada.', "success")
        return redirect(url_for("admin.categorias_lista"))
    return render_template(
        "admin/categoria_form.html", categoria=categoria, valores=_categoria_a_valores(categoria)
    )


@admin_bp.route("/categorias/<int:categoria_id>/eliminar", methods=["POST"])
@requiere_admin
def categoria_eliminar(categoria_id: int):
    """Elimina una categoría (si no tiene ofertas asociadas)."""
    _verificar_csrf()
    categoria = obtener_categoria_por_id(categoria_id)
    if categoria is None:
        abort(404)
    try:
        eliminar_categoria(categoria)
    except CategoriaConOfertasError as exc:
        flash(str(exc), "error")
    else:
        flash(f'Categoría "{categoria.nombre}" eliminada.', "success")
    return redirect(url_for("admin.categorias_lista"))


# --- Ofertas ---


def _oferta_a_valores(oferta: Offering | None) -> dict:
    """Convierte una `Offering` (o None) en un dict plano para el formulario.

    Args:
        oferta: Oferta existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if oferta is None:
        return {
            "category_id": "",
            "nombre": "",
            "slug": "",
            "tipo": TipoOffering.SERVICIO.value,
            "descripcion": "",
            "imagen_url": "",
            "precio": "",
            "vendible": False,
            "stock": "",
            "destacado": False,
            "activo": True,
        }
    return {
        "category_id": oferta.category_id,
        "nombre": oferta.nombre,
        "slug": oferta.slug,
        "tipo": oferta.tipo.value,
        "descripcion": oferta.descripcion,
        "imagen_url": oferta.imagen_url or "",
        "precio": oferta.precio if oferta.precio is not None else "",
        "vendible": oferta.vendible,
        "stock": oferta.stock if oferta.stock is not None else "",
        "destacado": oferta.destacado,
        "activo": oferta.activo,
    }


def _leer_datos_oferta(form: ImmutableMultiDict) -> tuple[dict, str | None]:
    """Extrae, tipa y valida los campos del formulario de oferta.

    Args:
        form: `request.form` de Flask.

    Returns:
        Tupla `(datos, error)`: `datos` con los valores tipados (misma forma
        que `_oferta_a_valores`, para poder re-renderizar el formulario tal
        cual si algo falla más adelante), y `error` con un mensaje si algún
        campo no es válido, o None si todo está bien.
    """
    precio_raw = form.get("precio", "").strip()
    precio: Decimal | str = ""
    if precio_raw:
        try:
            precio = Decimal(precio_raw)
        except InvalidOperation:
            return {**_oferta_a_valores(None), "nombre": form.get("nombre", "")}, f'"{precio_raw}" no es un precio válido.'

    stock_raw = form.get("stock", "").strip()
    stock: int | str = ""
    if stock_raw:
        try:
            stock = int(stock_raw)
        except ValueError:
            return {**_oferta_a_valores(None), "nombre": form.get("nombre", "")}, f'"{stock_raw}" no es un stock válido.'

    category_id_raw = form.get("category_id", "")
    try:
        category_id = int(category_id_raw)
    except (TypeError, ValueError):
        return {**_oferta_a_valores(None), "nombre": form.get("nombre", "")}, "Selecciona una categoría."

    tipo_raw = form.get("tipo", "")
    try:
        tipo = TipoOffering(tipo_raw)
    except ValueError:
        return {**_oferta_a_valores(None), "nombre": form.get("nombre", "")}, "Tipo de oferta inválido."

    datos = {
        "category_id": category_id,
        "nombre": form.get("nombre", "").strip(),
        "slug": form.get("slug", "").strip().lower(),
        "tipo": tipo.value,
        "descripcion": form.get("descripcion", "").strip(),
        "imagen_url": form.get("imagen_url", "").strip(),
        "precio": precio,
        "vendible": form.get("vendible") == "on",
        "stock": stock,
        "destacado": form.get("destacado") == "on",
        "activo": form.get("activo") == "on",
    }
    return datos, None


@admin_bp.route("/ofertas")
@requiere_admin
def ofertas_lista():
    """Lista todas las ofertas, opcionalmente filtradas por categoría."""
    category_id = request.args.get("categoria", type=int)
    return render_template(
        "admin/ofertas_lista.html",
        ofertas=listar_todas_las_ofertas(category_id),
        categorias=listar_categorias(),
        categoria_seleccionada=category_id,
    )


@admin_bp.route("/ofertas/nueva", methods=["GET", "POST"])
@requiere_admin
def oferta_nueva():
    """Formulario para crear una oferta nueva."""
    categorias = listar_categorias()
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_oferta(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/oferta_form.html", oferta=None, valores=datos, categorias=categorias)
        try:
            crear_oferta(datos)
        except SlugDuplicadoError as exc:
            flash(str(exc), "error")
            return render_template("admin/oferta_form.html", oferta=None, valores=datos, categorias=categorias)
        flash(f'Oferta "{datos["nombre"]}" creada.', "success")
        return redirect(url_for("admin.ofertas_lista"))
    return render_template(
        "admin/oferta_form.html", oferta=None, valores=_oferta_a_valores(None), categorias=categorias
    )


@admin_bp.route("/ofertas/<int:oferta_id>/editar", methods=["GET", "POST"])
@requiere_admin
def oferta_editar(oferta_id: int):
    """Formulario para editar una oferta existente."""
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta is None:
        abort(404)
    categorias = listar_categorias()
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_oferta(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/oferta_form.html", oferta=oferta, valores=datos, categorias=categorias)
        try:
            actualizar_oferta(oferta, datos)
        except SlugDuplicadoError as exc:
            flash(str(exc), "error")
            return render_template("admin/oferta_form.html", oferta=oferta, valores=datos, categorias=categorias)
        flash(f'Oferta "{datos["nombre"]}" actualizada.', "success")
        return redirect(url_for("admin.ofertas_lista"))
    return render_template(
        "admin/oferta_form.html", oferta=oferta, valores=_oferta_a_valores(oferta), categorias=categorias
    )


@admin_bp.route("/ofertas/<int:oferta_id>/eliminar", methods=["POST"])
@requiere_admin
def oferta_eliminar(oferta_id: int):
    """Elimina una oferta del catálogo."""
    _verificar_csrf()
    oferta = obtener_oferta_por_id(oferta_id)
    if oferta is None:
        abort(404)
    eliminar_oferta(oferta)
    flash(f'Oferta "{oferta.nombre}" eliminada.', "success")
    return redirect(url_for("admin.ofertas_lista"))
