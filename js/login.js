document.addEventListener('DOMContentLoaded', function () {
  const loginForm = document.getElementById('login-form');
  const errorMessage = document.getElementById('error-message');
  const loginButton = document.getElementById('login-button');

  loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!username || !password) {
      showError('Por favor, completa todos los campos');
      return;
    }

    loginButton.textContent = 'Cargando...';
    loginButton.disabled = true;
    loginButton.classList.add('button-disabled');

    try {
      const response = await fetch('http://localhost:3000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Guardar token y usuario
        localStorage.setItem('token', data.token);
        localStorage.setItem('username', username);

        // Redirigir al inicio
        window.location.href = 'inicio.html';
      } else {
        showError(data.message || 'Usuario o contraseña incorrectos');
        resetButton();
      }
    } catch (error) {
      showError('Error del servidor, intenta más tarde');
      resetButton();
    }
  });

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
      errorMessage.style.display = 'none';
    }, 3000);
  }

  function resetButton() {
    loginButton.textContent = 'Iniciar Sesión';
    loginButton.disabled = false;
    loginButton.classList.remove('button-disabled');
  }

  // Si ya hay token, redirigir
  if (localStorage.getItem('token')) {
    window.location.href = 'inicio.html';
  }
});
