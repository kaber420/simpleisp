export const paymentsModule = {
    newPayment: { client_id: '', month_paid: '', amount: 0 },
    paymentHistory: [],
    paymentMonths: [],
    paymentSearchQuery: '',
    isPaymentDropdownOpen: false,

    getFilteredPaymentClients() {
        if (!this.paymentSearchQuery) return this.clients;
        const query = this.paymentSearchQuery.toLowerCase();
        return this.clients.filter(c => c.name.toLowerCase().includes(query));
    },

    selectPaymentClient(client) {
        this.newPayment.client_id = client.id;
        this.paymentSearchQuery = client.name;
        this.isPaymentDropdownOpen = false;
        this.loadPaymentMonths(client.id);
    },

    clearPaymentClient() {
        this.newPayment.client_id = '';
        this.paymentSearchQuery = '';
        this.paymentHistory = [];
        this.paymentMonths = [];
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
    }
};
