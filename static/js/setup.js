const setupForm = document.getElementById('setupForm');
const setupButton = document.getElementById('setupButton');
const errorDiv = document.getElementById('error');
const successDiv = document.getElementById('success');
const loadingDiv = document.getElementById('loading');

setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    // Validate passwords match
    if (password !== confirmPassword) {
        showError('Las contraseñas no coinciden');
        return;
    }

    // Hide previous messages
    errorDiv.classList.add('hidden');
    successDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    setupButton.disabled = true;

    try {
        const response = await fetch('/api/setup/create-admin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
            }),
        });

        if (response.ok) {
            showSuccess('¡Administrador creado exitosamente! Redirigiendo al login...');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            const errorData = await response.json();
            showError(errorData.detail || 'Error al crear el administrador');
        }
    } catch (error) {
        showError('Error de conexión. Por favor intenta de nuevo.');
    } finally {
        loadingDiv.classList.add('hidden');
        setupButton.disabled = false;
    }
});

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function showSuccess(message) {
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
}
