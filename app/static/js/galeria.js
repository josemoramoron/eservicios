/**
 * Lightbox de la galería de fotos en la ficha de detalle de producto
 * (`producto/detalle.html`). Vanilla JS, sin dependencias — mismo estilo
 * que `tienda.js` (modal de producto de la tienda de vendedor).
 *
 * Espera en el DOM:
 *   - `window.__galeriaFotos`: array de URLs (1 o más).
 *   - `[data-galeria-abrir]`: botón de la foto principal, abre el lightbox.
 *   - `[data-galeria-miniatura]` con `data-indice`: miniaturas, cambian la
 *     foto principal Y abren el lightbox en esa foto.
 *   - `#lightbox`, `#lightbox-img`, `[data-lightbox-cerrar]`,
 *     `[data-lightbox-prev]`, `[data-lightbox-next]`.
 */
(function () {
    "use strict";

    const fotos = window.__galeriaFotos || [];
    if (!fotos.length) return;

    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightbox-img");
    if (!lightbox || !lightboxImg) return;

    let indiceActual = 0;

    function mostrarEnLightbox(indice) {
        indiceActual = (indice + fotos.length) % fotos.length;
        lightboxImg.src = fotos[indiceActual];
        lightbox.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function cerrarLightbox() {
        lightbox.hidden = true;
        document.body.style.overflow = "";
    }

    function mostrarPrincipal(indice) {
        const principal = document.querySelector("[data-galeria-principal]");
        if (principal) principal.src = fotos[indice];
        document.querySelectorAll("[data-galeria-miniatura]").forEach((miniatura) => {
            miniatura.classList.toggle(
                "producto-detail__miniatura--activa",
                Number(miniatura.dataset.indice) === indice
            );
        });
    }

    const botonAbrir = document.querySelector("[data-galeria-abrir]");
    if (botonAbrir) {
        botonAbrir.addEventListener("click", () => {
            mostrarEnLightbox(Number(botonAbrir.dataset.indice) || 0);
        });
    }

    document.querySelectorAll("[data-galeria-miniatura]").forEach((miniatura) => {
        miniatura.addEventListener("click", () => {
            const indice = Number(miniatura.dataset.indice);
            mostrarPrincipal(indice);
        });
    });

    document.querySelectorAll("[data-lightbox-cerrar]").forEach((el) => {
        el.addEventListener("click", cerrarLightbox);
    });

    const botonPrev = document.querySelector("[data-lightbox-prev]");
    const botonNext = document.querySelector("[data-lightbox-next]");
    if (botonPrev) botonPrev.addEventListener("click", () => mostrarEnLightbox(indiceActual - 1));
    if (botonNext) botonNext.addEventListener("click", () => mostrarEnLightbox(indiceActual + 1));

    document.addEventListener("keydown", (evento) => {
        if (lightbox.hidden) return;
        if (evento.key === "Escape") cerrarLightbox();
        if (evento.key === "ArrowLeft" && fotos.length > 1) mostrarEnLightbox(indiceActual - 1);
        if (evento.key === "ArrowRight" && fotos.length > 1) mostrarEnLightbox(indiceActual + 1);
    });
})();
