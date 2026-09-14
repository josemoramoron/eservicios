/**
 * Recorte de imagen en el navegador antes de subirla — logo (1:1),
 * portada (3:1) y, opcionalmente, fotos de producto (libre, sin
 * proporción fija) — pedido de Jose, 2026-09-14. Usa Cropper.js
 * (cargado por CDN en cada plantilla que lo necesita, ver perfil.html
 * y producto_form.html). El archivo ya recortado reemplaza al original
 * dentro del mismo `<input type="file">`, así que el resto del flujo
 * de subida (`r2_service.subir_imagen`) no cambia en nada: sigue
 * recibiendo un único archivo por campo, ahora ya encuadrado.
 *
 * Un solo modal, creado una vez y reutilizado por todos los campos que
 * lo piden (logo, portada, cada foto de producto).
 */
(function () {
    "use strict";

    let modal = null;
    let cropper = null;
    let resolverActual = null;

    function crearModalSiHaceFalta() {
        if (modal) {
            return modal;
        }
        modal = document.createElement("div");
        modal.className = "recorte-modal";
        modal.innerHTML =
            '<div class="recorte-modal__caja">' +
            '<p class="recorte-modal__titulo"></p>' +
            '<div class="recorte-modal__lienzo"><img class="recorte-modal__img" alt=""></div>' +
            '<div class="recorte-modal__acciones">' +
            '<button type="button" class="admin-btn recorte-modal__cancelar">Elegir otra foto</button>' +
            '<button type="button" class="admin-btn admin-btn--primary recorte-modal__confirmar">Usar esta imagen</button>' +
            "</div></div>";
        document.body.appendChild(modal);
        modal.querySelector(".recorte-modal__cancelar").addEventListener("click", () => cerrarModal(false));
        modal.querySelector(".recorte-modal__confirmar").addEventListener("click", () => cerrarModal(true));
        return modal;
    }

    function cerrarModal(confirmado) {
        modal.classList.remove("recorte-modal--visible");
        const resolver = resolverActual;
        resolverActual = null;
        // Importante: llamar al resolver ANTES de destruir el cropper.
        // Cuando `confirmado` es true, el resolver todavía necesita leer
        // `cropper.getCroppedCanvas()` — destruirlo primero lo dejaría
        // en null y el recorte fallaría en silencio (bug real, detectado
        // al verificar con Playwright antes de entregar este cambio).
        if (resolver) {
            resolver(confirmado);
        }
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
    }

    function abrirModal(archivo, { aspectRatio, titulo }) {
        crearModalSiHaceFalta();
        modal.querySelector(".recorte-modal__titulo").textContent = titulo;
        const img = modal.querySelector(".recorte-modal__img");

        return new Promise((resolve) => {
            const lector = new FileReader();
            lector.onload = () => {
                img.src = lector.result;
                modal.classList.add("recorte-modal--visible");
                if (cropper) {
                    cropper.destroy();
                }
                cropper = new Cropper(img, {
                    aspectRatio: aspectRatio,
                    viewMode: 1,
                    background: false,
                    autoCropArea: 1,
                });
            };
            lector.readAsDataURL(archivo);
            resolverActual = (confirmado) => {
                if (!confirmado) {
                    resolve(null);
                    return;
                }
                const tipo = archivo.type || "image/jpeg";
                cropper.getCroppedCanvas({ imageSmoothingQuality: "high" }).toBlob(
                    (blob) => resolve(blob ? new File([blob], archivo.name, { type: tipo }) : null),
                    tipo,
                    0.92
                );
            };
        });
    }

    /**
     * Conecta un `<input type="file">` a la herramienta de recorte.
     *
     * @param {HTMLInputElement} input Campo de archivo original.
     * @param {{aspectRatio: number, titulo: string, obligatorio: boolean}} opciones
     *     `aspectRatio` en `NaN` deja un recuadro libre (sin proporción
     *     fija) — el caso de las fotos de producto. `obligatorio` abre
     *     el recorte apenas se elige un archivo (logo/portada); si es
     *     `false`, en cambio, se agrega un botón "Recortar" junto al
     *     campo para que el recorte quede a criterio del vendedor y
     *     nunca sea obligatorio.
     */
    window.activarRecorteImagen = function activarRecorteImagen(input, opciones) {
        if (!input) {
            return;
        }

        async function procesar(archivo) {
            const resultado = await abrirModal(archivo, opciones);
            if (!resultado) {
                input.value = "";
                return;
            }
            const dt = new DataTransfer();
            dt.items.add(resultado);
            input.files = dt.files;
        }

        if (opciones.obligatorio) {
            input.addEventListener("change", () => {
                const archivo = input.files[0];
                if (archivo) {
                    procesar(archivo);
                }
            });
            return;
        }

        // Opcional: un botón "Recortar" que aparece junto al campo una
        // vez que el vendedor eligió una foto — nunca se abre solo.
        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "admin-btn admin-btn--pequeno recorte-boton-opcional";
        boton.textContent = "Recortar imagen (opcional)";
        boton.hidden = true;
        input.insertAdjacentElement("afterend", boton);

        input.addEventListener("change", () => {
            boton.hidden = !input.files[0];
        });
        boton.addEventListener("click", () => {
            const archivo = input.files[0];
            if (archivo) {
                procesar(archivo);
            }
        });
    };
})();
