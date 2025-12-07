import { clientsModule } from './modules/clients.js';
import { routersModule } from './modules/routers.js';
import { paymentsModule } from './modules/payments.js';
import { usersModule } from './modules/users.js';
import { settingsModule } from './modules/settings.js';

window.appData = function () {
    return {
        currentTab: 'dashboard',
        trafficData: {},
        systemStats: {},
        isEditing: false,
        editingId: null,

        ...clientsModule,
        ...routersModule,
        ...paymentsModule,
        ...usersModule,
        ...settingsModule,

        init() {
            this.loadClients();
            this.loadRouters();
            this.loadSettings();
            this.connectWebSocket();
        },

        connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws/traffic`);
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this.trafficData = data.queues || {};
                this.systemStats = data.system || {};
            };
            ws.onclose = () => setTimeout(() => this.connectWebSocket(), 3000);
        }
    };
};
