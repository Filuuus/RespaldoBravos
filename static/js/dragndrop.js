    document.addEventListener('DOMContentLoaded', function () {
// --- Drag and Drop Files into Folders & Breadcrumbs ---
    let draggedDocId = null; // Variable to store the ID of the document being dragged

    // Function to handle the start of a drag operation
    function handleDragStartFile(event) {
        // 'this' refers to the draggable element (file row or card)
        draggedDocId = this.dataset.docId; 
        
        if (!draggedDocId) {
            console.error("Drag Start: data-doc-id not found on draggable element.");
            event.preventDefault(); // Prevent drag if ID is missing
            return;
        }
        
        event.dataTransfer.setData('text/plain', draggedDocId);
        event.dataTransfer.effectAllowed = 'move'; 
        this.classList.add('dragging-file'); 
        // console.log('Drag Start - Document ID:', draggedDocId);
    }

    // Function to handle when a dragged item is over a potential drop target
    function handleDragOverFolder(event) {
        event.preventDefault(); 
        event.dataTransfer.dropEffect = 'move'; 
        
        if (this.classList.contains('breadcrumb-item') && this.classList.contains('active')) {
            // Do not highlight the active breadcrumb (current folder) as a drop target
            return;
        }
        this.classList.add('drag-over-folder'); 
    }

    // Function to handle when a dragged item enters a potential drop target
    function handleDragEnterFolder(event) {
        if (this.classList.contains('breadcrumb-item') && this.classList.contains('active')) {
            return;
        }
        this.classList.add('drag-over-folder');
    }

    // Function to handle when a dragged item leaves a potential drop target
    function handleDragLeaveFolder(event) {
        this.classList.remove('drag-over-folder');
    }

    // Function to handle the drop event on a folder or breadcrumb
    async function handleDropOnFileOrFolderTarget(event) {
        event.preventDefault(); 
        this.classList.remove('drag-over-folder'); 
        
        const targetFolderId = this.dataset.folderId; 
        const droppedDocIdOnTarget = event.dataTransfer.getData('text/plain');

        // console.log(`Drop Event: Document ID '${droppedDocIdOnTarget}' dropped onto Target Folder ID '${targetFolderId}'`);

        if (!droppedDocIdOnTarget || targetFolderId === undefined) { 
            console.error('Drop error: Missing document ID or target folder ID is undefined.');
            draggedDocId = null; 
            return;
        }
        // Check if the dragged item is already in the target folder
        const draggedItemElement = document.querySelector(`.file-draggable[data-doc-id="${droppedDocIdOnTarget}"]`);
        let currentFolderOfDraggedItem = null;
        if (draggedItemElement && draggedItemElement.dataset.currentFolderId) {
            currentFolderOfDraggedItem = draggedItemElement.dataset.currentFolderId;
        } else if (draggedItemElement && draggedItemElement.closest('tr')) { // Attempt for list view
            // This is a more complex way to get it if not directly on the element.
            // Simpler if data-current-folder-id is added to draggable items.
        }
        
        if (currentFolderOfDraggedItem !== null && String(currentFolderOfDraggedItem) === String(targetFolderId)) {
            // console.log("File is already in the target folder. Move operation aborted by client.");
            draggedDocId = null;
            return; // Don't proceed if it's the same folder
        }


        const moveUrl = `/doc/move_file/${droppedDocIdOnTarget}`; 
        
        const formData = new FormData();
        formData.append('destination_folder', targetFolderId === "" ? "" : targetFolderId); // Empty string for root

        try {
            const response = await fetch(moveUrl, {
                method: 'POST',
                body: formData,
                // headers: { 'X-CSRFToken': getCsrfToken() }, // If using CSRF
            });

            const result = await response.json(); 

            if (response.ok && result.success) {
                alert(result.message || 'File moved successfully!');
                window.location.reload(); 
            } else {
                alert(result.message || 'Failed to move file. Please ensure the destination is valid.');
            }
        } catch (error) {
            console.error('Error during drag and drop move operation:', error);
            alert('An error occurred while attempting to move the file.');
        }
        draggedDocId = null; 
    }
    
    // Function to handle the end of a drag operation (fired on the source element)
    function handleDragEndFile(event) {
        this.classList.remove('dragging-file'); 
        // console.log('Drag End');
        draggedDocId = null; 
    }

    // Function to initialize all drag and drop event listeners
    function initializeDragAndDrop() {
        const draggableFileElements = document.querySelectorAll('.file-draggable');
        // Droppable targets now include folder items in list/grid AND breadcrumb list items
        const droppableTargets = document.querySelectorAll('.folder-drop-target');

        draggableFileElements.forEach(fileElement => {
            fileElement.removeEventListener('dragstart', handleDragStartFile); // Use specific handler name
            fileElement.removeEventListener('dragend', handleDragEndFile);   // Use specific handler name
            
            fileElement.addEventListener('dragstart', handleDragStartFile, false);
            fileElement.addEventListener('dragend', handleDragEndFile, false);
        });

        droppableTargets.forEach(targetElement => {
            // Ensure data-folder-id is present, especially for breadcrumbs
            if (targetElement.dataset.folderId === undefined) {
                // Special case for "My Files" root breadcrumb if data-folder-id wasn't set directly on <li>
                if (targetElement.classList.contains('breadcrumb-item') && targetElement.querySelector('a[href$="/files"]')) {
                    targetElement.dataset.folderId = "";
                } else {
                    // console.warn("Droppable target missing data-folder-id:", targetElement);
                    // return; // Skip attaching listeners if no ID
                }
            }
            // Skip attaching drop listeners to the 'active' breadcrumb item (current folder)
            if (targetElement.classList.contains('breadcrumb-item') && targetElement.classList.contains('active')) {
                return;
            }

            targetElement.removeEventListener('dragenter', handleDragEnterFolder);
            targetElement.removeEventListener('dragover', handleDragOverFolder);
            targetElement.removeEventListener('dragleave', handleDragLeaveFolder);
            targetElement.removeEventListener('drop', handleDropOnFileOrFolderTarget);
            
            targetElement.addEventListener('dragenter', handleDragEnterFolder, false);
            targetElement.addEventListener('dragover', handleDragOverFolder, false);
            targetElement.addEventListener('dragleave', handleDragLeaveFolder, false);
            targetElement.addEventListener('drop', handleDropOnFileOrFolderTarget, false);
        });
        // console.log('Drag and drop listeners initialized/re-initialized.');
    }

    const originalSetViewFunction = window.setView; 
    if (typeof originalSetViewFunction === 'function') {
        window.setView = function(viewType) { 
            originalSetViewFunction(viewType); // Call the original setView
            setTimeout(initializeDragAndDrop, 100); // Re-init after DOM updates
        };
    } else {
        console.warn("Original setView function not found on window. Drag and drop might not re-initialize on view change.");
    }

    // Initial call to set up listeners on page load
    initializeDragAndDrop();
    // --- End Drag and Drop ---

// Ensure this is the closing bracket for your main DOMContentLoaded listener
});
