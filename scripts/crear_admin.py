"""Crea el primer usuario administrador (acceso al panel `/admin`).

Uso (desde la raíz del proyecto, con el venv activo):
    python scripts/crear_admin.py

Interactivo: pide correo, rol y contraseña (con `getpass`, sin mostrarla
en pantalla y sin dejarla escrita en ningún archivo ni en el historial
de la terminal). Si el correo ya existe, ofrece actualizar la
contraseña y/o el rol en vez de fallar.
"""
from __future__ import annotations

import sys
from getpass import getpass
from pathlib import Path

# Al correr este archivo directamente (`python scripts/crear_admin.py`),
# Python solo agrega la carpeta `scripts/` a sys.path, no la raíz del
# proyecto — por eso `from app import ...` fallaba con ModuleNotFoundError.
# Se agrega la raíz (un nivel arriba de este archivo) a mano.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import AdminUser, RolAdmin  # noqa: E402

ROLES = {"1": RolAdmin.OWNER, "2": RolAdmin.STAFF}


def pedir_correo() -> str:
    """Pide un correo por consola y lo valida de forma básica.

    Returns:
        El correo ingresado, en minúsculas y sin espacios.
    """
    while True:
        correo = input("Correo del administrador: ").strip().lower()
        if "@" in correo and "." in correo.split("@")[-1]:
            return correo
        print("  Correo inválido, intenta de nuevo.")


def pedir_rol() -> RolAdmin:
    """Pide el rol del administrador por consola.

    Returns:
        `RolAdmin.OWNER` o `RolAdmin.STAFF` según la elección.
    """
    while True:
        eleccion = input("Rol [1] owner  [2] staff (default 1): ").strip() or "1"
        if eleccion in ROLES:
            return ROLES[eleccion]
        print("  Opción inválida, escribe 1 o 2.")


def pedir_password() -> str:
    """Pide la contraseña dos veces (sin mostrarla) y valida longitud mínima.

    Returns:
        La contraseña en texto plano, ya confirmada por el usuario.
    """
    while True:
        password = getpass("Contraseña (mínimo 8 caracteres, no se mostrará): ")
        if len(password) < 8:
            print("  Muy corta, usa al menos 8 caracteres.")
            continue
        confirmacion = getpass("Confirma la contraseña: ")
        if password != confirmacion:
            print("  No coinciden, intenta de nuevo.")
            continue
        return password


def main() -> None:
    """Punto de entrada del script interactivo."""
    app = create_app()
    with app.app_context():
        correo = pedir_correo()
        existente = AdminUser.query.filter_by(email=correo).first()

        if existente is not None:
            print(f"\nYa existe un administrador con ese correo (rol actual: {existente.rol.value}).")
            respuesta = input("¿Actualizar su contraseña y rol? [s/N]: ").strip().lower()
            if respuesta != "s":
                print("Cancelado, no se hizo ningún cambio.")
                return
            rol = pedir_rol()
            password = pedir_password()
            existente.rol = rol
            existente.set_password(password)
            db.session.commit()
            print(f"\nListo: administrador '{correo}' actualizado (rol: {rol.value}).")
            return

        rol = pedir_rol()
        password = pedir_password()
        admin = AdminUser(email=correo, rol=rol)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"\nListo: administrador '{correo}' creado (rol: {rol.value}). Ya puedes entrar en /admin/login.")


if __name__ == "__main__":
    main()
