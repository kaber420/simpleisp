export const settingsModule = {
    settings: { suspension_speed: '1k/1k', suspension_method: 'queue', address_list_name: 'clientes_activos', grace_days: '3' },

    async loadSettings() {
        const res = await fetch('/api/settings');
        if (res.ok) this.settings = await res.json();
    },

    async saveSettings() {
        await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.settings) });
        alert("Configuración guardada");
    }
};
