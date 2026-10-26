/* La historia se valida en Python. Este archivo solo mejora los controles. */
(() => {
    const pause = document.getElementById('pause-dialog');
    document.querySelector('[data-open-pause]')?.addEventListener('click', () => pause?.showModal());
    document.querySelectorAll('.restart-form').forEach(form => form.addEventListener('submit', event => {
        if (!confirm('¿Empezar una nueva partida? La actual quedará archivada y la nueva comenzará desde el principio.')) event.preventDefault();
    }));
    // Evita dobles clics; la revisión de MongoDB también evita aplicar acciones dos veces.
    document.querySelectorAll('.game-action').forEach(form => form.addEventListener('submit', () => {
        const button = form.querySelector('button');
        if (button) { button.disabled = true; button.textContent = 'Guardando…'; }
    }));
    addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
})();
