    document.addEventListener('DOMContentLoaded', function () {
    // --- Drag and Drop ---
    let draggedItemId = null;
    let draggedItemType = null; // 'file' or 'folder'
    let draggedItemOriginalParentId = null;

    // --- FILE Drag Handlers ---
    function handleDragStartFile(event) {
        this.classList.add('dragging-item', 'dragging-file');
        event.dataTransfer.effectAllowed = 'move';
        
        draggedItemType = 'file';
        draggedItemId = this.dataset.docId;
        draggedItemOriginalParentId = this.dataset.currentFolderId;

        if (!draggedItemId) {
            console.error("Drag Start File: data-doc-id not found.");
            event.preventDefault();
            return;
        }
        
        event.dataTransfer.setData('text/item-id', draggedItemId);
        event.dataTransfer.setData('text/item-type', 'file');
        event.dataTransfer.setData('text/item-original-parent-id', draggedItemOriginalParentId || "");
        // console.log('Drag Start File:', draggedItemId);
    }

    function handleDragEndFile(event) {
        this.classList.remove('dragging-item', 'dragging-file');
        // Reset global state after any drag operation ends
        draggedItemId = null;
        draggedItemType = null;
        draggedItemOriginalParentId = null;
    }

    // --- FOLDER Drag Handlers ---
    function handleDragStartFolder(event) {
        this.classList.add('dragging-item', 'dragging-folder');
        event.dataTransfer.effectAllowed = 'move';

        draggedItemType = 'folder';
        draggedItemId = this.dataset.folderId;
        draggedItemOriginalParentId = this.dataset.currentParentId;

        if (!draggedItemId) {
            console.error("Drag Start Folder: data-folder-id not found.");
            event.preventDefault();
            return;
        }

        event.dataTransfer.setData('text/item-id', draggedItemId);
        event.dataTransfer.setData('text/item-type', 'folder');
        event.dataTransfer.setData('text/item-original-parent-id', draggedItemOriginalParentId || "");
        // console.log('Drag Start Folder:', draggedItemId);
    }

    function handleDragEndFolder(event) {
        this.classList.remove('dragging-item', 'dragging-folder');
        // Reset global state
        draggedItemId = null;
        draggedItemType = null;
        draggedItemOriginalParentId = null;
    }

    // --- COMMON Drop Target Handlers (for Folders and Breadcrumbs) ---
    function handleDragOverTarget(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        
        const targetFolderId = this.dataset.folderId;
        let canDrop = true;

        // Prevent dropping on the active breadcrumb (current folder view)
        if (this.classList.contains('breadcrumb-item') && this.classList.contains('active')) {
            canDrop = false;
        }
        // Prevent dropping an item into its current location
        else if (String(draggedItemOriginalParentId) === String(targetFolderId)) {
            canDrop = false;
        }
        // Prevent dropping a folder onto itself
        else if (draggedItemType === 'folder' && String(draggedItemId) === String(targetFolderId)) {
            canDrop = false;
        }
        // Backend will handle more complex cycle detection for folders.

        if (canDrop) {
            this.classList.add('drag-over-folder');
        } else {
            this.classList.remove('drag-over-folder');
            event.dataTransfer.dropEffect = 'none';
        }
    }

    function handleDragEnterTarget(event) {
        // Similar logic to handleDragOver for adding class
        const targetFolderId = this.dataset.folderId;
        let canHighlight = true;
        if (this.classList.contains('breadcrumb-item') && this.classList.contains('active')) {
            canHighlight = false;
        } else if (String(draggedItemOriginalParentId) === String(targetFolderId)) {
            canHighlight = false;
        } else if (draggedItemType === 'folder' && String(draggedItemId) === String(targetFolderId)) {
            canHighlight = false;
        }

        if (canHighlight) {
            this.classList.add('drag-over-folder');
        }
    }

    function handleDragLeaveTarget(event) {
        this.classList.remove('drag-over-folder');
    }

    async function handleDropOnTarget(event) {
        event.preventDefault();
        this.classList.remove('drag-over-folder');
        
        const targetParentFolderId = this.dataset.folderId;
        // Retrieve data set in dragstart from the event, not global state
        const droppedItemIdFromTransfer = event.dataTransfer.getData('text/item-id');
        const droppedItemTypeFromTransfer = event.dataTransfer.getData('text/item-type');
        const droppedItemOriginalParentFromTransfer = event.dataTransfer.getData('text/item-original-parent-id');

        if (!droppedItemIdFromTransfer || targetParentFolderId === undefined || !droppedItemTypeFromTransfer) {
            console.error('Drop error: Missing item ID, target folder ID, or item type from dataTransfer.');
            return;
        }
        
        // Final client-side validation before sending to backend
        if (droppedItemTypeFromTransfer === 'folder') {
            if (String(droppedItemIdFromTransfer) === String(targetParentFolderId)) {
                alert("Cannot move a folder into itself."); return;
            }
            if (String(droppedItemOriginalParentFromTransfer) === String(targetParentFolderId)) {
                alert("Folder is already in that location."); return;
            }
        } else if (droppedItemTypeFromTransfer === 'file') {
            if (String(droppedItemOriginalParentFromTransfer) === String(targetParentFolderId)) {
                alert("File is already in that folder."); return;
            }
        }
        
        let moveUrl = '';
        const formData = new FormData();
        formData.append('destination_folder', targetParentFolderId === "" ? "" : targetParentFolderId);

        if (droppedItemTypeFromTransfer === 'file') {
            moveUrl = `/doc/move_file/${droppedItemIdFromTransfer}`;
        } else if (droppedItemTypeFromTransfer === 'folder') {
            moveUrl = `/folder/move/${droppedItemIdFromTransfer}`;
        } else {
            console.error("Unknown item type dropped:", droppedItemTypeFromTransfer);
            return;
        }

        try {
            const response = await fetch(moveUrl, {
                method: 'POST',
                body: formData,
            });
            const result = await response.json(); 

            if (response.ok && result.success) {
                alert(result.message || `${droppedItemTypeFromTransfer.charAt(0).toUpperCase() + droppedItemTypeFromTransfer.slice(1)} moved successfully!`);
                window.location.reload(); 
            } else {
                alert(result.message || `Failed to move ${droppedItemTypeFromTransfer}.`);
            }
        } catch (error) {
            console.error(`Error during drag and drop move for ${droppedItemTypeFromTransfer}:`, error);
            alert(`An error occurred while attempting to move the ${droppedItemTypeFromTransfer}.`);
        }
    }
    
    // Function to initialize all drag and drop event listeners
    function initializeDragAndDrop() {
        const draggableFileElements = document.querySelectorAll('.file-draggable');
        const draggableFolderElements = document.querySelectorAll('.folder-draggable');
        const droppableTargets = document.querySelectorAll('.folder-drop-target'); 

        draggableFileElements.forEach(item => {
            item.removeEventListener('dragstart', handleDragStartFile); 
            item.removeEventListener('dragend', handleDragEndFile);   
            item.addEventListener('dragstart', handleDragStartFile, false);
            item.addEventListener('dragend', handleDragEndFile, false);
        });

        draggableFolderElements.forEach(item => {
            item.removeEventListener('dragstart', handleDragStartFolder);
            item.removeEventListener('dragend', handleDragEndFolder);
            item.addEventListener('dragstart', handleDragStartFolder, false);
            item.addEventListener('dragend', handleDragEndFolder, false);
        });

        droppableTargets.forEach(targetElement => {
            if (targetElement.dataset.folderId === undefined) {
                if (targetElement.classList.contains('breadcrumb-item') && 
                    targetElement.firstElementChild && 
                    targetElement.firstElementChild.tagName === 'A' &&
                    targetElement.firstElementChild.getAttribute('href') &&
                    targetElement.firstElementChild.getAttribute('href').endsWith("/files") && // More specific check for root
                    !targetElement.firstElementChild.getAttribute('href').includes("/files/")) { 
                    targetElement.dataset.folderId = ""; 
                }
            }
            
            if (targetElement.classList.contains('breadcrumb-item') && targetElement.classList.contains('active')) {
                return; 
            }

            targetElement.removeEventListener('dragenter', handleDragEnterTarget);
            targetElement.removeEventListener('dragover', handleDragOverTarget);
            targetElement.removeEventListener('dragleave', handleDragLeaveTarget);
            targetElement.removeEventListener('drop', handleDropOnTarget);
            
            targetElement.addEventListener('dragenter', handleDragEnterTarget, false);
            targetElement.addEventListener('dragover', handleDragOverTarget, false);
            targetElement.addEventListener('dragleave', handleDragLeaveTarget, false);
            targetElement.addEventListener('drop', handleDropOnTarget, false);
        });
        // console.log('Drag and drop listeners initialized/re-initialized.');
    }

    // --- Integration with View Toggle (setView function) ---
    const fileFolderContainerForDd = document.getElementById('file-folder-container'); 
    if (fileFolderContainerForDd) { 
        const originalSetViewFunction = window.setView; 
        if (typeof originalSetViewFunction === 'function') {
            window.setView = function(viewType) { 
                originalSetViewFunction(viewType);
                setTimeout(initializeDragAndDrop, 150); 
            };
            const preferredView = localStorage.getItem('driveViewPreference') || 'list';
            setView(preferredView);
        } else {
            initializeDragAndDrop();
        }
    } else {
        const breadcrumbNav = document.querySelector('.drive-breadcrumb-nav');
        if (breadcrumbNav) {
            initializeDragAndDrop();
        }
    }
    // --- End Drag and Drop ---

// Ensure this is the closing bracket for your main DOMContentLoaded listener
});