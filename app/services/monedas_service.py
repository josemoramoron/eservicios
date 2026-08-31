"""Monedas disponibles para mostrar los precios de una tienda de vendedor.

A diferencia de `color_acento`/`plantilla`/`badge`/`disponible_ahora`
(funciones de e-link Plus, roadmap Fase 2), elegir la moneda de la
tienda es **gratis para cualquier plan** — decisión explícita de Jose
(roadmap, Fase 2, punto 20, 2026-08-31): mostrar el precio en la moneda
del comprador no es una personalización visual de pago, es una
necesidad básica para que el precio tenga sentido. Por eso `Vendor.moneda`
no tiene ningún resolver de gating (a diferencia de `resolver_acento_vendor`
y similares) — se lee directo en las plantillas.

Vive en `Vendor`, no en `VendorProduct`: toda la tienda cotiza en una
sola moneda, no hay selector por producto. Al registrarse,
`vendor_service.registrar_vendor()`/`registrar_vendor_google()` sugieren
una moneda a partir del código de país del número de WhatsApp (ver
`detectar_moneda_por_whatsapp` abajo) — el vendedor la cambia libremente
después desde `/vendedor/perfil`, sin relación con su WhatsApp actual.

Importante: esto NO es una conversión automática de precios. El número
que el vendedor carga en cada producto (`VendorProduct.precio`) se
muestra tal cual, con el símbolo de la moneda elegida — no hay tasa de
cambio de por medio. Si un vendedor cambia de moneda, sus precios ya
cargados no se recalculan, solo cambia el símbolo con el que se muestran.

**Adenda (2026-08-31):** Jose pidió dos cambios sobre la primera versión
(6 monedas, "Nombre (símbolo)" en el selector):

1. Ampliar la lista lo más posible — de 6 a 25 monedas, cubriendo la
   totalidad de Latinoamérica más las monedas globales más comunes
   (USD, EUR, GBP, CAD, JPY, CNY, INR, AUD, CHF). No es la lista
   completa de las ~180 monedas ISO 4217 del mundo — habría que
   verificar bandera/símbolo de cada una una por una para no meter
   datos incorrectos — pero cubre con holgura la base de usuarios
   realista de eServicios (LatAm + mercados globales grandes). Fácil
   de seguir ampliando: cada moneda nueva es una entrada más en
   `MONEDAS` y, opcionalmente, uno o más prefijos nuevos en
   `_PREFIJO_PAIS_A_MONEDA`.
2. Cambiar la nomenclatura del selector de "Nombre (símbolo)" a
   "🇽🇽 Nombre (CÓDIGO ISO)" — más reconocible de un vistazo. `simbolo`
   se conserva tal cual para `formatear_precio()` (el precio del
   producto en sí no cambió de formato, solo el selector).

**Segunda adenda (2026-08-31, mismo día):** tras ver el precio real en
la tienda pública ("COL$50.00"), Jose pidió simplificar: **el símbolo
de cada moneda pasa a ser el propio de cada país/región, o la
abreviatura más corta que exista de verdad** ("$", no "COL$") — en vez
del prefijo desambiguado a propósito que tenía la primera versión.
Se revierte esa decisión de diseño anterior: ahora varias monedas
comparten el signo "$" tal cual se usa en cada país (COP, MXN, ARS,
CLP, UYU, CUP, CAD, AUD y el propio USD), igual que en la vida real —
quien vea "$50.00" sabe la moneda por el contexto de la tienda que está
viendo, no por el precio en sí. El código ISO 4217 (ya agregado en la
adenda anterior) sigue siendo la referencia sin ambigüedad, pero vive
en el selector de `/vendedor/perfil` y en el detalle de `/admin`, no en
el precio del producto.
"""
from __future__ import annotations

from decimal import Decimal

