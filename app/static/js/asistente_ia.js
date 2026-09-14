/**
 * Botón "Escribir con IA" del panel de vendedor (perfil y ficha de
 * producto) — genera o mejora un primer borrador a partir de los datos
 * que el vendedor ya cargó (roadmap, "Ideas para más adelante", anotada
 * 2026-09-13, construida 2026-09-14). Nunca guarda nada por sí solo:
 * solo llena el textarea correspondiente, el vendedor decide si lo
 * ajusta y guarda el formulario como siempre.
 *
 * Si el asistente todavía no está configurado en este entorno (falta
 * la API key, ver app/services/asistente_ia_service.py), el propio
 * servidor no imprime el botón — este script no asume que exista,
 * simplemente no hace nada si no lo encuentra en la página.
 */
(function () {
    "use strict";

    function conectarBoton(boton, { campoTexto, aviso, construirCuerpo }) {
        if (!boton || !campoTexto) {
            return;
        }
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        const textoOriginal = boton.textContent;

        boton.addEventListener("click", async () => {
            if (aviso) {
                aviso.textContent = "";
            }
            boton.disabled = true;
            boton.textContent = "Escribiendo…";

            try {
                const respuesta = await fetch(boton.dataset.url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        csrf_token: csrfInput ? csrfInput.value : "",
                        borrador: campoTexto.value.trim(),
                        ...construirCuerpo(),
                    }),
                });
                const datos = await respuesta.json();
                if (!respuesta.ok) {
                    throw new Error(datos.error || "No se pudo generar el texto. Intenta de nuevo.");
                }
                campoTexto.value = datos.texto;
                campoTexto.dispatchEvent(new Event("input"));
                campoTexto.focus();
            } catch (error) {
                if (aviso) {
                    aviso.textContent = error.message;
                }
            } finally {
                boton.disabled = false;
                boton.textContent = textoOriginal;
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        conectarBoton(document.getElementById("asistente-ia-producto"), {
            campoTexto: document.getElementById("descripcion"),
            aviso: document.getElementById("asistente-ia-producto-aviso"),
            construirCuerpo: () => {
                const selectCategoria = document.getElementById("categoria_id");
                let categoria = "";
                if (selectCategoria && selectCategoria.selectedIndex >= 0) {
                    const texto = selectCategoria.options[selectCategoria.selectedIndex].text;
                    categoria = texto === "Sin categoría" ? "" : texto;
                }
                const campoTitulo = document.getElementById("titulo");
                return { titulo: campoTitulo ? campoTitulo.value.trim() : "", categoria };
            },
        });

        conectarBoton(document.getElementById("asistente-ia-perfil"), {
            campoTexto: document.getElementById("bio"),
            aviso: document.getElementById("asistente-ia-perfil-aviso"),
            construirCuerpo: () => {
                const campoNombre = document.getElementById("nombre_negocio");
                return { nombre_negocio: campoNombre ? campoNombre.value.trim() : "" };
            },
        });
    });
})();
