// Notifications module for Telegram integration
export const notificationsModule = {
    // Telegram config
    telegramToken: '',
    telegramBotName: '',
    botStatus: 'checking',

    // Linking
    linkCode: '',
    manualChatId: '',

    // User status
    telegramLinked: false,
    userChatId: null,
    receiveAlerts: true,

    async loadNotificationSettings() {
        try {
            // Load bot settings
            const settingsRes = await fetch('/api/settings/');
            const settings = await settingsRes.json();
            this.telegramToken = settings.telegram_bot_token || '';
            this.telegramBotName = settings.telegram_bot_name || '';

            // Load bot status
            const statusRes = await fetch('/api/settings/telegram/status');
            const status = await statusRes.json();
            this.botStatus = status.status;

            // Load user notification status
            const myStatusRes = await fetch('/api/settings/notifications/my-status');
            const myStatus = await myStatusRes.json();
            this.telegramLinked = myStatus.telegram_linked;
            this.userChatId = myStatus.telegram_chat_id;
            this.receiveAlerts = myStatus.receive_alerts;
        } catch (e) {
            console.error('Error loading notification settings:', e);
        }
    },

    async saveTelegramToken() {
        try {
            const res = await fetch('/api/settings/telegram/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: this.telegramToken,
                    bot_name: this.telegramBotName
                })
            });

            if (res.ok) {
                alert('✅ Token guardado. Reiniciando bot...');
                await this.restartBot();
            } else {
                const data = await res.json();
                alert('Error: ' + (data.detail || 'No se pudo guardar'));
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    },

    async restartBot() {
        this.botStatus = 'checking';
        try {
            const res = await fetch('/api/settings/telegram/restart-bot', { method: 'POST' });
            const data = await res.json();
            this.botStatus = data.status;

            if (data.status === 'connected') {
                alert('✅ ' + data.message);
            } else {
                alert('⚠️ ' + data.message);
            }
        } catch (e) {
            this.botStatus = 'disconnected';
            alert('Error: ' + e.message);
        }
    },

    async generateLinkCode() {
        try {
            const res = await fetch('/api/settings/notifications/generate-token', { method: 'POST' });
            const data = await res.json();

            if (res.ok) {
                this.linkCode = data.token;
            } else {
                alert('Error: ' + (data.detail || 'No se pudo generar código'));
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    },

    async saveChatId() {
        try {
            const res = await fetch('/api/settings/notifications/save-chat-id', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: this.manualChatId })
            });

            if (res.ok) {
                this.telegramLinked = true;
                this.userChatId = this.manualChatId;
                this.manualChatId = '';
                alert('✅ Chat ID guardado correctamente');
            } else {
                const data = await res.json();
                alert('Error: ' + (data.detail || 'No se pudo guardar'));
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    },

    async toggleAlerts() {
        try {
            const res = await fetch('/api/settings/notifications/toggle-alerts', { method: 'POST' });
            const data = await res.json();

            if (res.ok) {
                this.receiveAlerts = data.receive_alerts;
            }
        } catch (e) {
            console.error('Error toggling alerts:', e);
        }
    },

    async sendTestAlert() {
        try {
            const res = await fetch('/api/settings/notifications/test-alert', { method: 'POST' });

            if (res.ok) {
                alert('✅ Mensaje de prueba enviado a tu Telegram');
            } else {
                const data = await res.json();
                alert('Error: ' + (data.detail || 'No se pudo enviar'));
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }
};
