document.addEventListener('DOMContentLoaded', function () {
  const registroForm = document.getElementById('registro-form');
  const errorMessage = document.getElementById('error-message');
  const registroButton = document.getElementById('registro-button');

  registroForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const nombre = document.getElementById('nombre').value.trim();
    const apellido = document.getElementById('apellido').value.trim();
    const email = document.getElementById('email').value.trim();
    const usuario = document.getElementById('usuario').value.trim();
    const password = document.getElementById('password').value.trim();
    const confirmPassword = document.getElementById('confirm-password').value.trim();

    if (!nombre || !apellido || !email || !usuario || !password || !confirmPassword) {
      showError('Por favor, completa todos los campos');
      return;
    }

    if (password !== confirmPassword) {
      showError('Las contraseñas no coinciden');
      return;
    }

    if (password.length < 6) {
      showError('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError('Por favor, ingresa un correo electrónico válido');
      return;
    }

    registroButton.textContent = 'Procesando...';
    registroButton.disabled = true;
    registroButton.classList.add('button-disabled');

    try {
      const response = await fetch('http://localhost:3000/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          nombre,
          apellido,
          email,
          usuario,
          password
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        alert('Registro exitoso. Por favor, inicia sesión.');
        window.location.href = 'Plogin.html';
      } else {
        showError(data.message || 'Error al registrar');
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
    registroButton.textContent = 'Registrarse';
    registroButton.disabled = false;
    registroButton.classList.remove('button-disabled');
  }
});
document.addEventListener('DOMContentLoaded', function () {
  const registroForm = document.getElementById('registro-form');
  const errorMessage = document.getElementById('error-message');
  const registroButton = document.getElementById('registro-button');

  registroForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const nombre = document.getElementById('nombre').value.trim();
    const apellido = document.getElementById('apellido').value.trim();
    const email = document.getElementById('email').value.trim();
    const usuario = document.getElementById('usuario').value.trim();
    const password = document.getElementById('password').value.trim();
    const confirmPassword = document.getElementById('confirm-password').value.trim();

    if (!nombre || !apellido || !email || !usuario || !password || !confirmPassword) {
      showError('Por favor, completa todos los campos');
      return;
    }

    if (password !== confirmPassword) {
      showError('Las contraseñas no coinciden');
      return;
    }

    if (password.length < 6) {
      showError('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError('Por favor, ingresa un correo electrónico válido');
      return;
    }

    registroButton.textContent = 'Procesando...';
    registroButton.disabled = true;
    registroButton.classList.add('button-disabled');

    try {
      const response = await fetch('http://localhost:3000/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          nombre,
          apellido,
          email,
          usuario,
          password
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        alert('Registro exitoso. Por favor, inicia sesión.');
        window.location.href = 'Plogin.html';
      } else {
        showError(data.message || 'Error al registrar');
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
    registroButton.textContent = 'Registrarse';
    registroButton.disabled = false;
    registroButton.classList.remove('button-disabled');
  }
});
