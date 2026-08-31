/**
 * Filtro de categorías de la tienda pública (punto 18 del roadmap, e-link Plus).
 *
 * Puramente del lado del cliente, sin recargar la página. Cada pastilla
 * trae la categoría a filtrar en `data-categoria-pill` (vacío = "Todas"),
 * y cada tarjeta de producto ya trae la suya en `data-categoria` (ver
 * `_filtro_categorias.html` y las 3 plantillas de tienda pública) —
 * este script solo compara y muestra/oculta con el atributo `hidden`.
 */
document.addEventListener("DOMContentLoaded", () => {
    const grupo = document.querySelector("[data-categoria-filtro-grupo]");
    if (!grupo) {
        return;
    }

    const pills = grupo.querySelectorAll("[data-categoria-pill]");
    const tarjetas = document.querySelectorAll(".tienda-card");

    pills.forEach((pill) => {
        pill.addEventListener("click", () => {
            const categoriaElegida = pill.dataset.categoriaPill || "";

            pills.forEach((p) => p.classList.remove("tienda-categorias__pill--activa"));
            pill.classList.add("tienda-categorias__pill--activa");

            tarjetas.forEach((tarjeta) => {
                tarjeta.hidden = Boolean(categoriaElegida) && tarjeta.dataset.categoria !== categoriaElegida;
            });
        });
    });
});
