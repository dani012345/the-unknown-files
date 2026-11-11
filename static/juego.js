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
    const fitScene = () => {
        if (!world || !background?.naturalWidth) return;
        const scene = world.parentElement;
        const scale = Math.max(
            scene.clientWidth / background.naturalWidth,
            scene.clientHeight / background.naturalHeight
        );
        world.style.width = `${background.naturalWidth * scale}px`;
        world.style.height = `${background.naturalHeight * scale}px`;
    };
    background?.addEventListener('load', fitScene);
    if (world) new ResizeObserver(fitScene).observe(world.parentElement);
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
