# eServicios

Marketplace de empleos | Publicaciones de anuncio.

## Stack

Flask 3.1 + PostgreSQL + SQLAlchemy + Redis + Python 3.13, siguiendo el mismo
patrón de arquitectura de Ceiba21 (ver `.clinerules` del proyecto hermano):
Routes → Services → Models.

## Dev local (Windows)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # y editar con tus credenciales locales
flask --app wsgi run
```

Prueba: http://localhost:5000/health

## Deploy

```powershell
git push production main
```

El hook `post-receive` en la Pi corre `deploy.sh` automáticamente.
