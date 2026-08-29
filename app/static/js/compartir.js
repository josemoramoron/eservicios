/**
 * Botón de "Compartir" genérico, reusable en la tienda pública y en el
 * panel de vendedor (dashboard). Usa la Web Share API nativa del
 * celular/navegador cuando está disponible (abre el selector de
 * WhatsApp/Instagram/etc. del sistema) y cae a "copiar el enlace al
 * portapapeles" cuando no está disponible (ej. escritorio) — sin
 * duplicar esta lógica en cada plantilla.
 *
 * Atributos que lee de cada botón `[data-compartir-btn]`:
 *   data-url    → URL a compartir (si falta, usa la URL actual de la página).
 *   data-titulo → Título a compartir (si falta, usa el <title> de la página).
 */
(function () {
    "use strict";

    function textoOriginal(boton) {
        if (!boton.dataset.textoOriginal) {
            boton.dataset.textoOriginal = boton.textContent.trim();
        }
        return boton.dataset.textoOriginal;
    }

    function avisarTemporal(boton, mensaje) {
        var original = textoOriginal(boton);
        boton.textContent = mensaje;
        setTimeout(function () {
            boton.textContent = original;
        }, 2000);
    }

    function copiarAlPortapapeles(url, boton) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard
                .writeText(url)
                .then(function () {
                    avisarTemporal(boton, "¡Enlace copiado!");
                })
                .catch(function () {
                    window.prompt("Copia este enlace:", url);
                });
        } else {
            window.prompt("Copia este enlace:", url);
        }
    }

    document.querySelectorAll("[data-compartir-btn]").forEach(function (boton) {
        textoOriginal(boton);
        boton.addEventListener("click", function () {
            var url = boton.getAttribute("data-url") || window.location.href;
            var titulo = boton.getAttribute("data-titulo") || document.title;

            if (navigator.share) {
                navigator.share({ title: titulo, url: url }).catch(function () {
                    // El usuario cerró el selector nativo sin elegir nada — no hace falta avisar.
                });
            } else {
                copiarAlPortapapeles(url, boton);
            }
        });
    });
})();
