document.addEventListener('DOMContentLoaded', function() {



    // --- Edit File Modal Functionality ---
    const editFileModalElement = document.getElementById('editFileModal');
    const editFileForm = document.getElementById('editFileForm');

    // Form fields inside the edit modal
    const editFileModalDocId = document.getElementById('editFileModalDocId');
    const editFileModalOriginalTitle = document.getElementById('editFileModalOriginalTitle');
    const editFileModalTituloNuevo = document.getElementById('editFileModalTituloNuevo');
    const editFileModalCategoria = document.getElementById('editFileModalCategoria');
    const editFileModalCarpeta = document.getElementById('editFileModalCarpeta');
    const editFileModalDescripcion = document.getElementById('editFileModalDescripcion');
    const editFileModalPeriodoInicio = document.getElementById('editFileModalPeriodoInicio');
    const editFileModalPeriodoFin = document.getElementById('editFileModalPeriodoFin');
    const editFileModalFavorito = document.getElementById('editFileModalFavorito');

    // Function to populate select dropdowns (generic for categories and folders)
    async function populateSelectWithOptions(selectElement, apiUrl, currentId) {
        if (!selectElement) return;

        // Add a default "loading" or "select" option
        const defaultOptionText = selectElement.id === 'editFileModalCategoria' ? 'Seleccionar categoría' : 'Seleccionar carpeta';
        const rootOptionText = selectElement.id === 'editFileModalCategoria' ? '-- Sin Categoría --' : '-- Mis Archivos (Raíz) --';
        
        selectElement.innerHTML = `<option value="" disabled>${defaultOptionText}</option>`;
        
        const noValueOption = document.createElement('option');
        noValueOption.value = ""; // Value for no category or root folder
        noValueOption.textContent = rootOptionText;
        selectElement.appendChild(noValueOption);

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                console.error(`Failed to fetch options for ${selectElement.id}:`, response.statusText);
                selectElement.innerHTML = `<option value="" disabled selected>Error al cargar opciones</option>`;
                return;
            }
            const optionsData = await response.json();

            optionsData.forEach(optionData => {
                const option = document.createElement('option');
                option.value = optionData.id;
                option.textContent = optionData.name;
                if (currentId && String(optionData.id) === String(currentId)) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
             // Ensure the currentId value is correctly selected after populating
            if (currentId) {
                selectElement.value = currentId;
            } else {
                selectElement.value = ""; // Default to "No Category" or "Root" if no currentId
            }

        } catch (error) {
            console.error(`Error populating options for ${selectElement.id}:`, error);
            selectElement.innerHTML = `<option value="" disabled selected>Error al cargar opciones</option>`;
        }
    }


    if (editFileModalElement) {
        editFileModalElement.addEventListener('show.bs.modal', async function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;

            // Extract info from data-* attributes
            const docId = button.getAttribute('data-doc-id');
            const originalTitle = button.getAttribute('data-doc-title-original');
            const description = button.getAttribute('data-doc-description');
            const categoryId = button.getAttribute('data-doc-category-id');
            const folderId = button.getAttribute('data-doc-folder-id');
            const periodoInicio = button.getAttribute('data-doc-periodo-inicio');
            const periodoFin = button.getAttribute('data-doc-periodo-fin');
            const favorito = button.getAttribute('data-doc-favorito') === 'true';

            // Populate the modal's form fields
            if (editFileModalDocId) editFileModalDocId.value = docId;
            if (editFileModalOriginalTitle) editFileModalOriginalTitle.value = originalTitle;
            if (editFileModalTituloNuevo) editFileModalTituloNuevo.value = ''; // Clear new title field initially
            if (editFileModalDescripcion) editFileModalDescripcion.value = description;
            if (editFileModalPeriodoInicio) editFileModalPeriodoInicio.value = periodoInicio;
            if (editFileModalPeriodoFin) editFileModalPeriodoFin.value = periodoFin;
            if (editFileModalFavorito) editFileModalFavorito.checked = favorito;

            // Set the form action URL dynamically
            if (editFileForm) editFileForm.action = `/edit/${docId}`; // Assumes your edit route is /edit/<doc_id>

            // Populate category and folder dropdowns
            // Ensure your API endpoints are correct
            await populateSelectWithOptions(editFileModalCategoria, '/api/get_categories', categoryId);
            await populateSelectWithOptions(editFileModalCarpeta, '/api/get_user_folders', folderId);
        });
    }

    if (editFileForm) {
        editFileForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default browser form submission

            const formData = new FormData(editFileForm);
            const actionUrl = editFileForm.action;
            const submitButton = editFileForm.querySelector('button[type="submit"]');

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Saving...';
            }

            try {
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json(); // Expect JSON response from backend

                if (response.ok && result.success) {
                    alert(result.message || 'File updated successfully!');
                    // Close the modal (Bootstrap 5)
                    const modalInstance = bootstrap.Modal.getInstance(editFileModalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload(); // Simple way to refresh the file list
                } else {
                    alert(result.message || 'Failed to update file. Please try again.');
                }
            } catch (error) {
                console.error('Error submitting edit form:', error);
                alert('An error occurred while saving changes.');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Save Changes';
                }
            }
        });
    }
});
