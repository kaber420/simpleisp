/**
 * Dashboard Module - Handles dashboard summary data and charts
 */
export const dashboardModule = {
    dashboardData: {
        routers: { total: 0, online: 0, offline: 0, offline_list: [] },
        clients: { total: 0, active: 0, suspended: 0 }
    },
    clientsChart: null,

    async loadDashboardSummary() {
        try {
            const response = await fetch('/api/dashboard/summary');
            if (response.ok) {
                this.dashboardData = await response.json();
                this.renderClientsChart();
            }
        } catch (error) {
            console.error('Error loading dashboard summary:', error);
        }
    },

    renderClientsChart() {
        const canvas = document.getElementById('clientsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.dashboardData.clients;

        // Destroy existing chart if present
        if (this.clientsChart) {
            this.clientsChart.destroy();
        }

        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        this.clientsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Activos', 'Suspendidos'],
                datasets: [{
                    data: [data.active, data.suspended],
                    backgroundColor: [
                        'rgba(34, 197, 94, 0.8)',   // Green for active
                        'rgba(239, 68, 68, 0.8)'    // Red for suspended
                    ],
                    borderColor: [
                        'rgba(34, 197, 94, 1)',
                        'rgba(239, 68, 68, 1)'
                    ],
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#94a3b8',
                            font: { size: 14 },
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 41, 59, 0.95)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                },
                cutout: '65%'
            }
        });
    }
};
