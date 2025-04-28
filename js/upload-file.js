document.addEventListener("DOMContentLoaded", () => {
  // Referencias a elementos del DOM
  const fileInput = document.getElementById("file-input")
  const uploadButton = document.getElementById("upload-button")
  uploadButton.addEventListener("click", () => fileInput.click())
  const previewContainer = document.getElementById("preview-container")
  const previewImage = document.getElementById("preview-image")
  const previewName = document.getElementById("preview-name")
  const previewType = document.getElementById("preview-type")
  const previewSize = document.getElementById("preview-size")
  const folderSelect = document.getElementById("folder-select")
  const uploadModal = document.getElementById("upload-modal")
  const openModalBtn = document.querySelector(".custom-file-upload")
  const closeModalBtn = document.getElementById("cancel-button")
  const submitBtn = document.getElementById("submit-button")
  const fileNameInput = document.getElementById("file-name")

  // Abrir el modal al hacer clic en "SUBIR ARCHIVO"
  openModalBtn.addEventListener("click", () => {
    uploadModal.classList.add("active")
  })

  // Cerrar el modal
  closeModalBtn.addEventListener("click", () => {
    uploadModal.classList.remove("active")
    resetForm()
  })

  // Manejar la selección de archivos
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0]
    if (file) {
      displayFilePreview(file)
    }
  })

  // Manejar el arrastre de archivos
  const dropArea = document.getElementById("drop-area")
  ;["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, preventDefaults, false)
  })

  function preventDefaults(e) {
    e.preventDefault()
    e.stopPropagation()
  }
  ;["dragenter", "dragover"].forEach((eventName) => {
    dropArea.addEventListener(eventName, highlight, false)
  })
  ;["dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, unhighlight, false)
  })

  function highlight() {
    dropArea.classList.add("highlight")
  }

  function unhighlight() {
    dropArea.classList.remove("highlight")
  }

  dropArea.addEventListener("drop", handleDrop, false)

  function handleDrop(e) {
    const dt = e.dataTransfer
    const file = dt.files[0]

    if (file) {
      fileInput.files = dt.files
      displayFilePreview(file)
    }
  }

  // Mostrar la previsualización del archivo
  function displayFilePreview(file) {
    // Ocultar el área de arrastrar y mostrar la previsualización
    document.getElementById("drag-text").style.display = "none"
    document.getElementById("drag-icon").style.display = "none"
    previewContainer.style.display = "flex"

    // Establecer el nombre del archivo en el input
    const fileName = file.name
    fileNameInput.value = fileName.substring(0, fileName.lastIndexOf(".")) || fileName

    // Mostrar información del archivo
    previewName.textContent = file.name
    previewType.textContent = file.type || "Desconocido"
    previewSize.textContent = formatFileSize(file.size)

    // Mostrar previsualización según el tipo de archivo
    if (file.type.startsWith("image/")) {
      const reader = new FileReader()
      reader.onload = (e) => {
        previewImage.src = e.target.result
        previewImage.style.display = "block"
      }
      reader.readAsDataURL(file)
    } else {
      // Para archivos que no son imágenes, mostrar un icono según el tipo
      previewImage.style.display = "block"
      if (file.type.includes("pdf")) {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMzIwIDQ2NEgxMjhhODIuOTQgODIuOTQgMCAwIDEtMjYuMjQtNC4wNmwtNjkuMTggMTcuMjlBMTUuOTkgMTUuOTkgMCAwIDEgMCA0NjEuOTFWMTUwLjA5YTE1Ljk5IDE1Ljk5IDAgMCAxIDMyLjU4LTE1LjQybDY1LjM2IDE2LjM0QTgzLjI1IDgzLjI1IDAgMCAxIDEyOCAxNDhIMzIwYTc5Ljk5IDc5Ljk5IDAgMCAxIDgwIDgwdjE1NmE3OS45OSA3OS45OSAwIDAgMS04MCA4MHptMC0yMTZIMTI4djE1NmgxOTJ6Ii8+PC9zdmc+"
      } else if (file.type.includes("word") || file.name.endsWith(".doc") || file.name.endsWith(".docx")) {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em01Ny4xIDMwLjZjLTEwLjQgMTQuOC0yMi45IDI4LjEtMzYuNiAzOS40LTQuOCA0LTkuOCA3LjgtMTQuOSAxMS40djEuMWgxMDEuOXYtNjIuMmgtNTAuNHYxMC4zek0yNTYgMHYxMzZoMTM2TDI1NiAwem0tMTguOCAzMDYuOWMtLjggMS42LTEuOCAzLjUtMi41IDUuMWwtNjQuOSAxNDIuNmgtMzguNWw4MC44LTE3Ni42YzEuMS0yLjQgMi4xLTQuNiAyLjgtNi45bC0uMi0uMWMtMTUuOSA5LjAtMzIuMiAxNS41LTQ5LjkgMTkuMXY0Ny4yYzI5LjgtOC4xIDUyLjQtMjIuMiA2Ni4xLTQxLjdsLjIuMXoiLz48L3N2Zz4="
      } else if (file.type.includes("excel") || file.name.endsWith(".xls") || file.name.endsWith(".xlsx")) {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em0yNS42IDIwNS4zYy0yLjEgNS41LTYuOSA5LjQtMTIuOCA5LjRoLTExLjNjLTMuNSAwLTYuOC0xLjUtOS4xLTQuMWwtNTYuMi02NC4ydi44MWMwIDUuNy00LjYgMTAuMy0xMC4zIDEwLjNoLTExLjNjLTUuNyAwLTEwLjMtNC42LTEwLjMtMTAuM3YtMTEzYzAtNS43IDQuNi0xMC4zIDEwLjMtMTAuM2gxMS4zYzUuNyAwIDEwLjMgNC42IDEwLjMgMTAuM3Y0NS44bDU2LjItNjQuMmMyLjMtMi42IDUuNi00LjEgOS4xLTQuMWgxMS4zYzUuOSAwIDEwLjggMy45IDEyLjggOS40IDEuOCA1LjEtLjIgMTAuOC00LjQgMTQuMWwtNTEuMSA1MS4xIDUxLjEgNTEuMWM0LjEgMy4zIDYuMSA5IDQuMyAxNC4xek0yNTYgMHYxMzZoMTM2TDI1NiAweiIvPjwvc3ZnPg=="
      } else if (file.type.includes("powerpoint") || file.name.endsWith(".ppt") || file.name.endsWith(".pptx")) {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em02My41IDExMy4xbC04Mi4zIDc3LjZjLTguMyA3LjgtMjEuNCAyLjUtMjEuNC04LjVWMjc1SDY0Yy0xNy43IDAtMzItMTQuMy0zMi0zMnYtMzJjMC0xNy43IDE0LjMtMzIgMzItMzJoMTIwdi00My4ybGgyLjVjMS40IDAgMi44LjUgMy45IDEuNGw4Mi4zIDc3LjZjMi4yIDIuMSAzLjMgNSAzLjMgOC4xcy0xLjEgNi0zLjMgOC4xek0yNTYgMHYxMzZoMTM2TDI1NiAweiIvPjwvc3ZnPg=="
      } else if (file.type.includes("text") || file.name.endsWith(".txt")) {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjg4IDI0OHYyOGMwIDYuNi01LjQgMTItMTIgMTJIMTA4YTEyIDEyIDAgMCAxLTEyLTEydi0yOGMwLTYuNiA1LjQtMTIgMTItMTJoMTY4YzYuNiAwIDEyIDUuNCAxMiAxMnptLTEyIDcySDEwOGExMiAxMiAwIDAgMC0xMiAxMnYyOGMwIDYuNiA1LjQgMTIgMTIgMTJoMTY4YzYuNiAwIDEyLTUuNCAxMi0xMnYtMjhjMC02LjYtNS40LTEyLTEyLTEyem0wLTE5MkgxMDhhMTIgMTIgMCAwIDAtMTIgMTJ2MjhjMCA2LjYgNS40IDEyIDEyIDEyaDE2OGM2LjYgMCAxMi01LjQgMTItMTJ2LTI4YzAtNi42LTUuNC0xMi0xMi0xMnpNMzg0IDEzMS45VjQ2NGMwIDI2LjUtMjEuNSA0OC00OCA0OEg0OGMtMjYuNSAwLTQ4LTIxLjUtNDgtNDhWNDhjMC0yNi41IDIxLjUtNDggNDgtNDhoMTU1LjlDMjE0LjkgMCAyMjYuMiA1LjkgMjM0LjggMTYuMkwzNjggMTYyYzYuNiA3LjkgMTAgMTcuNiAxMCAyNy45em0tMTkuNS0uNmMwLTEuOC0uNS0zLjYtMS40LTUuMkwyMjkuNSAyMS44Yy0xLjktMi4xLTQuNi0zLjgtNy40LTMuOEg0OEMyMi43IDE4IDIgMzguNyAyIDY0djM4NGMwIDI1LjMgMjAuNyA0NiA0NiA0NmgyODhjMjUuMyAwIDQ2LTIwLjcgNDYtNDZWMTMxLjl6Ii8+PC9zdmc+"
      } else {
        previewImage.src =
          "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMzY5LjkgOTcuOUwyODYgMTRDMjc3IDUgMjY0LjggLS4xIDI1Mi4xLS4xSDQ4QzIxLjUgMCAwIDIxLjUgMCA0OHY0MTZjMCAyNi41IDIxLjUgNDggNDggNDhoMjg4YzI2LjUgMCA0OC0yMS41IDQ4LTQ4VjEzMS45YzAtMTIuNy01LTI1LTEzLjktMzR6TTMzNiAxNjRoLTEyOFY0MGgxMi4xYzUuNyAwIDExLjEgMi4xIDE1LjEgNi4xbDk4LjggOTguOGM0IDQgNi4xIDkuNCAxLjEgMTUuMXYxMi4xek00OCA0NjRWNDhoMTYwdjEzNmMwIDEzLjMgMTAuNyAyNCAyNCAyNGgxMzZ2MjU2SDQ4eiIvPjwvc3ZnPg=="
      }
    }
  }

  // Formatear el tamaño del archivo
  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes"

    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  // Resetear el formulario
  function resetForm() {
    fileInput.value = ""
    fileNameInput.value = ""
    document.getElementById("drag-text").style.display = "block"
    document.getElementById("drag-icon").style.display = "block"
    previewContainer.style.display = "none"
    previewImage.src = ""
  }

  // Enviar el formulario
  submitBtn.addEventListener("click", (e) => {
    e.preventDefault()

    if (!fileInput.files[0]) {
      alert("Por favor, selecciona un archivo.")
      return
    }

    if (!fileNameInput.value.trim()) {
      alert("Por favor, ingresa un nombre para el archivo.")
      return
    }

    if (!folderSelect.value) {
      alert("Por favor, selecciona una carpeta de destino.")
      return
    }

    // Aquí iría el código para enviar el archivo al servidor
    // Por ahora, solo mostraremos un mensaje de éxito
    alert("Archivo subido correctamente a la carpeta: " + folderSelect.options[folderSelect.selectedIndex].text)

    // Cerrar el modal y resetear el formulario
    uploadModal.classList.remove("active")
    resetForm()
  })
})
