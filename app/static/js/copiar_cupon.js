/**
 * Copia el código de un cupón al portapapeles al tocar el marco que lo
 * muestra en la tienda pública (ver Vendor.cupon / resolver_cupon_vendor,
 * punto 16 del roadmap). No calcula ningún descuento — solo copia el
 * texto tal cual el vendedor lo escribió, para que el cliente lo pegue
 * donde quiera (típicamente en el mensaje de WhatsApp).
 *
 * Mismo criterio que compartir.js: Clipboard API cuando está disponible,
 * con un window.prompt como respaldo para navegadores sin soporte.
 *
 * Atributos que lee de cada botón [data-cupon-copiar]:
 *   data-codigo → Texto exacto a copiar (si falta, usa el propio texto del botón).
 */
(function () {
    "use strict";

    function avisarCopiado(boton) {
        if (!boton.dataset.textoOriginal) {
            boton.dataset.textoOriginal = boton.textContent.trim();
        }
        var original = boton.dataset.textoOriginal;
        boton.textContent = "¡Copiado!";
        boton.classList.add("tienda-cupon__codigo--copiado");
        setTimeout(function () {
            boton.textContent = original;
            boton.classList.remove("tienda-cupon__codigo--copiado");
        }, 1800);
    }

    document.querySelectorAll("[data-cupon-copiar]").forEach(function (boton) {
        boton.addEventListener("click", function () {
            var codigo = boton.getAttribute("data-codigo") || boton.textContent.trim();
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard
                    .writeText(codigo)
                    .then(function () {
                        avisarCopiado(boton);
                    })
                    .catch(function () {
                        window.prompt("Copia este código:", codigo);
                    });
            } else {
                window.prompt("Copia este código:", codigo);
            }
        });
    });
})();
