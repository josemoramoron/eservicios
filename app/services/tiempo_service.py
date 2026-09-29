"""Hora actual en UTC, sin tzinfo — reemplazo de `datetime.utcnow()`.

`datetime.utcnow()` está deprecado desde Python 3.12 (se elimina en una
versión futura) porque devuelve un datetime *naive* (sin zona horaria),
algo que la librería considera ambiguo. El reemplazo que sugiere la
documentación, `datetime.now(datetime.UTC)`, devuelve un datetime
*aware* — pero ninguna columna `DateTime` de los modelos de este
proyecto usa `timezone=True` (ver app/models/), o sea que Postgres las
guarda como `TIMESTAMP WITHOUT TIME ZONE` y SQLAlchemy las lee de
vuelta como datetimes naive. Comparar un datetime aware contra uno de
esos valores naive revienta con
`TypeError: can't compare offset-naive and offset-aware datetimes`.

Migrar las columnas a `timezone=True` es una migración de BD en
producción — fuera de alcance por ahora (ver regla del proyecto:
preferir lógica en código sobre ALTER TABLE). Este helper es el punto
único para obtener la hora actual sin el warning, sin tocar la BD y
sin cambiar el comportamiento existente.
"""
from __future__ import annotations

from datetime import UTC, datetime


def ahora_utc() -> datetime:
    """Hora actual en UTC, como datetime naive (sin tzinfo).

    Returns:
        El mismo valor que devolvía `datetime.utcnow()` (naive, en
        UTC), pero sin usar la función deprecada — compatible con las
        columnas `DateTime` existentes sin necesitar migración.
    """
    return datetime.now(UTC).replace(tzinfo=None)
