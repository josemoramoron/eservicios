/**
 * Reordenar/quitar fotos existentes en el formulario de producto del panel de vendedor.
 *
 * Dos formas de reordenar a propósito: arrastrar (`draggable`, cómodo
 * en escritorio) y botones ‹ › (funcionan igual en escritorio y en
 * celular — el drag-and-drop nativo de HTML5 no dispara en touch, así
 * que los botones son la vía garantizada para el vendedor en el
 * celular). Ambas vías terminan sincronizando los mismos dos inputs
 * hidden que lee el servidor: `orden_fotos` (ids en el orden final,
 * separados por coma) y `fotos_a_quitar` (ids marcados para borrar).
 */
(function () {
    "use strict";

    const lista = document.getElementById("fotos-actuales-lista");
    if (!lista) return;

    const inputOrden = document.getElementById("orden_fotos");
    const inputQuitar = document.getElementById("fotos_a_quitar");

    let idsAQuitar = [];

    function itemsVisibles() {
        return Array.from(lista.querySelectorAll(".fotos-actuales-lista__item"));
    }

    function sincronizar() {
        const items = itemsVisibles();
        inputOrden.value = items.map((li) => li.dataset.fotoId).join(",");
        inputQuitar.value = idsAQuitar.join(",");

        items.forEach((li, indice) => {
            li.classList.toggle("fotos-actuales-lista__item--portada", indice === 0);
        });
    }

    function moverItem(li, direccion) {
        if (direccion === "arriba") {
            const anterior = li.previousElementSibling;
            if (anterior) lista.insertBefore(li, anterior);
        } else {
            const siguiente = li.nextElementSibling;
            if (siguiente) lista.insertBefore(siguiente, li);
        }
        sincronizar();
    }

    function quitarItem(li) {
        idsAQuitar.push(li.dataset.fotoId);
        li.remove();
        sincronizar();
    }

    lista.addEventListener("click", function (evento) {
        const botonMover = evento.target.closest(".fotos-actuales-lista__mover");
        if (botonMover) {
            const li = botonMover.closest(".fotos-actuales-lista__item");
            moverItem(li, botonMover.dataset.direccion);
            return;
        }
        const botonQuitar = evento.target.closest(".fotos-actuales-lista__quitar");
        if (botonQuitar) {
            const li = botonQuitar.closest(".fotos-actuales-lista__item");
            quitarItem(li);
        }
    });

    // --- Drag-and-drop nativo (desktop) ---
    let arrastrando = null;

    lista.addEventListener("dragstart", function (evento) {
        const li = evento.target.closest(".fotos-actuales-lista__item");
        if (!li) return;
        arrastrando = li;
        li.classList.add("fotos-actuales-lista__item--arrastrando");
        evento.dataTransfer.effectAllowed = "move";
    });

    lista.addEventListener("dragend", function () {
        if (arrastrando) arrastrando.classList.remove("fotos-actuales-lista__item--arrastrando");
        arrastrando = null;
        sincronizar();
    });

    lista.addEventListener("dragover", function (evento) {
        evento.preventDefault();
        const objetivo = evento.target.closest(".fotos-actuales-lista__item");
        if (!objetivo || objetivo === arrastrando || !arrastrando) return;
        const rect = objetivo.getBoundingClientRect();
        const mitad = rect.top + rect.height / 2;
        if (evento.clientY < mitad) {
            lista.insertBefore(arrastrando, objetivo);
        } else {
            lista.insertBefore(arrastrando, objetivo.nextElementSibling);
        }
    });

    sincronizar();
})();
