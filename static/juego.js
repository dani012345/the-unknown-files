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
    // El plano cubre la pantalla y mantiene las zonas sobre sus objetos.
    const world = document.querySelector('[data-scene-world]');
    const background = document.querySelector('[data-scene-background]');
    const gameInterface = document.querySelector('.game-interface');
    const bedroomFocus = Number(world?.dataset.focusX);
    const hotspots = Array.from(world?.querySelectorAll('.scene-hotspot') ?? [], spot => {
        const coordinate = name => parseFloat(spot.style.getPropertyValue(name)) / 100;
        return { x: coordinate('--x'), right: coordinate('--x') + coordinate('--w'),
                 bottom: coordinate('--y') + coordinate('--h') };
    });
    const actionBottom = Math.max(Number(world?.dataset.actionBottom ?? 0),
        ...(Number.isFinite(bedroomFocus) ? hotspots.map(spot => spot.bottom) : []));
    const clamp = (value, min, max) => Math.max(min, Math.min(value, max));
    const fitScene = () => {
        if (!world || !background?.naturalWidth) return;
        const scene = world.parentElement;
        const { clientWidth, clientHeight } = scene;
        const scale = Math.max(clientWidth / background.naturalWidth, clientHeight / background.naturalHeight);
        const width = Math.max(clientWidth, background.naturalWidth * scale);
        const height = Math.max(clientHeight, background.naturalHeight * scale);
        let focusX = Number.isFinite(bedroomFocus) ? bedroomFocus : .5;
        if (Number.isFinite(bedroomFocus) && hotspots.length) {
            const leftEdge = Math.min(...hotspots.map(spot => spot.x));
            const rightEdge = Math.max(...hotspots.map(spot => spot.right));
            const halfView = clientWidth / (2 * width);
            focusX = rightEdge - leftEdge <= 2 * halfView
                ? clamp(focusX, rightEdge - halfView, leftEdge + halfView)
                : (leftEdge + rightEdge) / 2;
        }
        const left = clamp(clientWidth / 2 - width * focusX, clientWidth - width, 0);
        let top = 'focusTop' in world.dataset ? 0 : (clientHeight - height) / 2;
        if (actionBottom && gameInterface) {
            const clearHeight = gameInterface.getBoundingClientRect().top - scene.getBoundingClientRect().top - 8;
            top = Math.min(top, clearHeight - height * actionBottom);
        }
        top = clamp(top, clientHeight - height, 0);
        world.style.left = `${left + width / 2}px`;
        world.style.top = `${top + height / 2}px`;
        world.style.width = `${width}px`;
        world.style.height = `${height}px`;
    };
    background?.addEventListener('load', fitScene);
    if (world) {
        const observer = new ResizeObserver(fitScene);
        observer.observe(world.parentElement);
        if (gameInterface && actionBottom) observer.observe(gameInterface);
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