# Conjunto cerrado de monedas ofrecidas — mismo criterio que
# `badges_producto_service.BADGES_PRODUCTO`/`estados_stock_service.ESTADOS_STOCK`:
# el vendedor elige entre opciones curadas desde un <select>, no texto
# libre. Cada entrada trae:
#   - `nombre`: nombre de la moneda en español.
#   - `simbolo`: usado por `formatear_precio()` — el símbolo real o la
#     abreviatura más corta que usa cada país/región (decisión de Jose,
#     2026-08-31: preferible a un prefijo desambiguado inventado, ver
#     la "Segunda adenda" arriba). Varias monedas comparten el signo
#     "$" a propósito (COP, MXN, ARS, CLP, UYU, CUP, CAD, AUD, USD) —
#     es exactamente como se ve un precio en cada uno de esos países.
#     El código ISO 4217 (`codigo`, abajo) es lo que desambigua sin
#     ninguna duda cuando hace falta.
#   - `bandera`: emoji de bandera para el selector — la del país de
#     origen de la moneda; para el euro se usa la bandera de la Unión
#     Europea (🇪🇺) por ser una moneda compartida entre varios países.
#   - `codigo`: código ISO 4217 en mayúscula (coincide con la propia
#     clave del diccionario, guardado aparte para no repetir
#     `clave.upper()` en cada plantilla).
MONEDAS: dict[str, dict[str, str]] = {
    "usd": {"nombre": "Dólar estadounidense", "simbolo": "$", "bandera": "🇺🇸", "codigo": "USD"},
    "eur": {"nombre": "Euro", "simbolo": "€", "bandera": "🇪🇺", "codigo": "EUR"},
    "ves": {"nombre": "Bolívar venezolano", "simbolo": "Bs.", "bandera": "🇻🇪", "codigo": "VES"},
    "cop": {"nombre": "Peso colombiano", "simbolo": "$", "bandera": "🇨🇴", "codigo": "COP"},
    "mxn": {"nombre": "Peso mexicano", "simbolo": "$", "bandera": "🇲🇽", "codigo": "MXN"},
    "pen": {"nombre": "Sol peruano", "simbolo": "S/", "bandera": "🇵🇪", "codigo": "PEN"},
    "ars": {"nombre": "Peso argentino", "simbolo": "$", "bandera": "🇦🇷", "codigo": "ARS"},
    "brl": {"nombre": "Real brasileño", "simbolo": "R$", "bandera": "🇧🇷", "codigo": "BRL"},
    "clp": {"nombre": "Peso chileno", "simbolo": "$", "bandera": "🇨🇱", "codigo": "CLP"},
    "gtq": {"nombre": "Quetzal guatemalteco", "simbolo": "Q", "bandera": "🇬🇹", "codigo": "GTQ"},
    "hnl": {"nombre": "Lempira hondureño", "simbolo": "L", "bandera": "🇭🇳", "codigo": "HNL"},
    "nio": {"nombre": "Córdoba nicaragüense", "simbolo": "C$", "bandera": "🇳🇮", "codigo": "NIO"},
    "crc": {"nombre": "Colón costarricense", "simbolo": "₡", "bandera": "🇨🇷", "codigo": "CRC"},
    "pab": {"nombre": "Balboa panameño", "simbolo": "B/.", "bandera": "🇵🇦", "codigo": "PAB"},
    "pyg": {"nombre": "Guaraní paraguayo", "simbolo": "₲", "bandera": "🇵🇾", "codigo": "PYG"},
    "uyu": {"nombre": "Peso uruguayo", "simbolo": "$", "bandera": "🇺🇾", "codigo": "UYU"},
    "bob": {"nombre": "Boliviano", "simbolo": "Bs", "bandera": "🇧🇴", "codigo": "BOB"},
    "dop": {"nombre": "Peso dominicano", "simbolo": "RD$", "bandera": "🇩🇴", "codigo": "DOP"},
    "cup": {"nombre": "Peso cubano", "simbolo": "$", "bandera": "🇨🇺", "codigo": "CUP"},
    "gbp": {"nombre": "Libra esterlina", "simbolo": "£", "bandera": "🇬🇧", "codigo": "GBP"},
    "cad": {"nombre": "Dólar canadiense", "simbolo": "$", "bandera": "🇨🇦", "codigo": "CAD"},
    "jpy": {"nombre": "Yen japonés", "simbolo": "¥", "bandera": "🇯🇵", "codigo": "JPY"},
    "cny": {"nombre": "Yuan chino", "simbolo": "¥", "bandera": "🇨🇳", "codigo": "CNY"},
    "inr": {"nombre": "Rupia india", "simbolo": "₹", "bandera": "🇮🇳", "codigo": "INR"},
    "aud": {"nombre": "Dólar australiano", "simbolo": "$", "bandera": "🇦🇺", "codigo": "AUD"},
    "chf": {"nombre": "Franco suizo", "simbolo": "CHF", "bandera": "🇨🇭", "codigo": "CHF"},
}

