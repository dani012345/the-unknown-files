/* El escritorio y sus enlaces funcionan sin JS. Con JS, cada carpeta se levanta. */
(() => {
    const camera = document.querySelector('.office-camera');
    const image = document.querySelector('.office-image');
    const skip = document.querySelector('.skip-approach');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const storageKey = 'uf-desk-approach-v3';
    let approach;
    let activeDialog;
    let opener;
    let lifting;
    let closing = false;

    function stopApproach() {
        approach?.cancel();
        approach = null;
        if (skip) skip.hidden = true;
    }
    function startApproach() {
        if (!camera || !skip || reduced.matches || !camera.animate) return;
        try { if (sessionStorage.getItem(storageKey)) return; } catch (_) {}
        try { sessionStorage.setItem(storageKey, '1'); } catch (_) {}
        skip.hidden = false;
        approach = camera.animate([
            { transform: 'scale(1) translateY(0)' },
            { transform: window.matchMedia('(max-width: 700px)').matches ? 'scale(1.14) translateY(1%)' : 'scale(1.245) translateY(1%)' }
        ], { duration: 2600, easing: 'cubic-bezier(.22,.5,.25,1)' });
        approach.finished.then(stopApproach, () => {});
    }
    function getLiftTransform(trigger, carrier) {
        const source = trigger.getBoundingClientRect();
        const target = carrier.getBoundingClientRect();
        const x = source.left + source.width / 2 - (target.left + target.width / 2);
        const y = source.top + source.height / 2 - target.top;
        const scale = Math.max(.1, Math.min(.4, source.width / target.width));
        return `translate(${x}px, ${y}px) scale(${scale}) rotateX(35deg) rotate(-4deg)`;
    }
    function openDocument(trigger) {
        const dialog = document.getElementById(trigger.dataset.document);
        if (!dialog || typeof dialog.showModal !== 'function') return false;
        stopApproach();
        if (activeDialog) return true;
        opener = trigger;
        activeDialog = dialog;
        dialog.showModal();
        dialog.scrollTop = 0;
        document.body.classList.add('document-open');
        const carrier = dialog.querySelector('.document-carrier');
        if (!reduced.matches && carrier?.animate) {
            lifting = carrier.animate([
                { transform: getLiftTransform(trigger, carrier), opacity: .25 },
                { transform: 'none', opacity: 1 }
            ], { duration: 650, easing: 'cubic-bezier(.16,.7,.2,1)' });
        }
        return true;
    }
    async function closeDocument() {
        if (!activeDialog || closing) return;
        closing = true;
        const dialog = activeDialog;
        lifting?.cancel();
        const carrier = dialog.querySelector('.document-carrier');
        if (!reduced.matches && carrier?.animate && opener) {
            const returning = carrier.animate([
                { transform: 'none', opacity: 1 },
                { transform: getLiftTransform(opener, carrier), opacity: 0 }
            ], { duration: 320, easing: 'ease-in', fill: 'forwards' });
            try { await returning.finished; } catch (_) {}
            returning.cancel();
        }
        dialog.close();
        closing = false;
    }
    document.querySelectorAll('[data-document]').forEach(trigger => {
        const dialog = document.getElementById(trigger.dataset.document);
        if (typeof dialog?.showModal === 'function') {
            trigger.setAttribute('aria-haspopup', 'dialog');
            trigger.setAttribute('aria-controls', dialog.id);
        }
        trigger.addEventListener('click', event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) return;
            if (openDocument(trigger)) event.preventDefault();
        });
    });
    document.querySelectorAll('.document-view').forEach(dialog => {
        dialog.querySelector('[data-close-document]')?.addEventListener('click', closeDocument);
        dialog.addEventListener('cancel', event => { event.preventDefault(); closeDocument(); });
        dialog.addEventListener('click', event => {
            if (event.target !== dialog) return;
            const rect = dialog.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeDocument();
        });
        dialog.addEventListener('close', () => {
            activeDialog = null;
            closing = false;
            document.body.classList.remove('document-open');
            opener?.focus({ preventScroll: true });
        });
    });
    skip?.addEventListener('click', stopApproach);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !activeDialog) stopApproach();
    });
    reduced.addEventListener('change', () => { if (reduced.matches) { stopApproach(); lifting?.cancel(); } });
    if (image?.complete && image.naturalWidth > 0) startApproach();
    else image?.addEventListener('load', startApproach, { once: true });
})();
