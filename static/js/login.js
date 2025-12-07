const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const errorDiv = document.getElementById('error');
const loadingDiv = document.getElementById('loading');

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    // Hide previous errors
    errorDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    loginButton.disabled = true;

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username: email,
                password: password,
            }),
        });

        if (response.ok) {
            // Login exitoso - redirigir al dashboard
            window.location.href = '/';
        } else {
            const errorData = await response.json();
            showError(errorData.detail || 'Credenciales incorrectas');
        }
    } catch (error) {
        showError('Error de conexión. Por favor intenta de nuevo.');
    } finally {
        loadingDiv.classList.add('hidden');
        loginButton.disabled = false;
    }
});

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}
