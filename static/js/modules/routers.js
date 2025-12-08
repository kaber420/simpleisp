export const routersModule = {
    routers: [],
    routerStats: {},  // Map of router_id -> stats object
    routerInterfaces: [],  // List of interfaces for the current router being edited
    loadingInterfaces: false,
    statsPollingInterval: null,
    showAddRouterModal: false,
    newRouter: { name: '', ip_address: '', username: '', password: '', port: 8728, is_active: true, wan_interface: '', use_ssl: false },

    formatBytes(bytes, decimals = 1) {
        if (!bytes || bytes === '0 B') return bytes || '0 B';
        // If already formatted (contains unit), return as-is
        if (typeof bytes === 'string' && /[KMGTP]?B$/.test(bytes)) return bytes;

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    },

    async loadRouters() {
        const res = await fetch('/api/routers');
        if (res.ok) {
            this.routers = await res.json();
            // Initialize stats object for each router
            this.routers.forEach(r => {
                if (!this.routerStats[r.id]) {
                    this.routerStats[r.id] = { loading: true, online: null };
                }
            });
        }
    },

    async loadRouterInterfaces(routerId) {
        this.loadingInterfaces = true;
        this.routerInterfaces = [];
        try {
            const res = await fetch(`/api/routers/${routerId}/interfaces`);
            if (res.ok) {
                this.routerInterfaces = await res.json();
            }
        } catch (e) {
            console.error('Error loading interfaces:', e);
        }
        this.loadingInterfaces = false;
    },

    async fetchRouterStats(routerId) {
        try {
            const res = await fetch(`/api/routers/${routerId}/stats`);
            if (res.ok) {
                const data = await res.json();
                this.routerStats[routerId] = { ...data, loading: false };
            } else {
                this.routerStats[routerId] = { online: false, loading: false, error: 'API Error' };
            }
        } catch (e) {
            this.routerStats[routerId] = { online: false, loading: false, error: e.message };
        }
    },

    async fetchAllRouterStats() {
        // Fetch stats for all routers in parallel
        await Promise.all(this.routers.map(r => this.fetchRouterStats(r.id)));
    },

    startStatsPolling() {
        if (this.statsPollingInterval) return; // Already polling
        // Fetch immediately on start
        this.fetchAllRouterStats();
        // Then poll every 10 seconds
        this.statsPollingInterval = setInterval(() => {
            this.fetchAllRouterStats();
        }, 10000);
    },

    stopStatsPolling() {
        if (this.statsPollingInterval) {
            clearInterval(this.statsPollingInterval);
            this.statsPollingInterval = null;
        }
    },

    openCreateRouterModal() {
        this.isEditing = false;
        this.routerInterfaces = [];
        this.newRouter = { name: '', ip_address: '', username: '', password: '', port: 8728, is_active: true, wan_interface: '', use_ssl: false };
        this.showAddRouterModal = true;
    },

    openEditRouterModal(router) {
        this.isEditing = true;
        this.editingId = router.id;
        this.newRouter = { ...router, password: '', wan_interface: router.wan_interface || '', use_ssl: router.use_ssl || false };
        this.showAddRouterModal = true;
        // Load interfaces for this router
        this.loadRouterInterfaces(router.id);
    },

    async saveRouter() {
        const url = this.isEditing ? `/api/routers/${this.editingId}` : '/api/routers';
        const method = this.isEditing ? 'PUT' : 'POST';
        let body = { ...this.newRouter };
        if (this.isEditing && !body.password) {
            delete body.password;
        }
        // Clean up empty wan_interface
        if (!body.wan_interface) {
            body.wan_interface = null;
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
