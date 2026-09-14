/**
 * Comportamiento del correo en el login (2026-09-14, segunda ronda — en
 * paralelo a registro_vendedor.js):
 *
 *   - "Continuar con Google" se apaga apenas se EMPIEZA a escribir el
 *     correo a mano (no hace falta que esté completo ni bien escrito
 *     todavía): no tiene sentido ofrecer las dos vías de acceso a la vez
 *     una vez que el vendedor ya eligió la manual. Se reactiva solo si
 *     borra el correo.
 *
 *     Acá "Continuar con Google" es un <a> normal (ver _boton_google.html),
 *     no un <button> dentro de un <form> compartido como en el registro —
 *     un enlace no tiene un atributo `disabled` nativo, así que se simula
 *     con la clase `.admin-btn--deshabilitado` (ver style.css) + bloqueando
 *     el clic mientras esté puesta.
 *
 *   - El campo de "Contraseña" queda oculto (misma transición suave de
 *     `.admin-form__grupo-oculto`, ver style.css) hasta que el correo esté
 *     bien escrito de verdad — no basta con que no esté vacío, se exige
 *     el formato de un correo válido. Se aprovecha gratis la validación
 *     nativa del `<input type="email" required>` vía `checkValidity()`,
 *     sin reinventar una expresión regular (pedido de Jose: no revelar la
 *     contraseña mientras todavía se está escribiendo la dirección).
 */
document.addEventListener("DOMContentLoaded", () => {
    const email = document.getElementById("email");
    if (!email) {
        return;
    }

    const botonGoogle = document.getElementById("boton-continuar-google");
    const grupoPassword = document.getElementById("grupo-password");

    function actualizar() {
        const hayCorreo = email.value.trim() !== "";
        const correoValido = hayCorreo && email.checkValidity();

        if (botonGoogle) {
            botonGoogle.classList.toggle("admin-btn--deshabilitado", hayCorreo);
            botonGoogle.setAttribute("aria-disabled", hayCorreo ? "true" : "false");
            botonGoogle.tabIndex = hayCorreo ? -1 : 0;
        }

        if (grupoPassword) {
            grupoPassword.classList.toggle("admin-form__grupo-oculto--visible", correoValido);
        }
    }

    if (botonGoogle) {
        botonGoogle.addEventListener("click", (evento) => {
            if (botonGoogle.getAttribute("aria-disabled") === "true") {
                evento.preventDefault();
            }
        });
    }

    email.addEventListener("input", actualizar);
    actualizar();
});
