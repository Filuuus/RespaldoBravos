document.addEventListener('DOMContentLoaded', function () {
    // --- Delete Folder Confirmation Logic ---
    const gridViewFolderDeleteForms = document.querySelectorAll('#grid-view-section .delete-folder-form');
    gridViewFolderDeleteForms.forEach(form => {
        const deleteButton = form.querySelector('.delete-folder-btn');
        if (deleteButton) {
            deleteButton.addEventListener('click', function (event) {
                event.preventDefault();
                if (confirm('Are you sure you want to delete this folder? It must be empty.')) {
                    form.submit();
                }
            });
        }
    });

    const listViewFolderDeleteForms = document.querySelectorAll('#list-view-section .delete-folder-form-list');
    listViewFolderDeleteForms.forEach(form => {
        const deleteButton = form.querySelector('.delete-folder-btn-list');
        if (deleteButton) {
            deleteButton.addEventListener('click', function (event) {
                event.preventDefault();
                if (confirm('Are you sure you want to delete this folder? It must be empty.')) {
                    form.submit();
                }
            });
        }
    });
    // --- End Delete Confirmations ---

}); // End of DOMContentLoaded