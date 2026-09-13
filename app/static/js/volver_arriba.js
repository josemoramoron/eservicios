/**
 * Botón flotante "volver arriba" de la tienda pública (pedido de Jose,
 * 2026-09-13, junto con el scroll suave general del sitio).
 *
 * Aparece recién después de bajar un poco en la página (para no
 * estorbar arriba de todo, donde no hace falta) y, al pulsarlo, sube de
 * nuevo con scroll suave. Un solo botón compartido por las 4 plantillas
 * de tienda pública vía tienda/_pie_tienda.html — sin datos propios de
 * cada plantilla, así que no necesita ningún atributo `data-*` aparte
 * del que lo marca.
 */
document.addEventListener("DOMContentLoaded", () => {
    const boton = document.querySelector("[data-volver-arriba]");
    if (!boton) {
        return;
    }

    const UMBRAL_PX = 480;

    function actualizarVisibilidad() {
        boton.classList.toggle("tienda-volver-arriba--visible", window.scrollY > UMBRAL_PX);
    }

    boton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    window.addEventListener("scroll", actualizarVisibilidad, { passive: true });
    actualizarVisibilidad();
});
