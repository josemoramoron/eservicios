/**
 * Filtro de categorías de la tienda pública (punto 18 del roadmap, e-link Plus).
 *
 * Puramente del lado del cliente, sin recargar la página. Cada pastilla
 * trae la categoría a filtrar en `data-categoria-pill` (vacío = "Todas"),
 * y cada tarjeta de producto ya trae la suya en `data-categoria` (ver
 * `_filtro_categorias.html` y las 4 plantillas de tienda pública) —
 * este script solo compara y muestra/oculta con el atributo `hidden`.
 *
 * Importante: el `hidden` se pone en `.tienda-card-wrap` (el contenedor),
 * no en `.tienda-card` (el <button> con la info del producto). El
 * checkbox de "consulta múltiple" (punto 19) vive como hermano del
 * <button>, fuera de él (ver consulta_multiple.js) — si solo se ocultaba
 * el <button>, ese checkbox quedaba flotando solo, sin su tarjeta, para
 * cualquier producto que el filtro escondiera (bug reportado por Jose,
 * corregido 2026-09-14).
 */
document.addEventListener("DOMContentLoaded", () => {
    const grupo = document.querySelector("[data-categoria-filtro-grupo]");
    if (!grupo) {
        return;
    }

    const pills = grupo.querySelectorAll("[data-categoria-pill]");
    const envoltorios = document.querySelectorAll(".tienda-card-wrap");

    pills.forEach((pill) => {
        pill.addEventListener("click", () => {
            const categoriaElegida = pill.dataset.categoriaPill || "";

            pills.forEach((p) => p.classList.remove("tienda-categorias__pill--activa"));
            pill.classList.add("tienda-categorias__pill--activa");

            envoltorios.forEach((envoltorio) => {
                const tarjeta = envoltorio.querySelector(".tienda-card");
                const categoria = tarjeta ? tarjeta.dataset.categoria : "";
                envoltorio.hidden = Boolean(categoriaElegida) && categoria !== categoriaElegida;
            });
        });
    });
});
