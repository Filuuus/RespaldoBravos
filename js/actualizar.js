// Esperar a que el DOM esté completamente cargado
window.onload = () => {
  console.log("Ventana cargada completamente")

  // 1. Funcionalidad del menú desplegable
  const userIcon = document.getElementById("userIcon")
  const userDropdown = document.getElementById("userDropdown")

  if (userIcon && userDropdown) {
    userIcon.onclick = (e) => {
      e.stopPropagation()
      userDropdown.classList.toggle("active")
      console.log("Menú desplegable toggled")
    }

    document.onclick = (e) => {
      if (!userIcon.contains(e.target)) {
        userDropdown.classList.remove("active")
      }
    }
  }

  // 2. Funcionalidad de cambio de foto de perfil
  const photoUpload = document.getElementById("photoUpload")
  const profileImage = document.getElementById("profileImage")

  if (photoUpload && profileImage) {
    photoUpload.onchange = function () {
      console.log("Archivo seleccionado")
      const file = this.files[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (e) => {
          profileImage.src = e.target.result
          console.log("Imagen actualizada")
        }
        reader.readAsDataURL(file)
      }
    }
  }

  // 3. Funcionalidad del botón de cambiar contraseña
  const togglePasswordBtn = document.getElementById("togglePassword")
  const passwordSection = document.getElementById("password-section")

  if (togglePasswordBtn && passwordSection) {
    console.log("Elementos de contraseña encontrados")

    togglePasswordBtn.onclick = function () {
      console.log("Botón de contraseña clickeado")

      if (passwordSection.classList.contains("hidden")) {
        passwordSection.classList.remove("hidden")
        this.textContent = "Ocultar Campos de Contraseña"
        console.log("Mostrando campos de contraseña")
      } else {
        passwordSection.classList.add("hidden")
        this.textContent = "Cambiar Contraseña"
        console.log("Ocultando campos de contraseña")
      }
    }
  }

  // 4. Cargar datos de usuario simulados
  setTimeout(() => {
    document.getElementById("nombre").value = "Usuario"
    document.getElementById("apellidos").value = "Ejemplo"
    document.getElementById("institucion").value = "Universidad Ejemplo"
    document.getElementById("grado-estudios").value = "licenciatura"
    document.getElementById("perfil-profesional").value =
      "Profesional con experiencia en desarrollo de software y gestión de proyectos."
    document.getElementById("experiencia").value = "5 años de experiencia en desarrollo web y aplicaciones móviles."
    document.getElementById("habilidades").value = "JavaScript, HTML, CSS, React, Node.js, Gestión de proyectos"
  }, 500)

  // 5. Manejar el envío del formulario
  const updateForm = document.querySelector(".update-form")

  if (updateForm) {
    updateForm.onsubmit = (e) => {
      e.preventDefault()
      console.log("Formulario enviado")

      // Validar contraseñas si la sección está visible
      if (!passwordSection.classList.contains("hidden")) {
        const newPassword = document.getElementById("new-password").value
        const confirmPassword = document.getElementById("confirm-password").value
        const currentPassword = document.getElementById("password").value

        if (!currentPassword) {
          alert("Debes ingresar tu contraseña actual para confirmar los cambios")
          return
        }

        if (newPassword || confirmPassword) {
          if (newPassword !== confirmPassword) {
            alert("Las contraseñas no coinciden")
            return
          }

          if (newPassword.length < 6) {
            alert("La contraseña debe tener al menos 6 caracteres")
            return
          }
        }
      }

      // Simulación de actualización exitosa
      alert("Datos actualizados correctamente")
      window.location.href = "Inicio.html"
    }
  }
}
