/**
 * Modal de detalle de producto en la tienda pública de un vendedor.
 *
 * Cada tarjeta de producto trae sus datos en atributos `data-*` (ya
 * escapados por Jinja al renderizar), este script solo los copia al
 * modal y lo muestra/oculta. Si el producto tiene más de una foto
 * (`data-fotos`, un array JSON), pinta una fila de miniaturas debajo de
 * la foto principal para poder cambiarla sin cerrar el modal.
 *
 * Video del producto (2026-09-30, roadmap — sección "Video, estados y
 * productos digitales bloqueados"; ampliado 2026-10-01 de YouTube a 8
 * plataformas: YouTube, TikTok, Vimeo, Twitch (video, clip o canal en
 * vivo), Facebook, Threads, Instagram y X — ver
 * app/services/video_service.py). Si la
 * tarjeta trae `data-video-plataforma`/`data-video-valor` (ver
 * resolver_video_producto) el modal muestra la pestaña "Video" además
 * de "Fotos" — un producto puede tener más fotos que la que ya se ve
 * en su tarjeta, así que el usuario tiene que poder volver a verlas
 * sin cerrar el modal (corrección de Jose, 2026-10-01). Siempre se abre
 * mostrando "Fotos" primero. `data-video-vertical` ("1" en TikTok e
 * Instagram) decide si la caja del video usa la proporción vertical
 * (`.tienda-modal__video-wrap--vertical`) o la 16:9 de siempre.
 *
 * Dos mecanismos de embed, según la plataforma (tabla PLATAFORMAS_VIDEO
 * más abajo), para que el vendedor nunca tenga que pensar en esto — él
 * solo pega el link que copió de "Compartir" en la red social:
 * - "iframe": YouTube, TikTok, Vimeo y Twitch tienen un reproductor
 *   embebible público — se arma la URL del iframe a partir del valor
 *   guardado y listo.
 * - "widget": Facebook, Threads, Instagram y X no tienen un iframe
 *   público — cada uno pide un `<div>`/`<blockquote>` con el link en un
 *   atributo `data-*`, y un script propio (su SDK de embeds) que
 *   escanea la página y lo reemplaza por el reproductor real.
 *
 * El mismo modal se reutiliza para el video-tráiler del perfil (punto
 * 22-bis, botones `[data-abrir-trailer]` en la cabecera de las 8
 * plantillas, con `data-plataforma`/`data-valor`/`data-vertical`): ahí
 * se abre en "modo tráiler", que oculta todo lo específico de un
 * producto (precio, descripción, estado de stock, WhatsApp, aviso) Y
 * TAMBIÉN las pestañas — a diferencia del producto, el tráiler nunca
 * tiene fotos propias que mostrar, así que ahí el modal es solo el
 * video, sin nada que elegir.
 *
 * Sin dependencias propias — los 4 SDK de los widgets se cargan como
 * `<script>` sueltos, solo cuando hacen falta (nunca de entrada).
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
    const videoWrap = document.getElementById("tienda-modal-video-wrap");
    const videoWidget = document.getElementById("tienda-modal-video-widget");

    // Una entrada por cada plataforma reconocida en
    // app/services/video_service.py — la clave es exactamente
    // `video_plataforma` tal como lo guarda el backend.
    //
    // tipo "iframe": `src(valor)` devuelve la URL del iframe. `valor`
    // es un ID (YouTube, Vimeo, Twitch video/clip) salvo en TikTok, que
    // guarda el link completo (su link público no es reconstruible
    // solo con el ID — necesita el @usuario) y por eso extrae el ID
    // del link acá mismo con una expresión regular.
    //
    // tipo "widget": no hay iframe público. `marcado(valor)` devuelve
    // el HTML que pide el SDK de esa red (con el link completo en su
    // atributo `data-*`), `script` es la URL de ese SDK, y
    // `reprocesar` es la función que hay que llamar para que el SDK
    // vuelva a escanear el widget recién insertado — ya cargado el
    // script una vez, reabrir el modal con otro video del mismo tipo
    // no debe volver a bajarlo. Twitch necesita además el hostname de
    // la página (parámetro `parent`, obligatorio) — como e-link usa un
    // subdominio distinto por vendedor, no hay forma de armar una
    // lista fija del lado del servidor, así que se calcula aquí con
    // `location.hostname`.
    const PLATAFORMAS_VIDEO = {
        youtube: {
            tipo: "iframe",
            src: (valor) => `https://www.youtube.com/embed/${valor}`,
        },
        tiktok: {
            tipo: "iframe",
            src: (valor) => {
                const match = String(valor).match(/\/video\/(\d+)/);
                return match ? `https://www.tiktok.com/player/v1/${match[1]}` : "";
            },
        },
        vimeo: {
            tipo: "iframe",
            src: (valor) => `https://player.vimeo.com/video/${valor}`,
        },
        twitch_video: {
            tipo: "iframe",
            src: (valor) => `https://player.twitch.tv/?video=${valor}&parent=${location.hostname}`,
        },
        twitch_clip: {
            tipo: "iframe",
            src: (valor) => `https://clips.twitch.tv/embed?clip=${valor}&parent=${location.hostname}`,
        },
        // Canal en vivo (2026-10-01, Jose probó con el link de su propio
        // canal y no se reconocía) — el reproductor de canal de Twitch
        // funciona esté en vivo o no (muestra la pantalla "offline" si no
        // transmite), así que no hace falta saber el estado del stream acá.
        twitch_channel: {
            tipo: "iframe",
            src: (valor) => `https://player.twitch.tv/?channel=${valor}&parent=${location.hostname}`,
        },
        facebook: {
            tipo: "widget",
            script: "https://connect.facebook.net/es_LA/sdk.js#xfbml=1&version=v19.0",
            marcado: (valor) =>
                `<div class="fb-video" data-href="${valor}" data-allowfullscreen="true" data-autoplay="false"></div>`,
            reprocesar: () => {
                if (window.FB && videoWidget) {
                    window.FB.XFBML.parse(videoWidget);
                }
            },
        },
        threads: {
            tipo: "widget",
            script: "https://www.threads.net/embed.js",
            marcado: (valor) =>
                `<blockquote class="text-post-media" data-text-post-permalink="${valor}"><a href="${valor}"></a></blockquote>`,
            // Sin API incremental confirmada en la documentación pública
            // de Threads (a diferencia de FB/Instagram/X) — `reprocesar`
            // queda sin definir a propósito, y cargarScriptWidget()
            // reinyecta el script completo cada vez como alternativa
            // segura (embed.js escanea toda la página al cargar).
        },
        instagram: {
            tipo: "widget",
            script: "https://www.instagram.com/embed.js",
            marcado: (valor) => `<blockquote class="instagram-media" data-instgrm-permalink="${valor}"></blockquote>`,
            reprocesar: () => {
                if (window.instgrm) {
                    window.instgrm.Embeds.process();
                }
            },
        },
        x: {
            tipo: "widget",
            script: "https://platform.twitter.com/widgets.js",
            marcado: (valor) => `<blockquote class="twitter-tweet"><a href="${valor}"></a></blockquote>`,
            reprocesar: () => {
                if (window.twttr && videoWidget) {
                    window.twttr.widgets.load(videoWidget);
                }
            },
        },
    };

    // Scripts de SDK que ya se cargaron una vez en esta página (para no
    // volver a bajarlos cada vez que se abre el modal).
    const scriptsWidgetCargados = new Set();

    // Carga (o reaprovecha) el script del SDK que necesita un widget, y
    // dispara su reprocesamiento sobre el contenido ya insertado en
    // `videoWidget`.
    function cargarScriptWidget(config) {
        if (!config.script) {
            return;
        }
        if (!config.reprocesar) {
            const anterior = document.getElementById("tienda-modal-widget-script");
            if (anterior) {
                anterior.remove();
            }
            const script = document.createElement("script");
            script.id = "tienda-modal-widget-script";
            script.src = config.script;
            script.async = true;
            document.body.appendChild(script);
            return;
        }
        if (scriptsWidgetCargados.has(config.script)) {
            config.reprocesar();
            return;
        }
        const script = document.createElement("script");
        script.src = config.script;
        script.async = true;
        script.addEventListener("load", () => {
            scriptsWidgetCargados.add(config.script);
            config.reprocesar();
        });
        document.body.appendChild(script);
    }

    // Alterna la proporción de la caja del iframe entre 16:9 (YouTube,
    // Vimeo, Twitch) y vertical (TikTok, casi siempre 9:16) — ver
    // .tienda-modal__video-wrap--vertical en tienda.css. No afecta a
    // los widgets, que se autoajustan de tamaño.
    function marcarVideoVertical(esVertical) {
        if (videoWrap) {
            videoWrap.classList.toggle("tienda-modal__video-wrap--vertical", !!esVertical);
        }
    }

    // Vacía el iframe y el widget — se usa al cerrar el modal (para que
    // el video deje de sonar/reproducirse de fondo) y cuando el
    // producto/tráiler no tiene ningún video.
    function limpiarVideo() {
        if (videoIframe) {
            videoIframe.src = "";
        }
        if (videoWidget) {
            videoWidget.innerHTML = "";
        }
    }

    // Muestra el video de `plataforma`/`valor` en el contenedor que
    // corresponda (iframe o widget) y oculta el otro. Devuelve `true`
    // si había un video válido para mostrar, `false` si no (plataforma
    // no reconocida, sin valor, o un `src` de iframe que no se pudo
    // armar) — quien llama usa ese resultado para decidir si el panel
    // de video o el de fotos es el que se ve.
    function mostrarVideo(plataforma, valor) {
        const config = PLATAFORMAS_VIDEO[plataforma];
        if (!config || !valor) {
            limpiarVideo();
            if (videoWrap) videoWrap.hidden = true;
            if (videoWidget) videoWidget.hidden = true;
            return false;
        }

        if (config.tipo === "iframe") {
            const src = config.src(valor);
            if (!src) {
                limpiarVideo();
                if (videoWrap) videoWrap.hidden = true;
                if (videoWidget) videoWidget.hidden = true;
                return false;
            }
            if (videoWidget) {
                videoWidget.innerHTML = "";
                videoWidget.hidden = true;
            }
            if (videoIframe) {
                videoIframe.src = src;
            }
            if (videoWrap) {
                videoWrap.hidden = false;
            }
            return true;
        }

        // tipo "widget"
        if (videoIframe) {
            videoIframe.src = "";
        }
        if (videoWrap) {
            videoWrap.hidden = true;
        }
        if (videoWidget) {
            videoWidget.hidden = false;
            videoWidget.innerHTML = config.marcado(valor);
        }
        cargarScriptWidget(config);
        return true;
    }

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

    // Cambia entre la pestaña "Fotos" y "Video" del modal de producto
    // (solo relevante cuando `tabs` está visible, es decir, cuando el
    // producto abierto tiene video guardado — corrección de Jose,
    // 2026-10-01: a diferencia del tráiler de perfil, que nunca
    // muestra `tabs` porque no tiene fotos que mostrar, un producto
    // puede tener más fotos que la que ya se ve en su tarjeta, y el
    // usuario tiene que poder volver a verlas sin cerrar el modal).
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

        // Pestaña "Video" — solo se ofrece si este producto en
        // particular tiene un video guardado (y el plan Plus del
        // vendedor está vigente, ya resuelto del lado del servidor en
        // data-video-plataforma/data-video-valor). Siempre se abre
        // mostrando "Fotos" primero — el usuario puede cambiar a
        // "Video" y volver, sin perder acceso a ninguna de las dos.
        marcarVideoVertical(tarjeta.dataset.videoVertical);
        const hayVideo = mostrarVideo(tarjeta.dataset.videoPlataforma || "", tarjeta.dataset.videoValor || "");
        if (tabs) tabs.hidden = !hayVideo;
        mostrarPestana("fotos");
        delete modal.dataset.modo;

        modal.hidden = false;
    }

    // Abre el modal en "modo tráiler" (tráiler de perfil gratis): un solo video de
    // presentación del perfil, sin nada de lo específico de un producto.
    function abrirModalTrailer(plataforma, valor, esVertical) {
        if (!plataforma || !valor) {
            return;
        }
        mostrarCamposProducto(false);
        estadoStock.hidden = true;
        if (formAviso) {
            formAviso.hidden = true;
        }
        titulo.textContent = "Video";
        modal.dataset.modo = "trailer";
        if (tabs) tabs.hidden = true;
        if (panelFotos) panelFotos.hidden = true;
        marcarVideoVertical(esVertical);
        const hayVideo = mostrarVideo(plataforma, valor);
        if (panelVideo) panelVideo.hidden = !hayVideo;
        modal.hidden = false;
    }

    function cerrarModal() {
        modal.hidden = true;
        // Vacía el iframe/widget al cerrar para que el video deje de
        // sonar/reproducirse de fondo (ocultar el modal con `hidden` no
        // detiene un <iframe> ni un widget por sí solo).
        limpiarVideo();
    }

    document.querySelectorAll(".tienda-card").forEach((tarjeta) => {
        tarjeta.addEventListener("click", () => abrirModal(tarjeta));
    });

    document.querySelectorAll("[data-abrir-trailer]").forEach((boton) => {
        boton.addEventListener("click", () =>
            abrirModalTrailer(boton.dataset.plataforma || "", boton.dataset.valor || "", boton.dataset.vertical)
        );
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
