(() => {
    const image = document.getElementById('shop-image-dialog');
    document.querySelector('[data-open-image]')?.addEventListener('click', () => image?.showModal());
    document.querySelector('[data-close-image]')?.addEventListener('click', () => image?.close());
    image?.addEventListener('click', event => { if (event.target === image) image.close(); });
    document.querySelectorAll('.shop-purchase-form').forEach(form => form.addEventListener('submit', () => {
        const button = form.querySelector('button[type="submit"]');
        if (button) { button.disabled = true; button.textContent = 'Guardando…'; }
    }));
    const reservation = document.querySelector('[data-reservation]');
    if (!reservation) return;
    const clock = reservation.querySelector('[data-clock]');
    const countdown = reservation.querySelector('[data-countdown]');
    let remaining = Date.parse(reservation.dataset.expires) - Date.parse(reservation.dataset.serverTime);
    let lastSync = performance.now();
    let state = reservation.dataset.state;
    let polling = false;
    let finalRequest = false;
    const messages = {
        vencida: 'El tiempo terminó. La reserva venció y la unidad se liberó.',
        cancelada: 'La reserva fue cancelada y la unidad se liberó.',
        confirmada: 'Compra simulada confirmada. Puedes encontrarla en tu colección.',
    };
    const render = () => {
        if (state !== 'temporal') {
            countdown.hidden = true;
            reservation.querySelector('[data-hold-actions]')?.setAttribute('hidden', '');
            reservation.querySelector('[data-state-label]').textContent = state[0].toUpperCase() + state.slice(1);
            reservation.querySelector('[data-state-message]').textContent = messages[state] || 'La reserva terminó.';
            return;
        }
        const seconds = Math.max(0, Math.ceil((remaining - (performance.now() - lastSync)) / 1000));
        clock.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
        if (seconds === 0) {
            reservation.querySelectorAll('[data-hold-actions] button').forEach(button => { button.disabled = true; });
            if (!finalRequest) { finalRequest = true; refresh(); }
        }
    };
    async function refresh() {
        if (polling || state !== 'temporal') return;
        polling = true;
        try {
            const response = await fetch(reservation.dataset.statusUrl, { cache: 'no-store', headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error('Estado no disponible');
            const data = await response.json();
            state = data.estado;
            remaining = Date.parse(data.expira_en) - Date.parse(data.servidor);
            lastSync = performance.now();
            render();
        } catch {
            reservation.querySelector('[data-state-message]').textContent = 'No pudimos actualizar el estado. El servidor volverá a comprobar el plazo antes de confirmar la compra.';
            finalRequest = false;
        } finally { polling = false; }
    }
    render();
    setInterval(render, 1000);
    setInterval(refresh, 5000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
