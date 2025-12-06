function appData() {
    return {
        currentTab: 'dashboard',
        clients: [],
        routers: [],
        trafficData: {},
        systemStats: {},
        showAddClientModal: false,
        showAddRouterModal: false,
        isEditing: false,
        editingId: null,
        newClient: { name: '', ip_address: '', limit_max_upload: '5M', limit_max_download: '10M', billing_day: 1 },
        newRouter: { name: '', ip_address: '', username: '', password: '', port: 8728, is_active: true },
        newPayment: { client_id: '', month_paid: '', amount: 0 },
        paymentHistory: [],
        paymentMonths: [],
        users: [],
        userLoadError: '',
        showCreateUserModal: false,
        newUser: { email: '', password: '', is_superuser: false },

        // Settings con valores default
        settings: { suspension_speed: '1k/1k', suspension_method: 'queue', address_list_name: 'clientes_activos', grace_days: '3' },

        init() {
            this.loadClients();
            this.loadRouters();
            this.loadSettings();
            this.connectWebSocket();
        },
        
        async loadClients() {
            const res = await fetch('/api/clients');
            if (res.ok) this.clients = await res.json();
        },
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
        },
        openCreateModal() { this.isEditing = false; this.newClient = { name: '', ip_address: '', limit_max_upload: '5M', limit_max_download: '10M', billing_day: 1 }; this.showAddClientModal = true; },
        openEditModal(client) { this.isEditing = true; this.editingId = client.id; this.newClient = { ...client }; this.showAddClientModal = true; },
        async saveClient() {
            const url = this.isEditing ? `/api/clients/${this.editingId}` : '/api/clients';
            const method = this.isEditing ? 'PUT' : 'POST';
            await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.newClient) });
            this.showAddClientModal = false; this.loadClients();
        },
        async deleteClient(id) {
            if (!confirm("¿Borrar?")) return;
            await fetch(`/api/clients/${id}`, { method: 'DELETE' });
            this.loadClients();
        },
        async submitPayment() {
            if (!this.newPayment.month_paid) {
                alert('Por favor selecciona un mes');
                return;
            }
            try {
                const res = await fetch('/api/payments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newPayment)
                });
                if (!res.ok) {
                    const error = await res.json();
                    alert(error.detail || 'Error al registrar el pago');
                    return;
                }
                await this.loadPaymentMonths(this.newPayment.client_id);
                this.loadClients();
                this.newPayment.month_paid = '';
                this.newPayment.amount = 0;
                alert("Pago registrado exitosamente");
            } catch (error) {
                alert('Error al registrar el pago');
            }
        },
        async loadHistory(id) {
            if (!id) return;
            const res = await fetch(`/api/payments/${id}`);
            this.paymentHistory = await res.json();
        },
        async loadPaymentMonths(clientId) {
            if (!clientId) return;

            // Cargar historial
            await this.loadHistory(clientId);

            // Generar array de meses (6 anteriores + mes actual + 5 futuros)
            const months = [];
            const today = new Date();
            const currentMonth = today.toISOString().slice(0, 7);

            for (let i = -6; i <= 5; i++) {
                const date = new Date(today.getFullYear(), today.getMonth() + i, 1);
                const monthValue = date.toISOString().slice(0, 7);
                const paid = this.paymentHistory.some(p => p.month_paid === monthValue);

                months.push({
                    value: monthValue,
                    label: this.formatMonth(monthValue),
                    paid: paid,
                    isCurrent: monthValue === currentMonth
                });
            }

            this.paymentMonths = months;
        },
        selectMonth(monthObj) {
            if (!monthObj.paid) {
                this.newPayment.month_paid = monthObj.value;
            }
        },
        formatMonth(monthStr) {
            const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            const [year, month] = monthStr.split('-');
            return `${months[parseInt(month) - 1]} ${year}`;
        },

        // Settings Functions
        async loadSettings() {
            const res = await fetch('/api/settings');
            if (res.ok) this.settings = await res.json();
        },
        async saveSettings() {
            await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.settings) });
            alert("Configuración guardada");
        },


        // User Management Functions
        async loadUsers() {
            this.userLoadError = '';
            try {
                const res = await fetch('/api/users/');
                if (res.ok) {
                    this.users = await res.json();
                } else {
                    this.userLoadError = `Error: ${res.status} ${res.statusText}`;
                    if (res.status === 403) {
                        this.userLoadError += ' (Permiso denegado)';
                    }
                    console.error('Failed to load users:', res.status);
                }
            } catch (error) {
                console.error('Error loading users:', error);
                this.userLoadError = `Error de conexión: ${error.message}`;
            }
        },
        openCreateUserModal() {
            this.newUser = { email: '', password: '', is_superuser: false };
            this.showCreateUserModal = true;
        },
        async createUser() {
            try {
                const res = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newUser)
                });
                if (res.ok) {
                    alert('Usuario creado exitosamente');
                    this.showCreateUserModal = false;
                    await this.loadUsers();
                } else {
                    const error = await res.json();
                    alert(error.detail || 'Error al crear usuario');
                }
            } catch (error) {
                alert('Error de conexión');
            }
        },
        async toggleUserStatus(user) {
            try {
                const res = await fetch(`/api/users/${user.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: !user.is_active })
                });
                if (res.ok) {
                    await this.loadUsers();
                }
            } catch (error) {
                alert('Error al actualizar usuario');
            }
        },
        async deleteUser(id) {
            if (!confirm("¿Estás seguro de eliminar este usuario?")) return;
            try {
                const res = await fetch(`/api/users/${id}`, {
                    method: 'DELETE'
                });
                if (res.ok) {
                    await this.loadUsers();
                } else {
                    alert('Error al eliminar usuario');
                }
            } catch (error) {
                alert('Error de conexión');
            }
        },
        async logout() {
            try {
                const res = await fetch('/auth/logout', { method: 'POST' });
                if (res.ok) {
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error('Logout error:', error);
                window.location.href = '/login';
            }
        },

        connectWebSocket() {
            // (Misma lógica WebSocket que antes)
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws/traffic`);
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this.trafficData = data.queues || {};
                this.systemStats = data.system || {};
            };
            ws.onclose = () => setTimeout(() => this.connectWebSocket(), 3000);
        }
    }
}
