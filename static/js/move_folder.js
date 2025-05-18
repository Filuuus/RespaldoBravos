document.addEventListener('DOMContentLoaded', function() {

    // --- Move Folder Modal Functionality ---
    const moveFolderModalElement = document.getElementById('moveFolderModal');
    const moveFolderForm = document.getElementById('moveFolderForm');
    
    // Form fields inside the move folder modal
    const moveFolderModalFolderIdInput = document.getElementById('moveFolderModalFolderIdInput'); // Hidden input for folder_id_to_move
    const moveFolderModalCurrentNameSpan = document.getElementById('moveFolderModalCurrentName');
    const moveFolderModalDestinationFolderSelect = document.getElementById('moveFolderModalDestinationFolderSelect');

    let folderBeingMovedId = null; // To store the ID of the folder being moved
    let currentParentOfFolderBeingMoved = null; // To store its current parent ID

    function getAllDescendantIds(folders, parentId, allFolders) {
        let descendants = new Set();
        const children = allFolders.filter(f => String(f.id_carpeta_padre) === String(parentId));
        for (const child of children) {
            descendants.add(child.id);
            const subDescendants = getAllDescendantIds(folders, child.id, allFolders); // Recursive call
            subDescendants.forEach(id => descendants.add(id));
        }
        return descendants;
    }


    if (moveFolderModalElement) {
        moveFolderModalElement.addEventListener('show.bs.modal', async function(event) {
            // console.log("Move Folder Modal: 'show.bs.modal' event triggered.");
            const button = event.relatedTarget;
            if (!button) {
                // console.error("Move Folder Modal: Trigger button not found.");
                return;
            }

            folderBeingMovedId = button.getAttribute('data-folder-id');
            const folderName = button.getAttribute('data-folder-name');
            currentParentOfFolderBeingMoved = button.getAttribute('data-current-parent-id'); 

            // console.log("Move Folder Modal: Folder ID:", folderBeingMovedId, "Name:", folderName, "Current Parent ID:", currentParentOfFolderBeingMoved);

            if (moveFolderModalFolderIdInput) moveFolderModalFolderIdInput.value = folderBeingMovedId;
            if (moveFolderModalCurrentNameSpan) moveFolderModalCurrentNameSpan.textContent = folderName;
            
            if (moveFolderForm && folderBeingMovedId) {
                moveFolderForm.action = `/folder/move/${folderBeingMovedId}`; 
                // console.log("Move Folder Modal: Form action set to", moveFolderForm.action);
            }

            // Populate destination folder dropdown
            await populateMoveFolderDestinationFolders(folderBeingMovedId, currentParentOfFolderBeingMoved);
        });
    }

    async function populateMoveFolderDestinationFolders(folderIdToMove, currentParentId) {
        if (!moveFolderModalDestinationFolderSelect) {
            // console.error("Move Folder Modal: Destination folder select element not found.");
            return;
        }

        moveFolderModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Loading folders...</option>';
        // console.log("Move Folder Modal: Populating destination folders. Moving ID:", folderIdToMove, "Current Parent ID:", currentParentId);

        try {
            const response = await fetch('/api/get_user_folders'); 
            if (!response.ok) {
                // ... (error handling as in move file modal) ...
                moveFolderModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Error loading folders</option>';
                return;
            }
            
            const allUserFolders = await response.json(); // This is a flat list: [{id: ..., name: ...}, ...]
            // console.log("Move Folder Modal: Fetched all user folders:", allUserFolders);

            moveFolderModalDestinationFolderSelect.innerHTML = ''; 

            const rootOption = document.createElement('option');
            rootOption.value = ""; // Empty string for root
            rootOption.textContent = "-- My Files (Root) --";
            if (String(currentParentId) === "" || currentParentId === null) { 
                rootOption.disabled = true; 
                rootOption.textContent += " (Current Location)";
            }
            moveFolderModalDestinationFolderSelect.appendChild(rootOption);

            allUserFolders.forEach(folder => {
                // Exclude the folder being moved
                if (String(folder.id) === String(folderIdToMove)) {
                    return; // Skip adding this folder to the dropdown
                }

                const option = document.createElement('option');
                option.value = folder.id;
                option.textContent = folder.name;

                if (String(folder.id) === String(currentParentId)) {
                    option.disabled = true;
                    option.textContent += " (Current Location)";
                }
                moveFolderModalDestinationFolderSelect.appendChild(option);
            });
            
            // Default selection logic
            if (String(currentParentId) !== "" && currentParentId !== null) {
                moveFolderModalDestinationFolderSelect.value = ""; // Default to root if not already in root's parent
            }


        } catch (error) {
            // console.error("Move Folder Modal: Error populating destination folders:", error);
            moveFolderModalDestinationFolderSelect.innerHTML = '<option value="" disabled selected>Error loading folders</option>';
        }
    }

    if (moveFolderForm) {
        moveFolderForm.addEventListener('submit', async function(event) {
            event.preventDefault(); 
            const formData = new FormData(moveFolderForm);
            const actionUrl = moveFolderForm.action;
            const submitButton = moveFolderForm.querySelector('button[type="submit"]');
            
            const selectedOption = moveFolderModalDestinationFolderSelect.options[moveFolderModalDestinationFolderSelect.selectedIndex];

            if (!selectedOption) { 
                alert('Error with folder selection. Please try again.');
                return;
            }
            if (selectedOption.disabled) {
                if (selectedOption.textContent.includes("Loading") || selectedOption.textContent.includes("Error")) {
                    alert('Please wait for folders to load or select a valid folder.');
                } else {
                    alert('Cannot move to the current location or into itself/subfolder. Please select a different folder.');
                }
                return;
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
                const result = await response.json(); 

                if (response.ok && result.success) {
                    alert(result.message || 'Folder moved successfully!');
                    const modalInstance = bootstrap.Modal.getInstance(moveFolderModalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload(); 
                } else {
                    alert(result.message || 'Failed to move folder. Please try again.');
                }
            } catch (error) {
                console.error('Error submitting move folder form:', error);
                alert('An error occurred while moving the folder.');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Move Folder';
                }
                folderBeingMovedId = null;
                currentParentOfFolderBeingMoved = null;
            }
        });
    }
    // --- End Move Folder Modal ---

}); // This closes your main DOMContentLoaded listener
