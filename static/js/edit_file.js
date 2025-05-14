document.addEventListener('DOMContentLoaded', function() {



    // --- Edit File Modal Functionality ---
    const editFileModalElement = document.getElementById('editFileModal');
    const editFileForm = document.getElementById('editFileForm');
    
    const editFileModalDocId = document.getElementById('editFileModalDocId');
    const editFileModalOriginalTitle = document.getElementById('editFileModalOriginalTitle');
    const editFileModalTituloNuevo = document.getElementById('editFileModalTituloNuevo');
    const editFileModalCategoria = document.getElementById('editFileModalCategoria');
    const editFileModalCarpeta = document.getElementById('editFileModalCarpeta');
    const editFileModalDescripcion = document.getElementById('editFileModalDescripcion');
    const editFileModalPeriodoInicio = document.getElementById('editFileModalPeriodoInicio');
    const editFileModalPeriodoFin = document.getElementById('editFileModalPeriodoFin');
    const editFileModalFavorito = document.getElementById('editFileModalFavorito');

    async function populateSelectWithOptions(selectElement, apiUrl, currentId) {
        if (!selectElement) return;
        const defaultOptionText = selectElement.id === 'editFileModalCategoria' ? 'Select Category' : 'Select Folder';
        const rootOptionText = selectElement.id === 'editFileModalCategoria' ? '-- No Category --' : '-- My Files (Root) --';
        
        selectElement.innerHTML = `<option value="" disabled>${defaultOptionText}</option>`;
        const noValueOption = document.createElement('option');
        noValueOption.value = ""; 
        noValueOption.textContent = rootOptionText;
        selectElement.appendChild(noValueOption);

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                console.error(`Failed to fetch options for ${selectElement.id}:`, response.statusText);
                selectElement.innerHTML = `<option value="" disabled selected>Error loading options</option>`;
                return;
            }
            const optionsData = await response.json();
            optionsData.forEach(optionData => {
                const option = document.createElement('option');
                option.value = optionData.id;
                option.textContent = optionData.name;
                selectElement.appendChild(option);
            });
            if (currentId || currentId === 0) { 
                selectElement.value = currentId;
            } else {
                selectElement.value = ""; 
            }
        } catch (error) {
            console.error(`Error populating options for ${selectElement.id}:`, error);
            selectElement.innerHTML = `<option value="" disabled selected>Error loading options</option>`;
        }
    }

    if (editFileModalElement) {
        editFileModalElement.addEventListener('show.bs.modal', async function(event) {
            const button = event.relatedTarget;
            const docId = button.getAttribute('data-doc-id');
            const originalTitle = button.getAttribute('data-doc-title-original');
            const description = button.getAttribute('data-doc-description');
            const categoryId = button.getAttribute('data-doc-category-id');
            const folderId = button.getAttribute('data-doc-folder-id');
            const periodoInicio = button.getAttribute('data-doc-periodo-inicio');
            const periodoFin = button.getAttribute('data-doc-periodo-fin');
            const favorito = button.getAttribute('data-doc-favorito') === 'true';

            if (editFileModalDocId) editFileModalDocId.value = docId;
            if (editFileModalOriginalTitle) editFileModalOriginalTitle.value = originalTitle;
            if (editFileModalTituloNuevo) editFileModalTituloNuevo.value = ''; 
            if (editFileModalDescripcion) editFileModalDescripcion.value = description;
            if (editFileModalPeriodoInicio) editFileModalPeriodoInicio.value = periodoInicio;
            if (editFileModalPeriodoFin) editFileModalPeriodoFin.value = periodoFin;
            if (editFileModalFavorito) editFileModalFavorito.checked = favorito;

            if (editFileForm) editFileForm.action = `/doc/edit/${docId}`;

            await populateSelectWithOptions(editFileModalCategoria, '/api/get_categories', categoryId);
            await populateSelectWithOptions(editFileModalCarpeta, '/api/get_user_folders', folderId);
        });
    }

    if (editFileForm) {
        editFileForm.addEventListener('submit', async function(event) {
            event.preventDefault();
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
                const result = await response.json();
                if (response.ok && result.success) {
                    alert(result.message || 'File updated successfully!');
                    const modalInstance = bootstrap.Modal.getInstance(editFileModalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload();
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
