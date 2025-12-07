export const usersModule = {
    users: [],
    userLoadError: '',
    showCreateUserModal: false,
    newUser: { email: '', password: '', is_superuser: false },

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
    }
};
