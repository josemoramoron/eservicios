/**
 * Círculos de color rápido para "Color de tu tienda" en /vendedor/perfil.
 *
 * Al hacer clic en un círculo, escribe ese color en el input
 * `#color_acento` — un <input type="color"> visible con e-link Plus
 * (el selector nativo sigue disponible aparte, para cualquier hex que
 * no esté en la paleta), o un <input type="hidden"> con el plan
 * gratis, que solo estos círculos pueden cambiar (ver
 * vendor_service.PALETA_ACENTO_GRATIS: azul y rosado). Sin
 * dependencias, mismo espíritu que validacion_formulario.js y
 * producto_fotos.js.
 */
document.addEventListener("DOMContentLoaded", () => {
    const circulos = document.querySelectorAll(".admin-paleta-acento__circulo");
    const inputColor = document.getElementById("color_acento");

    if (!circulos.length || !inputColor) {
        return;
    }

    circulos.forEach((circulo) => {
        circulo.addEventListener("click", () => {
            inputColor.value = circulo.dataset.color;
            circulos.forEach((otro) => otro.classList.remove("admin-paleta-acento__circulo--activo"));
            circulo.classList.add("admin-paleta-acento__circulo--activo");
        });
    });

    // Si el vendedor cambia el color a mano con el selector nativo, ningún
    // círculo debería seguir marcado como "activo" salvo que coincida.
    inputColor.addEventListener("input", () => {
        circulos.forEach((circulo) => {
            circulo.classList.toggle(
                "admin-paleta-acento__circulo--activo",
                circulo.dataset.color.toLowerCase() === inputColor.value.toLowerCase()
            );
        });
    });
});
