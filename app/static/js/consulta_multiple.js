/**
 * Consulta de múltiples productos por WhatsApp (punto 19 del roadmap,
 * e-link Plus). Sin dependencias, mismo estilo que categoria_filtro.js.
 *
 * A propósito este script NUNCA arma el link de WhatsApp ni el texto del
 * mensaje — eso vive enteramente en el servidor
 * (vendor_service.construir_mensaje_consulta_multiple, invocado desde
 * clicks.click_whatsapp_multiple). Este script solo hace dos cosas:
 * llevar la cuenta de qué productos están marcados, y mantener el href
 * de la bandeja apuntando a
 * "{consulta_multiple_base_href}?productos=id1,id2,id3".
 *
 * Los checkboxes viven SIEMPRE fuera del <button> de la tarjeta (nunca
 * anidados dentro) — ver la nota en tienda.css sobre .tienda-card-wrap —
 * así que no hace falta detener la propagación de ningún evento: un
 * clic en el checkbox nunca dispara el modal de detalle del producto.
 */
document.addEventListener("DOMContentLoaded", function () {
    var casillas = document.querySelectorAll("[data-consulta-multiple-check]");
    var bandeja = document.getElementById("consulta-multiple-bandeja");
    if (!casillas.length || !bandeja) {
        return;
    }

    var enlace = document.getElementById("consulta-multiple-link");
    var contador = document.getElementById("consulta-multiple-contador");
    var botonLimpiar = document.getElementById("consulta-multiple-limpiar");
    var baseHref = bandeja.dataset.baseHref;
    var seleccionados = [];

    function actualizarBandeja() {
        if (seleccionados.length === 0) {
            bandeja.hidden = true;
            return;
        }
        bandeja.hidden = false;
        contador.textContent =
            seleccionados.length === 1
                ? "1 producto seleccionado"
                : seleccionados.length + " productos seleccionados";
        enlace.href = baseHref + "?productos=" + seleccionados.join(",");
    }

    casillas.forEach(function (casilla) {
        casilla.addEventListener("change", function () {
            var id = casilla.dataset.productoId;
            var indice = seleccionados.indexOf(id);
            if (casilla.checked && indice === -1) {
                seleccionados.push(id);
            } else if (!casilla.checked && indice !== -1) {
                seleccionados.splice(indice, 1);
            }
            actualizarBandeja();
        });
    });

    if (botonLimpiar) {
        botonLimpiar.addEventListener("click", function () {
            casillas.forEach(function (casilla) {
                casilla.checked = false;
            });
            seleccionados = [];
            actualizarBandeja();
        });
    }
});
