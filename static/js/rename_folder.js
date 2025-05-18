document.addEventListener('DOMContentLoaded', function() {

    // --- Rename Folder Modal Functionality ---
    const renameFolderModalElement = document.getElementById('renameFolderModal');
    const renameFolderForm = document.getElementById('renameFolderForm');
    
    // Form fields inside the rename folder modal
    const renameFolderModalFolderIdInput = document.getElementById('renameFolderModalFolderId');
    const renameFolderModalCurrentNameInput = document.getElementById('renameFolderModalCurrentName');
    const renameFolderModalNewNameInput = document.getElementById('renameFolderModalNewName');

    if (renameFolderModalElement) {
        renameFolderModalElement.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            if (!button) return;

            // Extract info from data-* attributes
            const folderId = button.getAttribute('data-folder-id');
            const currentFolderName = button.getAttribute('data-folder-name');

            // Populate the modal's form fields
            if (renameFolderModalFolderIdInput) renameFolderModalFolderIdInput.value = folderId;
            if (renameFolderModalCurrentNameInput) renameFolderModalCurrentNameInput.value = currentFolderName;
            if (renameFolderModalNewNameInput) {
                renameFolderModalNewNameInput.value = currentFolderName; // Pre-fill with current name for editing
                renameFolderModalNewNameInput.focus(); // Focus on the input field
                renameFolderModalNewNameInput.select(); // Select the text
            }
            
            // Set the form action URL dynamically
            if (renameFolderForm && folderId) {
                // Assuming your rename_folder route is in folder_actions_bp and has url_prefix '/folder'
                renameFolderForm.action = `/folder/rename/${folderId}`; 
            }
        });
    }

    if (renameFolderForm) {
        renameFolderForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default browser form submission

            const formData = new FormData(renameFolderForm);
            const actionUrl = renameFolderForm.action;
            const submitButton = renameFolderForm.querySelector('button[type="submit"]');
            const newName = formData.get('new_folder_name').trim();

            if (!newName) {
                alert('New folder name cannot be empty.');
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Renaming...';
            }

            try {
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    body: formData // Contains folder_id (hidden) and new_folder_name
                });

                const result = await response.json(); // Expect JSON response from backend

                if (response.ok && result.success) {
                    alert(result.message || 'Folder renamed successfully!');
                    // Close the modal (Bootstrap 5)
                    const modalInstance = bootstrap.Modal.getInstance(renameFolderModalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload(); // Simple way to refresh the file list
                } else {
                    alert(result.message || 'Failed to rename folder. Please try again.');
                }
            } catch (error) {
                console.error('Error submitting rename folder form:', error);
                alert('An error occurred while renaming the folder.');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Rename';
                }
            }
        });
    }
    // --- End Rename Folder Modal ---

})