const slideSection = document.getElementById('slideSection');
const mainHeading = document.getElementById('mainHeading');
const mainParagraph = document.getElementById('mainParagraph');

if (slideSection) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                // Mostrar sección y ocultar contenido anterior
                entry.target.classList.remove('opacity-0');
                entry.target.classList.add('animate-slide');
                if (mainHeading) mainHeading.classList.add('hidden');
                if (mainParagraph) mainParagraph.classList.add('hidden');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    observer.observe(slideSection);
}
