/* Entrada cinematográfica del archivo. El contenido funciona sin JavaScript. */
(() => {
    const body = document.body;
    const intro = document.querySelector('.room-intro');
    const skip = document.querySelector('.skip-intro');
    const stage = document.querySelector('.room-backdrop');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const storageKey = 'uf-office-intro-v1';
    if (!intro || !skip || !stage || reducedMotion.matches) return;
    try { if (sessionStorage.getItem(storageKey)) return; } catch (_) { /* Almacenamiento opcional. */ }

    let timer;
    function finish() {
        body.classList.remove('scene-entering');
        clearTimeout(timer);
        document.removeEventListener('keydown', onKey);
        skip.removeEventListener('click', finish);
        if (document.activeElement === skip) {
            document.querySelector('.investigation-desk a')?.focus({ preventScroll: true });
        }
    }
    function onKey(event) { if (event.key === 'Escape') finish(); }
    const image = new Image();
    image.onload = () => {
        if (reducedMotion.matches) return;
        try { sessionStorage.setItem(storageKey, '1'); } catch (_) { /* Sin persistencia. */ }
        body.classList.add('scene-entering');
        skip.addEventListener('click', finish);
        document.addEventListener('keydown', onKey);
        timer = setTimeout(finish, 2700);
    };
    // Precargar exactamente el mismo recurso que usa la hoja CSS.
    const background = getComputedStyle(stage).backgroundImage;
    const match = background.match(/url\(["']?(.*?)["']?\)/);
    if (match) image.src = match[1];
})();
