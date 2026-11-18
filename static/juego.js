/* La historia se valida en Python. Este archivo solo mejora los controles. */
(() => {
    const pause = document.getElementById('pause-dialog');
    const menu = document.querySelector('.game-menu');
    document.addEventListener('pointerdown', event => {
        if (menu?.open && !menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && menu?.open) menu.open = false;
    });
    document.querySelector('[data-open-pause]')?.addEventListener('click', () => { if (menu) menu.open = false; pause?.showModal(); });
    document.querySelectorAll('.restart-form').forEach(form => form.addEventListener('submit', event => {
        if (!confirm('¿Empezar una nueva partida? La actual quedará archivada y la nueva comenzará desde el principio.')) event.preventDefault();
    }));
    // Evita dobles clics; la revisión de MongoDB también evita aplicar acciones dos veces.
    document.querySelectorAll('.game-action').forEach(form => form.addEventListener('submit', () => {
        const button = form.querySelector('button');
        if (button) { button.disabled = true; if (!button.querySelector('img')) button.textContent = 'Guardando…'; }
    }));
    // Fondo y zonas clicables conservan la misma escala, incluso en vertical.
    const world = document.querySelector('[data-scene-world]');
    const background = document.querySelector('[data-scene-background]');
    const dialogueBox = document.querySelector('.dialogue-box');
    const fitScene = () => {
        if (!world || !background?.naturalWidth) return;
        const scene = world.parentElement;
        const fit = world.dataset.sceneFit ? Math.min : Math.max;
        const widthScale = scene.clientWidth / background.naturalWidth;
        let scale = fit(widthScale, scene.clientHeight / background.naturalHeight);
        world.style.top = '';
        if (world.dataset.sceneFit === 'shoes' && dialogueBox) {
            const clearHeight = dialogueBox.getBoundingClientRect().top - scene.getBoundingClientRect().top - 8;
            const imageHeight = background.naturalHeight * scale;
            // El gesto de calzarse queda en el tercio inferior del fondo.
            const shoeBottom = (scene.clientHeight - imageHeight) / 2 + imageHeight * .94;
            if (clearHeight > 0 && shoeBottom > clearHeight) {
                scale = Math.min(widthScale, clearHeight / background.naturalHeight);
                world.style.top = `${clearHeight / 2}px`;
            }
        }
        world.style.width = `${background.naturalWidth * scale}px`;
        world.style.height = `${background.naturalHeight * scale}px`;
    };
    background?.addEventListener('load', fitScene);
    if (world) {
        const observer = new ResizeObserver(fitScene);
        observer.observe(world.parentElement);
        if (dialogueBox && world.dataset.sceneFit === 'shoes') observer.observe(dialogueBox);
    }
    fitScene();
    document.querySelector('[data-show-hotspots]')?.addEventListener('click', event => {
        const visible = world.classList.toggle('show-hotspots');
        event.currentTarget.setAttribute('aria-pressed', String(visible));
        event.currentTarget.textContent = visible ? 'Ocultar objetos' : 'Mostrar objetos';
    });
    const photo = document.getElementById('photo-dialog');
    document.querySelectorAll('[data-open-evidence]').forEach(button => button.addEventListener('click', () => photo?.showModal()));
    document.querySelector('[data-toggle-photo]')?.addEventListener('click', event => {
        const detail = photo.classList.toggle('is-detail');
        event.currentTarget.setAttribute('aria-pressed', String(detail));
        event.currentTarget.textContent = detail ? 'Ver foto completa' : 'Ampliar gafete';
        photo.querySelector('[data-photo-caption]').textContent = detail ? 'Detalle del gafete: RAMIRO.' : 'Una celebración en el mismo salón. Al reverso se lee: 1987.';
    });
    addEventListener('pageshow' , event => { if (event.persisted) location.reload(); });
})();
