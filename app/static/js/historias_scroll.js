/*
 * historias_scroll.js — cualquier fila horizontal marcada con
 * [data-historias-scroll]: la fila combinada de "historias" (categorías +
 * enlaces) de "Feed continuo", y la fila de enlaces circulares compartida
 * por Clásica/Editorial/Portada/Tablero (ver _enlaces_circulares.html).
 * Genérico a propósito (2026-09-30, pedido de Jose de unificar el
 * comportamiento en todas las plantillas con enlaces circulares, menos
 * Píldoras) — no asume ninguna clase CSS específica, solo el atributo.
 *
 * Pedido de Jose: cuando la fila no cabe en pantalla, debe combinar dos
 * comportamientos a la vez —
 *   1) Auto-desplazamiento tipo "marquesina" (va y vuelve solo, despacio).
 *   2) Seguir siendo arrastrable/desplazable manualmente por el usuario.
 *
 * Sin dependencias nuevas (convención del proyecto). El auto-scroll usa
 * requestAnimationFrame con velocidad baja y rebota en los extremos
 * ("ping-pong") en vez de duplicar el contenido, porque los círculos son
 * interactivos (filtran categoría o abren un enlace) y duplicarlos
 * complicaría la accesibilidad sin aportar nada aquí. El arrastre manual
 * (mouse) y el toque (touch, nativo del navegador) pausan el
 * auto-desplazamiento de inmediato y lo reanudan tras un respiro corto de
 * inactividad. Si el usuario prefiere menos movimiento
 * (prefers-reduced-motion), el auto-desplazamiento no arranca — la fila
 * sigue siendo desplazable a mano igual.
 */
(function () {
    "use strict";

    var VELOCIDAD_PX_SEG = 26;
    var PAUSA_EXTREMOS_MS = 900;
    var REANUDAR_TRAS_INTERACCION_MS = 2500;
    var prefiereMenosMovimiento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function iniciar(fila) {
        var direccion = 1;
        var pausadoHasta = 0;
        var enPausaExtremo = false;
        var arrastrando = false;
        var arrastreInicioX = 0;
        var arrastreInicioScroll = 0;
        var seMovioDurante = false;
        var ultimoTs = null;

        function cabe() {
            return fila.scrollWidth - fila.clientWidth <= 1;
        }

        function marcarInteraccion() {
            pausadoHasta = Date.now() + REANUDAR_TRAS_INTERACCION_MS;
        }

        function paso(ts) {
            if (ultimoTs === null) ultimoTs = ts;
            var dt = (ts - ultimoTs) / 1000;
            ultimoTs = ts;

            var listoParaMover = !arrastrando && !enPausaExtremo && Date.now() >= pausadoHasta && !cabe();

            if (listoParaMover) {
                var maximo = fila.scrollWidth - fila.clientWidth;
                var nuevo = fila.scrollLeft + direccion * VELOCIDAD_PX_SEG * dt;

                if (nuevo >= maximo) {
                    nuevo = maximo;
                    direccion = -1;
                    enPausaExtremo = true;
                    setTimeout(function () { enPausaExtremo = false; }, PAUSA_EXTREMOS_MS);
                } else if (nuevo <= 0) {
                    nuevo = 0;
                    direccion = 1;
                    enPausaExtremo = true;
                    setTimeout(function () { enPausaExtremo = false; }, PAUSA_EXTREMOS_MS);
                }

                fila.scrollLeft = nuevo;
            }

            requestAnimationFrame(paso);
        }

        // Arrastre manual con mouse (el toque ya funciona nativo vía
        // overflow-x:auto; esto agrega la misma comodidad con puntero).
        fila.addEventListener("pointerdown", function (evento) {
            if (evento.pointerType === "touch") return; // el touch nativo ya desplaza
            arrastrando = true;
            seMovioDurante = false;
            arrastreInicioX = evento.clientX;
            arrastreInicioScroll = fila.scrollLeft;
            fila.setPointerCapture(evento.pointerId);
            fila.classList.add("is-arrastrando");
        });

        fila.addEventListener("pointermove", function (evento) {
            if (!arrastrando) return;
            var delta = evento.clientX - arrastreInicioX;
            if (Math.abs(delta) > 3) seMovioDurante = true;
            fila.scrollLeft = arrastreInicioScroll - delta;
        });

        function soltar(evento) {
            if (!arrastrando) return;
            arrastrando = false;
            fila.classList.remove("is-arrastrando");
            marcarInteraccion();
            // Si hubo arrastre real, evita que el click posterior dispare
            // el filtro de categoría o el enlace por accidente.
            if (seMovioDurante) {
                var bloquear = function (e) { e.preventDefault(); e.stopPropagation(); };
                fila.addEventListener("click", bloquear, { capture: true, once: true });
            }
        }

        fila.addEventListener("pointerup", soltar);
        fila.addEventListener("pointercancel", soltar);
        fila.addEventListener("pointerleave", function () { if (arrastrando) soltar(); });

        // Cualquier scroll manual (touch, rueda, teclado) también pausa
        // el auto-desplazamiento un momento.
        fila.addEventListener("scroll", function () {
            if (!arrastrando) marcarInteraccion();
        }, { passive: true });

        if (!prefiereMenosMovimiento) {
            requestAnimationFrame(paso);
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-historias-scroll]").forEach(iniciar);
    });
})();
