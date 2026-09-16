/**
 * Selector rápido de red social en "Nuevo enlace" (2026-09-15).
 *
 * Alterna entre 2 grupos de campos según qué ícono se elija en
 * `#redes-grid`: `#grupo-usuario-red` (un solo input "@usuario") para
 * una red reconocida, o `#grupo-clasico` (título + URL de siempre) para
 * "Otro enlace". También autocompleta el título del botón con el nombre
 * de la red elegida (ej. "Instagram"), mientras el vendedor no haya
 * escrito uno propio — a partir de ahí deja de tocarlo. Al elegir una red
 * reconocida (no "Otro enlace"), también hace scroll y foco automático al
 * campo de usuario (2026-09-16, pedido de Jose) — en móvil la grilla de
 * íconos lo empuja fuera de la vista.
 *
 * Solo se carga en la pantalla de "Nuevo enlace" (ver enlace_form.html,
 * `{% if not link %}`) — "Editar enlace" sigue con el formulario clásico
 * sin este script.
 */
(function () {
    "use strict";

    var grid = document.getElementById("redes-grid");
    var grupoUsuario = document.getElementById("grupo-usuario-red");
    var grupoClasico = document.getElementById("grupo-clasico");
    var etiquetaUsuario = document.getElementById("etiqueta-usuario-red");
    var campoTitulo = document.getElementById("titulo");
    var campoUrl = document.getElementById("url");
    if (!grid || !grupoUsuario || !grupoClasico || !campoTitulo || !campoUrl) {
        return;
    }

    var tituloTocado = campoTitulo.value.trim() !== "";
    campoTitulo.addEventListener("input", function () {
        tituloTocado = campoTitulo.value.trim() !== "";
    });

    function actualizar() {
        var marcado = grid.querySelector("input[name='red']:checked");
        var esOtro = !marcado || marcado.value === "otro";

        grupoUsuario.hidden = esOtro;
        grupoClasico.hidden = !esOtro;

        // El "required" de #titulo/#url hay que alternarlo a mano junto con
        // `hidden` (2026-09-16, bug reportado por Jose: "elijo TikTok, lleno
        // el usuario, y Guardar no hace nada"). Ocultar el CONTENEDOR con
        // `hidden` no exime a estos campos de la validación nativa del
        // navegador — comprobado en Chrome: con la red seleccionada, #url
        // seguía vacío y `required`, así que el botón "Guardar" quedaba
        // bloqueado por un campo que ni siquiera se ve, sin ningún aviso en
        // pantalla (por eso "no pasaba nada"). Al ponerlos `required` solo
        // cuando su grupo realmente está visible, el navegador únicamente
        // exige lo que la persona tiene delante.
        campoTitulo.required = esOtro;
        campoUrl.required = esOtro;

        var nombreRed = !esOtro && marcado ? marcado.getAttribute("data-nombre-red") || "" : "";
        if (etiquetaUsuario) {
            etiquetaUsuario.textContent = nombreRed ? "Tu usuario en " + nombreRed : "Tu usuario";
        }
        if (!tituloTocado) {
            campoTitulo.value = nombreRed;
        }
    }

    var campoUsuario = document.getElementById("usuario");

    grid.querySelectorAll("input[name='red']").forEach(function (input) {
        input.addEventListener("change", function () {
            actualizar();
            // Ancla al input de usuario cada vez que se elige una red
            // (2026-09-16, pedido de Jose): en móvil la grilla de íconos
            // empuja el campo fuera de la vista, y a mucha gente no se le
            // ocurre bajar a buscarlo. No se hace en la carga inicial (solo
            // dentro de este listener de "change"), para no robarle el foco
            // a nadie que todavía no tocó nada.
            if (input.value !== "otro" && campoUsuario) {
                campoUsuario.scrollIntoView({ behavior: "smooth", block: "center" });
                // El foco se retrasa un poco para no pelear con la animación
                // del scroll (en iOS, enfocar de inmediato puede abrir el
                // teclado y saltar la posición antes de que termine).
                window.setTimeout(function () {
                    campoUsuario.focus();
                }, 300);
            }
        });
    });
    actualizar();
})();