MONEDA_POR_DEFECTO = "usd"

# Prefijo de código de país del número de WhatsApp (solo dígitos, sin
# "+") -> moneda sugerida al registrarse (ver `detectar_moneda_por_whatsapp`).
#
# Cubre el código de llamada internacional (E.164) de cada país cuya
# moneda está en MONEDAS. Varios países comparten una misma moneda
# (ej. España/Alemania/Francia/Italia -> eur) — está bien, varias
# claves del diccionario pueden apuntar al mismo valor.
#
# Limitación conocida y documentada, no resuelta a propósito: el
# código de llamada +1 lo comparten EE. UU., Canadá y buena parte del
# Caribe (con prefijos de 3 dígitos adicionales, ej. República
# Dominicana +1-809/829/849) — por eso esos prefijos de 4 dígitos se
# listan ANTES que el "1" genérico (ver el orden de evaluación en
# `detectar_moneda_por_whatsapp`, que prueba primero los prefijos más
# largos). Un número dominicano con otro prefijo de área que no sea
# 809/829/849, o un número canadiense (indistinguible de EE. UU. solo
# por los dígitos), cae en el valor por defecto de "1" (usd) — mismo
# criterio que ya tenía la primera versión de esta función.
_PREFIJO_PAIS_A_MONEDA: dict[str, str] = {
    # Norteamérica
    "1": "usd",  # EE. UU. / Canadá (ver limitación arriba) — genérico, se evalúa de último
    "1809": "dop",  # República Dominicana
    "1829": "dop",
    "1849": "dop",
    # Sudamérica
    "58": "ves",  # Venezuela
    "57": "cop",  # Colombia
    "51": "pen",  # Perú
    "54": "ars",  # Argentina
    "55": "brl",  # Brasil
    "56": "clp",  # Chile
    "591": "bob",  # Bolivia
    "593": "usd",  # Ecuador (dolarizado desde 2000)
    "595": "pyg",  # Paraguay
    "598": "uyu",  # Uruguay
    # Centroamérica
    "502": "gtq",  # Guatemala
    "503": "usd",  # El Salvador (dolarizado desde 2001)
    "504": "hnl",  # Honduras
    "505": "nio",  # Nicaragua
    "506": "crc",  # Costa Rica
    "507": "pab",  # Panamá
    # Caribe
    "53": "cup",  # Cuba
    # México
    "52": "mxn",  # México
    # Europa
    "34": "eur",  # España
    "351": "eur",  # Portugal
    "33": "eur",  # Francia
    "49": "eur",  # Alemania
    "39": "eur",  # Italia
    "44": "gbp",  # Reino Unido
    "41": "chf",  # Suiza
    # Resto del mundo (mercados globales grandes)
    "86": "cny",  # China
    "91": "inr",  # India
    "81": "jpy",  # Japón
    "61": "aud",  # Australia
}

