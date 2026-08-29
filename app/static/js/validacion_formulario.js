/**
 * Motor genérico de avisos y sugerencias para los formularios del panel
 * de vendedor. No reemplaza la validación del backend (esa sigue siendo
 * la única que de verdad decide si algo se guarda) — esto es solo para
 * dar una respuesta inmediata en pantalla, sin lógica particular por
 * formulario, para poder reusarlo en registro, perfil, productos y
 * enlaces con los mismos atributos `data-*`:
 *
 *   data-contador           → en un input/textarea con `maxlength`, agrega
 *                             un contador "N de M caracteres" que se
 *                             actualiza al escribir y se pone en rojo cerca
 *                             del límite.
 *   data-formato="url"      → en un input, avisa si el valor no parece una
 *                             URL válida (al perder el foco).
 *   data-formato="whatsapp" → en un input, avisa si el valor no son solo
 *                             dígitos con el código de país (al perder el foco).
 *   data-coincide-con="id"  → en un input, avisa si su valor no coincide
 *                             con el del input indicado (ej. confirmar
 *                             contraseña) — se revisa al escribir en
 *                             cualquiera de los dos campos.
 *
 * Los mensajes se pintan como `<p class="admin-form__error">` justo
 * después del campo, y el campo recibe `admin-form__input--error` (o
 * `admin-form__textarea--error`) mientras el aviso esté activo — son
 * solo una sugerencia visual, nunca bloquean el envío del formulario.
 */
(function () {
    "use strict";

    function claseError(campo) {
        return campo.tagName === "TEXTAREA" ? "admin-form__textarea--error" : "admin-form__input--error";
    }

    function crearElementoError(campo) {
        var error = document.createElement("p");
        error.className = "admin-form__error";
        error.hidden = true;
        campo.insertAdjacentElement("afterend", error);
        return error;
    }

    function mostrarError(campo, error, mensaje) {
        campo.classList.add(claseError(campo));
        error.textContent = mensaje;
        error.hidden = false;
    }

    function ocultarError(campo, error) {
        campo.classList.remove(claseError(campo));
        error.hidden = true;
    }

    function iniciarContador(campo) {
        var max = parseInt(campo.getAttribute("maxlength"), 10);
        if (!max) {
            return;
        }
        var contador = document.createElement("p");
        contador.className = "admin-form__contador";
        campo.insertAdjacentElement("afterend", contador);

        function actualizar() {
            var restante = max - campo.value.length;
            contador.textContent = campo.value.length + " de " + max + " caracteres";
            contador.classList.toggle("admin-form__contador--limite", restante <= 10);
        }

        campo.addEventListener("input", actualizar);
        actualizar();
    }

    function pareceUrlValida(valor) {
        if (!valor) {
            return true;
        }
        try {
            var url = new URL(valor);
            return url.protocol === "http:" || url.protocol === "https:";
        } catch (err) {
            return false;
        }
    }

    function iniciarFormato(campo) {
        var formato = campo.getAttribute("data-formato");
        var error = crearElementoError(campo);

        campo.addEventListener("blur", function () {
            var valor = campo.value.trim();
            var valido = true;
            var mensaje = "";
            if (formato === "url") {
                valido = pareceUrlValida(valor);
                mensaje = "Esa URL no parece válida — recuerda incluir https://";
            } else if (formato === "whatsapp") {
                valido = valor === "" || /^\d{8,15}$/.test(valor);
                mensaje = "Escribe solo dígitos, con el código de país (ej. 584121234567).";
            }
            if (valido) {
                ocultarError(campo, error);
            } else {
                mostrarError(campo, error, mensaje);
            }
        });
    }

    function iniciarCoincidencia(campo) {
        var otroId = campo.getAttribute("data-coincide-con");
        var otroCampo = document.getElementById(otroId);
        if (!otroCampo) {
            return;
        }
        var error = crearElementoError(campo);

        function revisar() {
            if (!campo.value || !otroCampo.value) {
                ocultarError(campo, error);
                return;
            }
            if (campo.value === otroCampo.value) {
                ocultarError(campo, error);
            } else {
                mostrarError(campo, error, "No coincide con el campo anterior.");
            }
        }

        campo.addEventListener("input", revisar);
        otroCampo.addEventListener("input", revisar);
    }

    document.querySelectorAll("[data-contador]").forEach(iniciarContador);
    document.querySelectorAll("[data-formato]").forEach(iniciarFormato);
    document.querySelectorAll("[data-coincide-con]").forEach(iniciarCoincidencia);
})();
