/**
 * Modal de detalle de producto en la tienda pública de un vendedor.
 *
 * Cada tarjeta de producto trae sus datos en atributos `data-*` (ya
 * escapados por Jinja al renderizar), este script solo los copia al
 * modal y lo muestra/oculta. Sin dependencias.
 */
document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("tienda-modal");
    if (!modal) {
        return;
    }

    const foto = document.getElementById("tienda-modal-foto");
    const titulo = document.getElementById("tienda-modal-titulo");
    const precio = document.getElementById("tienda-modal-precio");
    const descripcion = document.getElementById("tienda-modal-descripcion");
    const botonWhatsapp = document.getElementById("tienda-modal-wa");

    function abrirModal(tarjeta) {
        titulo.textContent = tarjeta.dataset.titulo;
        precio.textContent = tarjeta.dataset.precio;
        descripcion.textContent = tarjeta.dataset.descripcion;
        botonWhatsapp.href = tarjeta.dataset.wa;

        if (tarjeta.dataset.foto) {
            foto.style.backgroundImage = `url('${tarjeta.dataset.foto}')`;
        } else {
            foto.style.backgroundImage = "";
        }

        modal.hidden = false;
    }

    function cerrarModal() {
        modal.hidden = true;
    }

    document.querySelectorAll(".tienda-card").forEach((tarjeta) => {
        tarjeta.addEventListener("click", () => abrirModal(tarjeta));
    });

    modal.querySelectorAll("[data-cerrar]").forEach((el) => {
        el.addEventListener("click", cerrarModal);
    });

    document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && !modal.hidden) {
            cerrarModal();
        }
    });
});
