/**
 * Círculos de color rápido para "Color de acento propio" en /vendedor/perfil.
 *
 * Al hacer clic en un círculo, escribe ese color en el <input type="color">
 * nativo (el selector personalizado sigue disponible aparte, para
 * cualquier hex que no esté en la paleta) y desmarca el checkbox de
 * "quitar mi color" si estaba marcado, para que el color elegido no se
 * pierda al guardar. Sin dependencias, mismo espíritu que
 * validacion_formulario.js y producto_fotos.js.
 */
document.addEventListener("DOMContentLoaded", () => {
    const circulos = document.querySelectorAll(".admin-paleta-acento__circulo");
    const inputColor = document.getElementById("color_acento");
    const checkboxQuitar = document.querySelector('input[name="quitar_color_acento"]');

    if (!circulos.length || !inputColor) {
        return;
    }

    circulos.forEach((circulo) => {
        circulo.addEventListener("click", () => {
            inputColor.value = circulo.dataset.color;
            circulos.forEach((otro) => otro.classList.remove("admin-paleta-acento__circulo--activo"));
            circulo.classList.add("admin-paleta-acento__circulo--activo");
            if (checkboxQuitar) {
                checkboxQuitar.checked = false;
            }
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
