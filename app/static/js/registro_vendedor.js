/**
 * Chequeo en vivo de disponibilidad del subdominio en el registro de vendedor.
 *
 * Debounce simple: espera a que el usuario deje de escribir 400ms antes
 * de consultar `/vendedor/registro/verificar-slug`. Sin dependencias.
 */
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("slug");
    const estado = document.getElementById("slug-estado");
    if (!input || !estado) {
        return;
    }

    let temporizador = null;

    input.addEventListener("input", () => {
        const slug = input.value.trim().toLowerCase();
        window.clearTimeout(temporizador);

        if (!slug) {
            estado.textContent = "";
            return;
        }

        estado.textContent = "Verificando disponibilidad...";
        estado.style.color = "var(--color-text-muted)";

        temporizador = window.setTimeout(() => {
            fetch(`/vendedor/registro/verificar-slug?slug=${encodeURIComponent(slug)}`)
                .then((respuesta) => respuesta.json())
                .then((datos) => {
                    if (input.value.trim().toLowerCase() !== slug) {
                        return; // el usuario ya siguió escribiendo, esta respuesta quedó vieja
                    }
                    if (datos.disponible) {
                        estado.textContent = `¡Disponible! Tu tienda será ${slug}.eservicios.org`;
                        estado.style.color = "var(--color-whatsapp)";
                    } else {
                        estado.textContent = datos.error || "Ese subdominio no está disponible.";
                        estado.style.color = "#dc2626";
                    }
                })
                .catch(() => {
                    estado.textContent = "";
                });
        }, 400);
    });
});

/**
 * Paso de "correo" del registro (2026-09-14, reordenado al estilo
 * Linktree: correo manual primero, "Continuar con Google" debajo — ver
 * registro.html). Cosas que dependen del correo que se va escribiendo a
 * mano:
 *
 *   - El botón "Continuar con Google" se apaga (gris, deshabilitado) apenas
 *     se EMPIEZA a escribir el correo, no hace falta que esté completo:
 *     no tiene sentido ofrecer las dos vías de registro a la vez una vez
 *     que ya se está escribiendo el correo a mano. Si el vendedor borra
 *     el correo, se vuelve a habilitar solo.
 *   - Los campos de contraseña se revelan con una transición suave (la
 *     clase `--visible`, ver style.css) recién cuando el correo está BIEN
 *     escrito (formato válido, no solo "no vacío") — mismo criterio que
 *     el login, ver login_vendedor.js — para no revelar la contraseña
 *     mientras el vendedor todavía está a mitad de escribir la dirección.
 *   - El botón final "Crear mi tienda" queda deshabilitado hasta que el
 *     correo manual esté bien escrito Y se aceptaron los términos — la
 *     vía de Google no pasa por este botón (tiene su propio envío, ver
 *     _boton_google.html), así que no depende de él.
 */
document.addEventListener("DOMContentLoaded", () => {
    const email = document.getElementById("email");
    const grupoPassword = document.getElementById("grupo-password");
    if (!email || !grupoPassword) {
        return;
    }

    const botonGoogle = document.getElementById("boton-continuar-google");
    const terminos = document.getElementById("acepta_terminos");
    const botonCrear = document.getElementById("boton-crear-tienda");

    function actualizarBotonCrear(correoValido) {
        if (!botonCrear) {
            return;
        }
        const aceptaTerminos = !terminos || terminos.checked;
        botonCrear.disabled = !(correoValido && aceptaTerminos);
    }

    function actualizarPasoCorreo() {
        const hayCorreo = email.value.trim() !== "";
        const correoValido = hayCorreo && email.checkValidity();

        grupoPassword.classList.toggle("admin-form__grupo-oculto--visible", correoValido);

        if (botonGoogle) {
            botonGoogle.disabled = hayCorreo;
        }

        actualizarBotonCrear(correoValido);
    }

    email.addEventListener("input", actualizarPasoCorreo);
    if (terminos) {
        terminos.addEventListener("change", () => {
            const hayCorreo = email.value.trim() !== "";
            actualizarBotonCrear(hayCorreo && email.checkValidity());
        });
    }
    actualizarPasoCorreo();
});
