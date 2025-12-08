export const settingsModule = {
    settings: { suspension_speed: '1k/1k', suspension_method: 'queue', address_list_name: 'clientes_activos', grace_days: '3' },

    async loadSettings() {
        const res = await fetch('/api/settings');
        if (res.ok) this.settings = await res.json();
    },

    async saveSettings() {
        await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.settings) });
        alert("Configuración guardada");
    },

    async runSuspensions() {
        if (!confirm("¿Estás seguro de ejecutar el proceso de cortes? Esto suspenderá a los clientes con pagos vencidos.")) return;

        try {
            const res = await fetch('/api/payments/run-suspensions', { method: 'POST' });
            const data = await res.json();
            alert(data.detail + (data.processed ? ` (${data.processed} cambios)` : ""));
        } catch (e) {
            console.error(e);
            alert("Error al ejecutar suspensiones");
        }
    }
};