# Prefijos ordenados del más largo al más corto, calculado una sola
# vez al importar el módulo — así `detectar_moneda_por_whatsapp()`
# siempre prueba primero los prefijos más específicos (ej. "1809"
# antes que "1"), sin depender del orden de inserción del diccionario.
_PREFIJOS_ORDENADOS: list[str] = sorted(
    _PREFIJO_PAIS_A_MONEDA, key=len, reverse=True
)


def listar_monedas() -> list[dict[str, str]]:
    """Devuelve las monedas disponibles, con su clave incluida.

    Returns:
        Lista de dicts `{"clave", "nombre", "simbolo", "bandera", "codigo"}`,
        en el orden en que deben mostrarse las opciones en el `<select>`
        del perfil.
    """
    return [{"clave": clave, **datos} for clave, datos in MONEDAS.items()]


def obtener_moneda(clave: str | None) -> dict[str, str]:
    """Busca una moneda por su clave, con el dólar como respaldo.

    A diferencia de `estados_stock_service.obtener_estado_stock` (que
    puede devolver None), esta función siempre devuelve una moneda
    válida — no existe un "sin moneda" para una tienda, toda tienda
    cotiza en alguna.

    Args:
        clave: Clave de la moneda (ej. "cop"), o vacío/None/inválida.

    Returns:
        El dict de la moneda (con su propia `clave` incluida), o el del
        dólar estadounidense si `clave` está vacía o no corresponde a
        ninguna moneda disponible.
    """
    if clave and clave in MONEDAS:
        return {"clave": clave, **MONEDAS[clave]}
    return {"clave": MONEDA_POR_DEFECTO, **MONEDAS[MONEDA_POR_DEFECTO]}


def detectar_moneda_por_whatsapp(whatsapp_numero: str) -> str:
    """Sugiere una moneda a partir del código de país del número de WhatsApp.

    Se usa solo al registrarse (ver `vendor_service.registrar_vendor` /
    `registrar_vendor_google`) — un cambio posterior del WhatsApp en
    `/vendedor/perfil` NO vuelve a disparar esta detección, para no
    resetear en silencio una moneda que el vendedor ya eligió a mano.

    Prueba los prefijos de `_PREFIJO_PAIS_A_MONEDA` del más largo al
    más corto (`_PREFIJOS_ORDENADOS`), así un prefijo específico como
    "1809" (República Dominicana) gana sobre el genérico "1"
    (EE. UU./Canadá) cuando ambos podrían aplicar.

    Args:
        whatsapp_numero: Número tal como lo escribe el vendedor (código
            de país + número, solo dígitos, sin "+").

    Returns:
        Clave de la moneda sugerida, o `MONEDA_POR_DEFECTO` ("usd") si
        el número no arranca con ninguno de los prefijos mapeados.
    """
    numero = (whatsapp_numero or "").strip()
    for prefijo in _PREFIJOS_ORDENADOS:
        if numero.startswith(prefijo):
            return _PREFIJO_PAIS_A_MONEDA[prefijo]
    return MONEDA_POR_DEFECTO


def formatear_precio(precio: Decimal, moneda: str | None) -> str:
    """Formatea un precio con el símbolo de la moneda de la tienda.

    Punto único de formato usado tanto en la tienda pública (las 3
    plantillas) como en el panel del vendedor (lista de productos,
    formulario de producto) — para que un cambio de símbolo o de
    cantidad de decimales se aplique en todos lados a la vez.

    Args:
        precio: Precio del producto, tal como está guardado (sin
            conversión de moneda — ver el docstring del módulo).
        moneda: Clave de la moneda de la tienda (`Vendor.moneda`), o
            None/inválida (cae en dólar).

    Returns:
        Cadena lista para mostrar, ej. "US$25.00", "Bs.150.00", con 2
        decimales siempre.
    """
    datos = obtener_moneda(moneda)
    return f"{datos['simbolo']}{precio:.2f}"
