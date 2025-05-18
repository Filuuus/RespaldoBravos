document.addEventListener('DOMContentLoaded', function() {

    // --- Move File Modal Functionality ---
    const moveFileModalElement = document.getElementById('moveFileModal');
    const moveFileForm = document.getElementById('moveFileForm');
    
    // Form fields inside the move file modal
    const moveFileModalDocIdInput = document.getElementById('moveFileModalDocId');
    const moveFileModalCurrentNameSpan = document.getElementById('moveFileModalCurrentName');
    const moveFileModalDestinationFolderSelect = document.getElementById('moveFileModalDestinationFolder');

    let currentFileOriginalFolderId = null; // To store the original folder ID of the file being moved

    if (moveFileModalElement) {
        moveFileModalElement.addEventListener('show.bs.modal', async function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            if (!button) return;

            // Extract info from data-* attributes
            const docId = button.getAttribute('data-doc-id');
            const docName = button.getAttribute('data-doc-name');
            currentFileOriginalFolderId = button.getAttribute('data-current-folder-id'); // Store this

            // Populate the modal's display and hidden input
            if (moveFileModalDocIdInput) moveFileModalDocIdInput.value = docId;
            if (moveFileModalCurrentNameSpan) moveFileModalCurrentNameSpan.textContent = docName;
            
            // Set the form action URL dynamically
            if (moveFileForm && docId) {
                // Assuming your move_file route is in doc_actions_bp and has url_prefix '/doc'
                moveFileForm.action = `/doc/move_file/${docId}`; 
            }

            // Populate destination folder dropdown
            await populateMoveFileDestinationFolders(currentFileOriginalFolderId);
        });
    }

    async function populateMoveFileDestinationFolders(currentFolderIdToExclude) {
        if (!moveFileModalDestinationFolderSelect) return;

        moveFileModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Loading folders...</option>'; // Loading state

        try {
            const response = await fetch('/api/get_user_folders'); // Your existing API endpoint
            if (!response.ok) {
                console.error("Failed to fetch destination folders for move:", response.statusText);
                moveFileModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Error loading folders</option>';
                return;
            }
            const folders = await response.json();

            moveFileModalDestinationFolderSelect.innerHTML = ''; // Clear loading/error state

            // Add "My Files (Root)" option first
            const rootOption = document.createElement('option');
            rootOption.value = ""; // Empty string for root
            rootOption.textContent = "-- My Files (Root) --";
            if (currentFolderIdToExclude === "" || currentFolderIdToExclude === null) { // Check if current folder is root
                rootOption.disabled = true; // Disable if file is already in root
                rootOption.textContent += " (Current Location)";
            }
            moveFileModalDestinationFolderSelect.appendChild(rootOption);

            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                option.textContent = folder.name;
                // Disable the option if it's the file's current folder
                if (String(folder.id) === String(currentFolderIdToExclude)) {
                    option.disabled = true;
                    option.textContent += " (Current Location)";
                }
                moveFileModalDestinationFolderSelect.appendChild(option);
            });
             // Pre-select a valid option if possible (e.g., root if not current, or first available)
            if (currentFolderIdToExclude !== "" && currentFolderIdToExclude !== null) {
                moveFileModalDestinationFolderSelect.value = ""; // Default to root if not already in root
            }


        } catch (error) {
            console.error("Error populating destination folders for move:", error);
            moveFileModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Error loading folders</option>';
        }
    }

    if (moveFileForm) {
        moveFileForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default browser form submission

            const formData = new FormData(moveFileForm); // Contains doc_id (hidden) and destination_folder
            const actionUrl = moveFileForm.action;
            const submitButton = moveFileForm.querySelector('button[type="submit"]');
            const destinationFolder = formData.get('destination_folder');

            // Basic validation: ensure a destination is selected (unless it's a valid move to root)
            // The backend will do more robust validation.
            if (destinationFolder === null || destinationFolder === undefined) { // null if root, undefined if nothing selected
                 // If destinationFolder is "" (root), it's a valid choice unless the file is already in root.
                if (currentFileOriginalFolderId === "" && destinationFolder === "") {
                     alert('File is already in the root folder.');
                     return;
                } else if (destinationFolder === null || destinationFolder === undefined) { // Should not happen if required
                    alert('Please select a destination folder.');
                    return;
                }
            }


            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Moving...';
            }

            try {
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    body: formData 
                });

                const result = await response.json(); // Expect JSON response from backend

                if (response.ok && result.success) {
                    alert(result.message || 'File moved successfully!');
                    const modalInstance = bootstrap.Modal.getInstance(moveFileModalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload(); // Simple way to refresh the file list
                } else {
                    alert(result.message || 'Failed to move file. Please try again.');
                }
            } catch (error) {
                console.error('Error submitting move file form:', error);
                alert('An error occurred while moving the file.');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Move File';
                }
                currentFileOriginalFolderId = null; // Reset after operation
            }
        });
    }
    // --- End Move File Modal ---

}); // This closes your main DOMContentLoaded listener
