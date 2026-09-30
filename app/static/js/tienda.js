/**
 * Modal de detalle de producto en la tienda pública de un vendedor.
 *
 * Cada tarjeta de producto trae sus datos en atributos `data-*` (ya
 * escapados por Jinja al renderizar), este script solo los copia al
 * modal y lo muestra/oculta. Si el producto tiene más de una foto
 * (`data-fotos`, un array JSON), pinta una fila de miniaturas debajo de
 * la foto principal para poder cambiarla sin cerrar el modal.
 *
 * Pestañas "Fotos"/"Video" (2026-09-30, roadmap — embed de YouTube): si la
 * tarjeta trae `data-youtube-embed` (ver resolver_video_producto), el
 * modal muestra la pestaña "Video" además de "Fotos"; si no, las
 * pestañas quedan ocultas y todo se comporta igual que antes.
 *
 * El mismo modal se reutiliza para el video-tráiler del perfil (punto
 * 22-bis, botones `[data-abrir-trailer]` en la cabecera de las 7
 * plantillas): ahí se abre en "modo tráiler", que oculta todo lo
 * específico de un producto (precio, descripción, estado de stock,
 * WhatsApp, aviso) y muestra solo el video, sin pestañas.
 *
 * Sin dependencias.
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
    const estadoStock = document.getElementById("tienda-modal-estado-stock");
    const formAviso = document.getElementById("tienda-aviso-form");
    const avisoProductoId = document.getElementById("tienda-aviso-producto-id");
    const tabs = document.getElementById("tienda-modal-tabs");
    const tabFotosBtn = tabs ? tabs.querySelector('[data-modal-tab="fotos"]') : null;
    const tabVideoBtn = tabs ? tabs.querySelector('[data-modal-tab="video"]') : null;
    const panelFotos = document.getElementById("tienda-modal-panel-fotos");
    const panelVideo = document.getElementById("tienda-modal-panel-video");
    const videoIframe = document.getElementById("tienda-modal-video-iframe");

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

    // Cambia entre la pestaña "Fotos" y "Video" (solo relevante cuando
    // `tabs` está visible, es decir, cuando el producto abierto tiene
    // video) — no toca nada del modo tráiler, que nunca muestra `tabs`.
    function mostrarPestana(pestana) {
        const esFotos = pestana === "fotos";
        if (panelFotos) panelFotos.hidden = !esFotos;
        if (panelVideo) panelVideo.hidden = esFotos;
        if (tabFotosBtn) tabFotosBtn.classList.toggle("tienda-modal__tab--activa", esFotos);
        if (tabVideoBtn) tabVideoBtn.classList.toggle("tienda-modal__tab--activa", !esFotos);
    }

    if (tabFotosBtn) {
        tabFotosBtn.addEventListener("click", () => mostrarPestana("fotos"));
    }
    if (tabVideoBtn) {
        tabVideoBtn.addEventListener("click", () => mostrarPestana("video"));
    }

    // Muestra/oculta todo lo que es específico de un producto (precio,
    // descripción, botón de WhatsApp) — en modo tráiler (`mostrar =
    // false`) el modal es solo el video, sin nada de esto. El estado de
    // stock y el formulario de aviso se ocultan aparte en cada función
    // de apertura porque además dependen del producto en particular.
    function mostrarCamposProducto(mostrar) {
        precio.hidden = !mostrar;
        descripcion.hidden = !mostrar;
        botonWhatsapp.hidden = !mostrar;
    }

    function abrirModal(tarjeta) {
        mostrarCamposProducto(true);
        titulo.textContent = tarjeta.dataset.titulo;
        precio.textContent = tarjeta.dataset.precio;
        descripcion.textContent = tarjeta.dataset.descripcion;
        botonWhatsapp.href = tarjeta.dataset.wa;

        // Estado de stock (punto 17) — data-estado-stock viene vacío
        // ("") para "Normal", así que el texto y el mini-formulario
        // "avísame cuando vuelva" quedan ocultos salvo que el producto
        // tenga un estado guardado (y, para el formulario, que además
        // sea "agotado" en particular).
        const claveEstadoStock = tarjeta.dataset.estadoStock || "";
        if (claveEstadoStock) {
            estadoStock.textContent = tarjeta.dataset.estadoStockNombre || "";
            estadoStock.className = `tienda-estado-stock tienda-estado-stock--${claveEstadoStock}`;
            estadoStock.hidden = false;
        } else {
            estadoStock.hidden = true;
        }

        if (claveEstadoStock === "agotado" && formAviso && avisoProductoId) {
            avisoProductoId.value = tarjeta.dataset.productoId || "";
            formAviso.hidden = false;
        } else if (formAviso) {
            formAviso.hidden = true;
        }

        let fotos = [];
        try {
            fotos = JSON.parse(tarjeta.dataset.fotos || "[]");
        } catch (error) {
            fotos = [];
        }

        mostrarFotoPrincipal(fotos[0] || "");
        pintarMiniaturas(fotos);

        // Pestaña "Video" — solo se ofrece si este producto
        // en particular tiene un video guardado (y el plan Plus del
        // vendedor está vigente, ya resuelto del lado del servidor en
        // data-youtube-embed). Siempre se abre mostrando "Fotos" primero.
        const embedUrl = tarjeta.dataset.youtubeEmbed || "";
        if (videoIframe) {
            videoIframe.src = embedUrl;
        }
        if (tabs) {
            tabs.hidden = !embedUrl;
        }
        mostrarPestana("fotos");

        modal.hidden = false;
    }

    // Abre el modal en "modo tráiler" (tráiler de perfil gratis): un solo video de
    // presentación del perfil, sin nada de lo específico de un producto.
    function abrirModalTrailer(embedUrl) {
        if (!embedUrl) {
            return;
        }
        mostrarCamposProducto(false);
        estadoStock.hidden = true;
        if (formAviso) {
            formAviso.hidden = true;
        }
        if (tabs) {
            tabs.hidden = true;
        }
        titulo.textContent = "Video";
        if (panelFotos) panelFotos.hidden = true;
        if (panelVideo) panelVideo.hidden = false;
        if (videoIframe) {
            videoIframe.src = embedUrl;
        }
        modal.hidden = false;
    }

    function cerrarModal() {
        modal.hidden = true;
        // Vacía el iframe al cerrar para que el video deje de sonar/
        // reproducirse de fondo (ocultar el modal con `hidden` no
        // detiene un <iframe> por sí solo).
        if (videoIframe) {
            videoIframe.src = "";
        }
    }

    document.querySelectorAll(".tienda-card").forEach((tarjeta) => {
        tarjeta.addEventListener("click", () => abrirModal(tarjeta));
    });

    document.querySelectorAll("[data-abrir-trailer]").forEach((boton) => {
        boton.addEventListener("click", () => abrirModalTrailer(boton.dataset.embed || ""));
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
