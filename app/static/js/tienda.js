/**
 * Modal de detalle de producto en la tienda pública de un vendedor.
 *
 * Cada tarjeta de producto trae sus datos en atributos `data-*` (ya
 * escapados por Jinja al renderizar), este script solo los copia al
 * modal y lo muestra/oculta. Si el producto tiene más de una foto
 * (`data-fotos`, un array JSON), pinta una fila de miniaturas debajo de
 * la foto principal para poder cambiarla sin cerrar el modal. Sin
 * dependencias.
 */
document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("tienda-modal");
    if (!modal) {
        return;
    }

    const foto = document.getElementById("tienda-modal-foto");
    const miniaturas = document.getElementById("tienda-modal-miniaturas");
    const titulo = document.getElementById("tienda-modal-titulo");
    const precio = document.getElementById("tienda-modal-precio");
    const descripcion = document.getElementById("tienda-modal-descripcion");
    const botonWhatsapp = document.getElementById("tienda-modal-wa");

    function mostrarFotoPrincipal(url) {
        foto.style.backgroundImage = url ? `url('${url}')` : "";
    }

    function pintarMiniaturas(fotos) {
        miniaturas.innerHTML = "";
        if (fotos.length < 2) {
            return;
        }
        fotos.forEach((url, indice) => {
            const miniatura = document.createElement("button");
            miniatura.type = "button";
            miniatura.className =
                "tienda-modal__miniatura" + (indice === 0 ? " tienda-modal__miniatura--activa" : "");
            miniatura.style.backgroundImage = `url('${url}')`;
            miniatura.addEventListener("click", () => {
                mostrarFotoPrincipal(url);
                miniaturas.querySelectorAll(".tienda-modal__miniatura").forEach((el) => {
                    el.classList.remove("tienda-modal__miniatura--activa");
                });
                miniatura.classList.add("tienda-modal__miniatura--activa");
            });
            miniaturas.appendChild(miniatura);
        });
    }

    function abrirModal(tarjeta) {
        titulo.textContent = tarjeta.dataset.titulo;
        precio.textContent = tarjeta.dataset.precio;
        descripcion.textContent = tarjeta.dataset.descripcion;
        botonWhatsapp.href = tarjeta.dataset.wa;

        let fotos = [];
        try {
            fotos = JSON.parse(tarjeta.dataset.fotos || "[]");
        } catch (error) {
            fotos = [];
        }

        mostrarFotoPrincipal(fotos[0] || "");
        pintarMiniaturas(fotos);

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
