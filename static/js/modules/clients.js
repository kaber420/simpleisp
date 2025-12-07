export const clientsModule = {
    clients: [],
    showAddClientModal: false,
    newClient: { name: '', ip_address: '', limit_max_upload: '5M', limit_max_download: '10M', billing_day: 1 },

    async loadClients() {
        const res = await fetch('/api/clients');
        if (res.ok) this.clients = await res.json();
    },

    openCreateModal() {
        this.isEditing = false;
        this.newClient = { name: '', ip_address: '', limit_max_upload: '5M', limit_max_download: '10M', billing_day: 1 };
        this.showAddClientModal = true;
    },

    openEditModal(client) {
        this.isEditing = true;
        this.editingId = client.id;
        this.newClient = { ...client };
        this.showAddClientModal = true;
    },

    async saveClient() {
        const url = this.isEditing ? `/api/clients/${this.editingId}` : '/api/clients';
        const method = this.isEditing ? 'PUT' : 'POST';
        await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.newClient) });
        this.showAddClientModal = false;
        this.loadClients();
    },

    async deleteClient(id) {
        if (!confirm("¿Borrar?")) return;
        await fetch(`/api/clients/${id}`, { method: 'DELETE' });
        this.loadClients();
    }
};
