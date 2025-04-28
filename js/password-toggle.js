// Archivo independiente para la funcionalidad del botón de cambiar contraseña
document.addEventListener("DOMContentLoaded", () => {
    console.log("Script de contraseña cargado")
  
    // Obtener referencias a los elementos
    var toggleBtn = document.getElementById("togglePassword")
    var passwordSection = document.getElementById("password-section")
  
    // Verificar si los elementos existen
    if (!toggleBtn) {
      console.error("El botón de cambiar contraseña no se encontró")
      return
    }
  
    if (!passwordSection) {
      console.error("La sección de contraseña no se encontró")
      return
    }
  
    console.log("Elementos encontrados, configurando evento de clic")
  
    // Agregar el evento de clic al botón
    toggleBtn.addEventListener("click", () => {
      console.log("Botón de contraseña clickeado")
  
      // Alternar la clase 'hidden' en la sección de contraseña
      if (passwordSection.classList.contains("hidden")) {
        passwordSection.classList.remove("hidden")
        toggleBtn.textContent = "Ocultar Campos de Contraseña"
        console.log("Mostrando campos de contraseña")
      } else {
        passwordSection.classList.add("hidden")
        toggleBtn.textContent = "Cambiar Contraseña"
        console.log("Ocultando campos de contraseña")
      }
    })
  
    console.log("Evento de clic configurado correctamente")
  })
  