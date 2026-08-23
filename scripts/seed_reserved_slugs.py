"""Carga inicial (seed) de palabras reservadas de subdominio.

Uso (desde la raíz del proyecto, con el venv activo):
    python scripts/seed_reserved_slugs.py

Idempotente: usa `palabra` como clave — si ya existe, no hace nada; si
no existe, la crea. Se puede correr tantas veces como haga falta (ej.
después de agregar palabras nuevas a la lista de abajo).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Al correr este archivo directamente (`python scripts/seed_reserved_slugs.py`),
# Python solo agrega la carpeta `scripts/` a sys.path, no la raíz del
# proyecto — por eso `from app import ...` fallaba con ModuleNotFoundError.
# Se agrega la raíz (un nivel arriba de este archivo) a mano.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import ReservedSlug  # noqa: E402

# Ver la justificación de cada categoría en claude/spec-tiendas-vendedor.md
# (sección "Palabras reservadas de subdominio") en el proyecto eServicios.
# Incluye "monitor" y "temp", que ya están en uso real en el Cloudflare
# Tunnel de producción (Netdata y un servicio temporal).
PALABRAS_RESERVADAS: list[str] = [
    # Infraestructura / correo
    "www", "mail", "webmail", "smtp", "pop", "pop3", "imap", "mx",
    "ns", "ns1", "ns2", "ns3", "ns4", "ftp", "sftp", "ssh", "vpn",
    "autodiscover", "autoconfig", "cpanel", "whm", "dns",
    # Sistema / admin
    "admin", "administrator", "panel", "dashboard", "root", "system",
    "sys", "config", "settings", "setup", "install", "monitor",
    "status", "health", "metrics", "stats", "logs", "backend",
    "internal", "private", "cache", "edge", "proxy", "gateway",
    "server", "servers", "node", "cluster",
    # Autenticación / cuentas
    "login", "signin", "signup", "register", "logout", "auth",
    "oauth", "sso", "session", "token", "account", "accounts",
    "cuenta", "perfil", "profile",
    # Contenido genérico del sitio
    "app", "api", "blog", "news", "noticias", "docs", "help",
    "ayuda", "support", "soporte", "faq", "contact", "contacto",
    "about", "nosotros", "terms", "terminos", "privacy",
    "privacidad", "legal", "policy", "politica", "security",
    "seguridad",
    # Marketplace de empleos (línea de negocio hermana, polunga.com)
    "jobs", "careers", "empleos", "empleo", "trabajo", "trabajos",
    "partners", "afiliados", "referral", "ads", "marketing",
    # Entornos de prueba
    "test", "testing", "demo", "staging", "stage", "dev", "develop",
    "sandbox", "preview", "beta", "alpha", "temp", "tmp",
    # Correo transaccional / anti-spam
    "noreply", "no-reply", "reply", "bounce", "feedback", "abuse",
    "spam", "phishing", "info", "notifications", "notify",
    # CDN / estáticos
    "static", "assets", "cdn", "img", "images", "media", "files",
    "download", "downloads", "uploads", "storage",
    # Términos genéricos de alto valor (evitar squatting)
    "shop", "store", "tienda", "mercado", "market",
    # Marcas relacionadas (proyectos hermanos, ver .clinerules)
    "polunga", "ceiba21",
]


def main() -> None:
    """Punto de entrada del script de seed."""
    app = create_app()
    with app.app_context():
        creadas = 0
        for palabra in PALABRAS_RESERVADAS:
            if ReservedSlug.query.filter_by(palabra=palabra).first() is not None:
                continue
            db.session.add(ReservedSlug(palabra=palabra))
            creadas += 1
        db.session.commit()
        print(
            f"Listo: {creadas} palabra(s) reservada(s) nueva(s) agregada(s) "
            f"({len(PALABRAS_RESERVADAS) - creadas} ya existían)."
        )


if __name__ == "__main__":
    main()
