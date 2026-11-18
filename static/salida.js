(() => {
    const panel = document.getElementById('exit-panel');
    if (!panel || typeof panel.showModal !== 'function') return;
    const confirmation = panel.querySelector('[data-exit-confirm]');
    const complete = panel.querySelector('[data-exit-complete]');
    const error = panel.querySelector('[data-exit-error]');
    const form = panel.querySelector('[data-exit-form]');
    let submitting = false;
    const openPanel = () => {
        if (panel.open) panel.close();
        panel.showModal();
    };
    document.querySelectorAll('[data-exit-trigger]').forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();
            openPanel();
        });
    });
    panel.querySelectorAll('[data-exit-close]').forEach(button => {
        button.addEventListener('click', () => {
            if (submitting) return;
            if (panel.dataset.openInitial === 'true') {
                window.location.assign('/');
            } else {
                panel.close();
            }
        });
    });
    panel.addEventListener('cancel', event => {
        if (submitting || panel.dataset.closed === 'true') {
            event.preventDefault();
        } else if (panel.dataset.openInitial === 'true') {
            event.preventDefault();
            window.location.assign('/');
        }
    });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (submitting) return;
        submitting = true;
        error.hidden = true;
        const buttons = panel.querySelectorAll('button');
        buttons.forEach(button => { button.disabled = true; });
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { Accept: 'application/json' },
                credentials: 'same-origin'
            });
            const result = await response.json().catch(() => ({
                error: 'La sesión cambió. Recarga la página e inténtalo de nuevo.'
            }));
            if (!response.ok || !result.ok) {
                throw new Error(result.error || 'No se pudo cerrar la sesión. Recarga e inténtalo de nuevo.');
            }
            panel.dataset.closed = 'true';
            panel.setAttribute('aria-labelledby', 'exit-done-title');
            confirmation.hidden = true;
            complete.hidden = false;
            panel.querySelector('[data-exit-done-title]').focus();
        } catch (failure) {
            error.textContent = failure.message;
            error.hidden = false;
            buttons.forEach(button => { button.disabled = false; });
        } finally {
            submitting = false;
        }
    });
    if (panel.dataset.openInitial === 'true') openPanel();
})();
