document.addEventListener("DOMContentLoaded", () => {
    // Manejar el menú desplegable del usuario
    const userIcon = document.getElementById("userIcon")
    const userDropdown = document.getElementById("userDropdown")
  
    userIcon.addEventListener("click", (e) => {
      e.stopPropagation()
      userDropdown.classList.toggle("active")
    })
  
    document.addEventListener("click", (e) => {
      if (!userIcon.contains(e.target)) {
        userDropdown.classList.remove("active")
      }
    })
  
    // Manejar el formulario de actualización
    const updateForm = document.querySelector(".update-form")
    const changePhotoBtn = document.querySelector(".change-photo-btn")
  
    // Simular la carga de datos del usuario
    setTimeout(() => {
      document.getElementById("nombre").value = "Usuario"
      document.getElementById("apellidos").value = "Ejemplo"
      document.getElementById("email").value = "usuario@ejemplo.com"
      document.getElementById("telefono").value = "123456789"
      document.getElementById("institucion").value = "Universidad Ejemplo"
    }, 500)
  
    // Manejar el cambio de foto
    changePhotoBtn.addEventListener("click", () => {
      // Simular la apertura del selector de archivos
      alert("Esta funcionalidad permitiría al usuario seleccionar una nueva foto de perfil.")
    })
  
    // Manejar el envío del formulario
    updateForm.addEventListener("submit", (e) => {
      e.preventDefault()
  
      // Validar contraseñas si se está intentando cambiar
      const newPassword = document.getElementById("new-password").value
      const confirmPassword = document.getElementById("confirm-password").value
  
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
  
      // Simular actualización exitosa
      alert("Datos actualizados correctamente")
      window.location.href = "Inicio.html"
    })
  })
  