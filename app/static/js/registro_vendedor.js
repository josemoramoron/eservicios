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
