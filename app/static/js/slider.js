/**
 * Slider de destacados de la página de inicio.
 *
 * Carrusel simple basado en scroll-snap nativo (sin dependencias):
 * las flechas y los puntos solo controlan el scroll de la pista, y el
 * autoplay pausa mientras el mouse está encima. Si solo hay una
 * diapositiva, esta plantilla ni siquiera incluye este script.
 */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".hero-slider").forEach(inicializarSlider);
});

function inicializarSlider(slider) {
    const track = slider.querySelector(".hero-slider__track");
    const slides = Array.from(track.children);
    if (slides.length < 2) {
        return;
    }

    const dotsContainer = slider.querySelector(".hero-slider__dots");
    const dots = slides.map((_, indice) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "hero-slider__dot";
        dot.setAttribute("aria-label", `Ir a la diapositiva ${indice + 1}`);
        dot.addEventListener("click", () => irA(indice));
        dotsContainer?.appendChild(dot);
        return dot;
    });

    function actualizarDots(indiceActivo) {
        dots.forEach((dot, indice) => {
            dot.classList.toggle("hero-slider__dot--active", indice === indiceActivo);
        });
    }

    function irA(indice) {
        slides[indice].scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });
    }

    function indiceActual() {
        const centro = track.scrollLeft + track.clientWidth / 2;
        let mejorIndice = 0;
        let mejorDistancia = Infinity;
        slides.forEach((slide, indice) => {
            const distancia = Math.abs(slide.offsetLeft + slide.clientWidth / 2 - centro);
            if (distancia < mejorDistancia) {
                mejorDistancia = distancia;
                mejorIndice = indice;
            }
        });
        return mejorIndice;
    }

    let temporizadorScroll;
    track.addEventListener("scroll", () => {
        window.clearTimeout(temporizadorScroll);
        temporizadorScroll = window.setTimeout(() => actualizarDots(indiceActual()), 100);
    });

    slider.querySelector(".hero-slider__btn--prev")?.addEventListener("click", () => {
        irA(Math.max(0, indiceActual() - 1));
    });
    slider.querySelector(".hero-slider__btn--next")?.addEventListener("click", () => {
        irA(Math.min(slides.length - 1, indiceActual() + 1));
    });

    actualizarDots(0);

    const INTERVALO_MS = 6000;
    let autoplay = window.setInterval(avanzar, INTERVALO_MS);

    function avanzar() {
        irA((indiceActual() + 1) % slides.length);
    }

    slider.addEventListener("mouseenter", () => window.clearInterval(autoplay));
    slider.addEventListener("mouseleave", () => {
        autoplay = window.setInterval(avanzar, INTERVALO_MS);
    });
}
