"""Subida de imágenes a Cloudflare R2 (fotos de productos, logo y portada de tienda).

Cliente S3-compatible vía boto3, apuntando al endpoint privado de R2 de
la cuenta (`R2_ACCOUNT_ID`). Las credenciales y el nombre del bucket
vienen de variables de entorno (ver `.env.example`) — nunca se
hardcodean. Las URLs públicas que se guardan en la base de datos se
arman con `R2_PUBLIC_BASE_URL` (el dominio público conectado al
bucket, ej. `https://cdn.eservicios.org`), que es distinto del
endpoint S3 usado para subir/borrar (ese es privado y nunca se expone
al navegador).
"""
from __future__ import annotations

import io
import uuid

import boto3
from botocore.config import Config as BotoConfig
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

# Mapea el mimetype que reporta el navegador a la extensión guardada en R2.
# Nota: el mimetype lo declara el cliente, no es una verificación de
# contenido real — coherente con el resto del sitio, que hoy acepta
# `imagen_url` de texto libre sin ninguna validación. Suficiente para
# esta primera versión; una revisión de "magic bytes" queda como mejora
# futura si se detectan abusos. `_comprimir_imagen` sí abre el archivo
# con Pillow antes de subirlo, así que un archivo con mimetype falseado
# que no sea una imagen real termina rechazado igual (`ArchivoInvalidoError`).
_TIPOS_PERMITIDOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB por imagen

# Ningún uso en el sitio (foto de producto, logo, portada) necesita más
# resolución que esta — limitarla reduce el peso de archivo (menos
# costo de storage y de banda, tienda pública más rápida) sin pérdida
# visible en pantalla. `_CALIDAD_JPEG_WEBP` es el punto donde JPG/WEBP
# ya no pierden calidad perceptible a simple vista.
_DIMENSION_MAXIMA_PX = 1600
_CALIDAD_JPEG_WEBP = 85


class ArchivoInvalidoError(Exception):
    """El archivo subido no es una imagen de un tipo permitido (JPG/PNG/WEBP)."""


class ArchivoDemasiadoGrandeError(Exception):
    """El archivo supera el tamaño máximo permitido (5 MB)."""


def _cliente_r2():
    """Crea el cliente S3 apuntando al endpoint privado de Cloudflare R2.

    Returns:
        Cliente boto3 configurado con las credenciales del bucket de eServicios.
    """
    return boto3.client(
        "s3",
        endpoint_url=f"https://{current_app.config['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=current_app.config["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["R2_SECRET_ACCESS_KEY"],
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def _comprimir_imagen(archivo: FileStorage, extension: str) -> tuple[io.BytesIO, str]:
    """Redimensiona y recomprime una imagen antes de subirla a R2.

    También corrige la orientación EXIF (fotos tomadas con el celular
    en distintas posiciones se ven "rotadas" si se sirven sin
    interpretar ese metadato). El formato de salida es siempre el mismo
    que el de entrada — no se convierte PNG a JPG ni viceversa, para no
    perder transparencia en un PNG que la use.

    Args:
        archivo: Archivo original recibido en `request.files`, ya
            validado por tipo y tamaño en `subir_imagen`.
        extension: Extensión ya resuelta (`jpg`, `png` o `webp`).

    Returns:
        Tupla `(buffer, content_type)`: el archivo procesado en
        memoria, listo para subir, y su `Content-Type` final.

    Raises:
        ArchivoInvalidoError: Si Pillow no puede abrir el archivo como
            imagen (el mimetype declarado no coincide con el contenido real).
    """
    try:
        imagen = Image.open(archivo.stream)
        imagen.load()
    except UnidentifiedImageError as exc:
        raise ArchivoInvalidoError("El archivo no es una imagen válida.") from exc

    imagen = ImageOps.exif_transpose(imagen)
    if imagen.width > _DIMENSION_MAXIMA_PX or imagen.height > _DIMENSION_MAXIMA_PX:
        imagen.thumbnail((_DIMENSION_MAXIMA_PX, _DIMENSION_MAXIMA_PX), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if extension == "jpg":
        if imagen.mode in ("RGBA", "P", "LA"):
            imagen = imagen.convert("RGB")
        imagen.save(buffer, format="JPEG", quality=_CALIDAD_JPEG_WEBP, optimize=True)
        content_type = "image/jpeg"
    elif extension == "webp":
        imagen.save(buffer, format="WEBP", quality=_CALIDAD_JPEG_WEBP)
        content_type = "image/webp"
    else:  # png
        imagen.save(buffer, format="PNG", optimize=True)
        content_type = "image/png"
    buffer.seek(0)
    return buffer, content_type


def subir_imagen(archivo: FileStorage, *, carpeta: str) -> str:
    """Redimensiona/recomprime una imagen y la sube a R2, devolviendo su URL pública.

    Args:
        archivo: Archivo recibido en `request.files` (campo `type="file"`).
        carpeta: Prefijo dentro del bucket, ej. `"vendors/mitienda/productos"`.

    Returns:
        URL pública lista para guardar en el modelo (`foto_url`, `logo_url`, etc.).

    Raises:
        ArchivoInvalidoError: Si el archivo no es una imagen JPG, PNG o WEBP
            (por mimetype declarado, o porque Pillow no logra abrirlo).
        ArchivoDemasiadoGrandeError: Si supera los 5 MB.
    """
    extension = _TIPOS_PERMITIDOS.get(archivo.mimetype)
    if extension is None:
        raise ArchivoInvalidoError("La imagen debe ser JPG, PNG o WEBP.")

    archivo.stream.seek(0, 2)
    tamano = archivo.stream.tell()
    archivo.stream.seek(0)
    if tamano > _TAMANO_MAXIMO_BYTES:
        raise ArchivoDemasiadoGrandeError("La imagen no puede superar los 5 MB.")

    buffer, content_type = _comprimir_imagen(archivo, extension)

    clave = f"{carpeta}/{uuid.uuid4().hex}.{extension}"
    _cliente_r2().upload_fileobj(
        buffer,
        current_app.config["R2_BUCKET"],
        clave,
        ExtraArgs={"ContentType": content_type},
    )
    base = current_app.config["R2_PUBLIC_BASE_URL"].rstrip("/")
    return f"{base}/{clave}"


def eliminar_imagen(url: str | None) -> None:
    """Borra una imagen de R2 a partir de su URL pública, si es nuestra.

    Falla en silencio (no relanza la excepción) si el borrado no se
    puede completar — perder una imagen huérfana en el bucket no
    debería impedir que el resto de un cambio de perfil o producto se
    guarde correctamente.

    Args:
        url: URL pública guardada previamente en el modelo, o None.
    """
    if not url:
        return
    base = current_app.config["R2_PUBLIC_BASE_URL"].rstrip("/")
    if not base or not url.startswith(base + "/"):
        return  # no es una imagen nuestra en R2 (ej. una URL externa de una versión anterior)
    clave = url[len(base) + 1 :]
    try:
        _cliente_r2().delete_object(Bucket=current_app.config["R2_BUCKET"], Key=clave)
    except Exception:  # noqa: BLE001 — un fallo de borrado nunca debe romper el flujo del usuario
        current_app.logger.warning("No se pudo eliminar de R2 la clave: %s", clave)
