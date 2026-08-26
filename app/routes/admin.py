"""Rutas del panel de administración (`/admin`) — CRUD del catálogo."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.datastructures import ImmutableMultiDict

from app.models import Category, EstadoBlogPost, Offering, TipoOffering, Vendor
from app.services.auth_service import (
    admin_actual,
    autenticar,
    cerrar_sesion_admin,
    generar_csrf_token,
    iniciar_sesion_admin,
    requiere_admin,
    validar_csrf_token,
)
from app.services.blog_service import (
    SlugDuplicadoBlogError,
    actualizar_post,
    crear_post,
    eliminar_post,
    listar_todos_los_posts,
    obtener_post_por_id,
)
from app.services.catalogo_service import (
    MAX_FOTOS_OFERTA,
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
from app.services.estadisticas_service import resumen_estadisticas
from app.services.vendor_admin_service import (
    ESTADO_ACTIVOS,
    ESTADO_SUSPENDIDOS,
    eliminar_vendor_permanente,
    estadisticas_globales,
    listar_vendors_admin,
    obtener_vendor_por_id,
    reactivar_vendor,
    restablecer_password_vendor,
    suspender_vendor,
)
from app.services.vendor_service import estado_cambio_slug

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
        total_posts=len(listar_todos_los_posts()),
        total_vendedores=Vendor.query.count(),
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
        Diccionario con los valores a precargar en el formulario. `fotos`
        siempre trae exactamente `MAX_FOTOS_OFERTA` elementos (rellenados
        con cadenas vacías) para que la plantilla pinte un campo fijo por
        posición de la galería.
    """
    fotos = [foto.url for foto in oferta.fotos] if oferta is not None else []
    fotos += [""] * (MAX_FOTOS_OFERTA - len(fotos))

    if oferta is None:
        return {
            "category_id": "",
            "nombre": "",
            "slug": "",
            "tipo": TipoOffering.SERVICIO.value,
            "descripcion": "",
            "imagen_url": "",
            "fotos": fotos,
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
        "fotos": fotos,
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
    fotos = [form.get(f"foto_{i}", "").strip() for i in range(1, MAX_FOTOS_OFERTA + 1)]

    precio_raw = form.get("precio", "").strip()
    precio: Decimal | str = ""
    if precio_raw:
        try:
            precio = Decimal(precio_raw)
        except InvalidOperation:
            return {**_oferta_a_valores(None), "nombre": form.get("nombre", ""), "fotos": fotos}, f'"{precio_raw}" no es un precio válido.'

    stock_raw = form.get("stock", "").strip()
    stock: int | str = ""
    if stock_raw:
        try:
            stock = int(stock_raw)
        except ValueError:
            return {**_oferta_a_valores(None), "nombre": form.get("nombre", ""), "fotos": fotos}, f'"{stock_raw}" no es un stock válido.'

    category_id_raw = form.get("category_id", "")
    try:
        category_id = int(category_id_raw)
    except (TypeError, ValueError):
        return {**_oferta_a_valores(None), "nombre": form.get("nombre", ""), "fotos": fotos}, "Selecciona una categoría."

    tipo_raw = form.get("tipo", "")
    try:
        tipo = TipoOffering(tipo_raw)
    except ValueError:
        return {**_oferta_a_valores(None), "nombre": form.get("nombre", ""), "fotos": fotos}, "Tipo de oferta inválido."

    datos = {
        "category_id": category_id,
        "nombre": form.get("nombre", "").strip(),
        "slug": form.get("slug", "").strip().lower(),
        "tipo": tipo.value,
        "descripcion": form.get("descripcion", "").strip(),
        "imagen_url": form.get("imagen_url", "").strip(),
        "fotos": fotos,
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


# --- Blog ---


def _post_a_valores(post) -> dict:
    """Convierte un `BlogPost` (o None) en un dict plano para el formulario.

    Args:
        post: Artículo existente, o None para un formulario vacío.

    Returns:
        Diccionario con los valores a precargar en el formulario.
    """
    if post is None:
        return {
            "titulo": "",
            "slug": "",
            "resumen": "",
            "contenido_markdown": "",
            "imagen_url": "",
            "estado": EstadoBlogPost.BORRADOR.value,
        }
    return {
        "titulo": post.titulo,
        "slug": post.slug,
        "resumen": post.resumen or "",
        "contenido_markdown": post.contenido_markdown,
        "imagen_url": post.imagen_url or "",
        "estado": post.estado.value,
    }


def _leer_datos_post(form: ImmutableMultiDict) -> tuple[dict, str | None]:
    """Extrae, tipa y valida los campos del formulario de artículo.

    Args:
        form: `request.form` de Flask.

    Returns:
        Tupla `(datos, error)`: `datos` con los valores tipados (misma forma
        que `_post_a_valores`, para poder re-renderizar el formulario tal
        cual si algo falla más adelante), y `error` con un mensaje si algún
        campo no es válido, o None si todo está bien.
    """
    estado_raw = form.get("estado", "")
    try:
        estado = EstadoBlogPost(estado_raw)
    except ValueError:
        datos_reenviados = {
            "titulo": form.get("titulo", "").strip(),
            "slug": form.get("slug", "").strip().lower(),
            "resumen": form.get("resumen", "").strip(),
            "contenido_markdown": form.get("contenido_markdown", ""),
            "imagen_url": form.get("imagen_url", "").strip(),
            "estado": EstadoBlogPost.BORRADOR.value,
        }
        return datos_reenviados, "Estado de publicación inválido."

    titulo = form.get("titulo", "").strip()
    contenido_markdown = form.get("contenido_markdown", "").strip()
    if not titulo or not contenido_markdown:
        datos_reenviados = {
            "titulo": titulo,
            "slug": form.get("slug", "").strip().lower(),
            "resumen": form.get("resumen", "").strip(),
            "contenido_markdown": contenido_markdown,
            "imagen_url": form.get("imagen_url", "").strip(),
            "estado": estado.value,
        }
        return datos_reenviados, "Título y contenido son obligatorios."

    datos = {
        "titulo": titulo,
        "slug": form.get("slug", "").strip().lower(),
        "resumen": form.get("resumen", "").strip(),
        "contenido_markdown": contenido_markdown,
        "imagen_url": form.get("imagen_url", "").strip(),
        "estado": estado.value,
    }
    return datos, None


@admin_bp.route("/blog")
@requiere_admin
def blog_lista():
    """Lista todos los artículos del blog (borradores y publicados)."""
    return render_template("admin/blog_lista.html", posts=listar_todos_los_posts())


@admin_bp.route("/blog/nuevo", methods=["GET", "POST"])
@requiere_admin
def blog_nuevo():
    """Formulario para crear un artículo nuevo."""
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_post(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/blog_form.html", post=None, valores=datos)
        try:
            crear_post(datos)
        except SlugDuplicadoBlogError as exc:
            flash(str(exc), "error")
            return render_template("admin/blog_form.html", post=None, valores=datos)
        flash(f'Artículo "{datos["titulo"]}" creado.', "success")
        return redirect(url_for("admin.blog_lista"))
    return render_template("admin/blog_form.html", post=None, valores=_post_a_valores(None))


@admin_bp.route("/blog/<int:post_id>/editar", methods=["GET", "POST"])
@requiere_admin
def blog_editar(post_id: int):
    """Formulario para editar un artículo existente."""
    post = obtener_post_por_id(post_id)
    if post is None:
        abort(404)
    if request.method == "POST":
        _verificar_csrf()
        datos, error = _leer_datos_post(request.form)
        if error:
            flash(error, "error")
            return render_template("admin/blog_form.html", post=post, valores=datos)
        try:
            actualizar_post(post, datos)
        except SlugDuplicadoBlogError as exc:
            flash(str(exc), "error")
            return render_template("admin/blog_form.html", post=post, valores=datos)
        flash(f'Artículo "{datos["titulo"]}" actualizado.', "success")
        return redirect(url_for("admin.blog_lista"))
    return render_template("admin/blog_form.html", post=post, valores=_post_a_valores(post))


@admin_bp.route("/blog/<int:post_id>/eliminar", methods=["POST"])
@requiere_admin
def blog_eliminar(post_id: int):
    """Elimina un artículo del blog."""
    _verificar_csrf()
    post = obtener_post_por_id(post_id)
    if post is None:
        abort(404)
    eliminar_post(post)
    flash(f'Artículo "{post.titulo}" eliminado.', "success")
    return redirect(url_for("admin.blog_lista"))


# --- Vendedores (e-link) ---


@admin_bp.route("/vendedores")
@requiere_admin
def vendedores_lista():
    """Lista las tiendas de vendedor (e-link), con búsqueda y filtro por estado."""
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    return render_template(
        "admin/vendedores_lista.html",
        vendedores=listar_vendors_admin(busqueda=busqueda or None, estado=estado or None),
        estadisticas=estadisticas_globales(),
        busqueda=busqueda,
        estado_seleccionado=estado,
        estado_activos=ESTADO_ACTIVOS,
        estado_suspendidos=ESTADO_SUSPENDIDOS,
    )


@admin_bp.route("/vendedores/<int:vendor_id>")
@requiere_admin
def vendedor_detalle(vendor_id: int):
    """Detalle de una tienda de vendedor: perfil, estadísticas e historial de subdominios."""
    vendor = obtener_vendor_por_id(vendor_id)
    if vendor is None:
        abort(404)
    return render_template(
        "admin/vendedor_detalle.html",
        vendor=vendor,
        estadisticas=resumen_estadisticas(vendor),
        estado_slug=estado_cambio_slug(vendor),
    )


@admin_bp.route("/vendedores/<int:vendor_id>/suspender", methods=["POST"])
@requiere_admin
def vendedor_suspender(vendor_id: int):
    """Suspende una tienda (`Vendor.activo = False`) — deja de responder su subdominio."""
    _verificar_csrf()
    vendor = obtener_vendor_por_id(vendor_id)
    if vendor is None:
        abort(404)
    suspender_vendor(vendor)
    flash(f'Tienda "{vendor.nombre_negocio}" suspendida.', "success")
    return redirect(request.referrer or url_for("admin.vendedor_detalle", vendor_id=vendor.id))


@admin_bp.route("/vendedores/<int:vendor_id>/reactivar", methods=["POST"])
@requiere_admin
def vendedor_reactivar(vendor_id: int):
    """Reactiva una tienda suspendida (`Vendor.activo = True`)."""
    _verificar_csrf()
    vendor = obtener_vendor_por_id(vendor_id)
    if vendor is None:
        abort(404)
    reactivar_vendor(vendor)
    flash(f'Tienda "{vendor.nombre_negocio}" reactivada.', "success")
    return redirect(request.referrer or url_for("admin.vendedor_detalle", vendor_id=vendor.id))


@admin_bp.route("/vendedores/<int:vendor_id>/restablecer-password", methods=["POST"])
@requiere_admin
def vendedor_restablecer_password(vendor_id: int):
    """Genera una contraseña temporal nueva para el vendedor y la muestra una sola vez."""
    _verificar_csrf()
    vendor = obtener_vendor_por_id(vendor_id)
    if vendor is None:
        abort(404)
    password_temporal = restablecer_password_vendor(vendor)
    flash(
        f'Contraseña temporal para "{vendor.nombre_negocio}": {password_temporal} — '
        "compártesela al vendedor por un canal seguro; no queda guardada en ningún otro lado.",
        "success",
    )
    return redirect(url_for("admin.vendedor_detalle", vendor_id=vendor.id))


@admin_bp.route("/vendedores/<int:vendor_id>/eliminar", methods=["POST"])
@requiere_admin
def vendedor_eliminar(vendor_id: int):
    """Elimina una tienda de vendedor de forma permanente e irreversible.

    Exige que el admin reescriba el slug exacto de la tienda como
    confirmación (mismo patrón que usa el propio vendedor para cambiar
    su subdominio, ver `vendedor/perfil_slug.html`) — evita que un
    click accidental borre una cuenta real.
    """
    _verificar_csrf()
    vendor = obtener_vendor_por_id(vendor_id)
    if vendor is None:
        abort(404)
    confirmacion = request.form.get("confirmacion_slug", "").strip().lower()
    if confirmacion != vendor.slug:
        flash("Escribe el subdominio exacto de la tienda para confirmar la eliminación.", "error")
        return redirect(url_for("admin.vendedor_detalle", vendor_id=vendor.id))
    nombre = vendor.nombre_negocio
    eliminar_vendor_permanente(vendor)
    flash(f'Tienda "{nombre}" eliminada de forma permanente.', "success")
    return redirect(url_for("admin.vendedores_lista"))
