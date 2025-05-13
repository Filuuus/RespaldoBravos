document.addEventListener('DOMContentLoaded', function() {

    // --- List/Grid View Toggle Functionality ---
    const fileFolderContainer = document.getElementById('file-folder-container');
    const listViewBtn = document.getElementById('listViewBtn');
    const gridViewBtn = document.getElementById('gridViewBtn');
    const listViewSection = document.getElementById('list-view-section');
    const gridViewSection = document.getElementById('grid-view-section');

    // Function to set the view
    function setView(viewType) {
        if (!fileFolderContainer || !listViewSection || !gridViewSection || !listViewBtn || !gridViewBtn) {
            // console.warn("View toggle elements not all found.");
            return;
        }

        if (viewType === 'grid') {
            fileFolderContainer.classList.remove('list-view-active');
            fileFolderContainer.classList.add('grid-view-active');
            
            listViewBtn.classList.remove('active');
            gridViewBtn.classList.add('active');
            
            // Store preference
            localStorage.setItem('driveViewPreference', 'grid');
        } else { // Default to list view
            fileFolderContainer.classList.remove('grid-view-active');
            fileFolderContainer.classList.add('list-view-active');

            gridViewBtn.classList.remove('active');
            listViewBtn.classList.add('active');

            // Store preference
            localStorage.setItem('driveViewPreference', 'list');
        }
    }

    // Event listeners for buttons
    if (listViewBtn) {
        listViewBtn.addEventListener('click', function() {
            setView('list');
        });
    }

    if (gridViewBtn) {
        gridViewBtn.addEventListener('click', function() {
            setView('grid');
        });
    }

    // On page load, check for stored preference or default to list view
    // This check should only run if we are on a page that has the fileFolderContainer
    if (fileFolderContainer) {
        const preferredView = localStorage.getItem('driveViewPreference');
        if (preferredView === 'grid') {
            setView('grid');
        } else {
            setView('list'); // Default to list view
        }
    }
    // --- End List/Grid View Toggle ---

}); 
