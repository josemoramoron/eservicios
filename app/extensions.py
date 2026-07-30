"""Instancias compartidas de extensiones de Flask.

Se inicializan aquí sin una app asociada para evitar imports circulares;
se enlazan a la instancia real dentro de create_app() en app/__init__.py.
"""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
