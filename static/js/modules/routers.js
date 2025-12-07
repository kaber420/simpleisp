export const routersModule = {
    routers: [],
    showAddRouterModal: false,
    newRouter: { name: '', ip_address: '', username: '', password: '', port: 8728, is_active: true },

    async loadRouters() {
        const res = await fetch('/api/routers');
        if (res.ok) this.routers = await res.json();
    },

    openCreateRouterModal() {
        this.isEditing = false;
        this.newRouter = { name: '', ip_address: '', username: '', password: '', port: 8728, is_active: true };
        this.showAddRouterModal = true;
    },

    openEditRouterModal(router) {
        this.isEditing = true;
        this.editingId = router.id;
        this.newRouter = { ...router, password: '' };
        this.showAddRouterModal = true;
    },

    async saveRouter() {
        const url = this.isEditing ? `/api/routers/${this.editingId}` : '/api/routers';
        const method = this.isEditing ? 'PUT' : 'POST';
        let body = { ...this.newRouter };
        if (this.isEditing && !body.password) {
            delete body.password;
        }
        const res = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        if (res.ok) {
            this.showAddRouterModal = false;
            this.loadRouters();
        } else {
            alert("Error guardando router");
        }
    },

    async deleteRouter(id) {
        if (!confirm("¿Borrar Router?")) return;
        await fetch(`/api/routers/${id}`, { method: 'DELETE' });
        this.loadRouters();
    }
};
