document.addEventListener('DOMContentLoaded', function() {

    // --- List/Grid View Toggle Functionality ---
    const fileFolderContainer = document.getElementById('file-folder-container');
    const listViewBtn = document.getElementById('listViewBtn');
    const gridViewBtn = document.getElementById('gridViewBtn');
    const gridSortControl = document.getElementById('gridSortControl'); // The sort dropdown container

    // Function to set the view
    function setView(viewType) {
        if (!fileFolderContainer || !listViewBtn || !gridViewBtn) {
            // console.warn("View toggle elements not all found for setView.");
            return;
        }

        if (viewType === 'grid') {
            fileFolderContainer.classList.remove('list-view-active');
            fileFolderContainer.classList.add('grid-view-active');
            
            listViewBtn.classList.remove('active');
            gridViewBtn.classList.add('active');
            
            if (gridSortControl) gridSortControl.style.display = 'inline-block'; // Show sort for grid
            localStorage.setItem('driveViewPreference', 'grid');
        } else { // Default to list view
            fileFolderContainer.classList.remove('grid-view-active');
            fileFolderContainer.classList.add('list-view-active');

            gridViewBtn.classList.remove('active');
            listViewBtn.classList.add('active');

            if (gridSortControl) gridSortControl.style.display = 'inline-block'; // Also show for list, or 'none' if only for grid
            localStorage.setItem('driveViewPreference', 'list');
        }
    }

    // Event listeners for view toggle buttons
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
        // setView will also handle the initial display of gridSortControl
        setView(preferredView || 'list'); // Default to list view if no preference
    }
    // --- End List/Grid View Toggle ---


    // --- Sorting Control for Grid View (and potentially List View) ---
    const sortOptions = document.querySelectorAll('.drive-sort-control .sort-option');
    const currentSortLabel = document.getElementById('currentSortLabel');

    sortOptions.forEach(option => {
        option.addEventListener('click', function(event) {
            event.preventDefault();
            const sortBy = this.dataset.sortBy;
            const sortDir = this.dataset.sortDir;
            
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('sort_by', sortBy);
            currentUrl.searchParams.set('sort_dir', sortDir);
            
            // The filter parameters are already part of currentUrl.searchParams
            // if they were in the URL when the page loaded.
            // No need to explicitly add them again unless you are constructing from scratch.

            window.location.href = currentUrl.toString();
        });
    });

    // Initialize sort label on page load based on URL parameters
    if (currentSortLabel) {
        const urlParams = new URLSearchParams(window.location.search);
        const sortByParam = urlParams.get('sort_by') || 'name'; // Default to 'name' if not present
        const sortDirParam = urlParams.get('sort_dir') || 'asc';   // Default to 'asc' if not present
        let initialLabel = 'Name'; 

        if (sortByParam === 'name') {
            initialLabel = `Name (${sortDirParam === 'asc' ? 'A-Z' : 'Z-A'})`;
        } else if (sortByParam === 'date') {
            initialLabel = `Date (${sortDirParam === 'desc' ? 'Newest' : 'Oldest'})`;
        } else if (sortByParam === 'type') {
            initialLabel = `Type (${sortDirParam === 'asc' ? 'A-Z' : 'Z-A'})`;
        } else if (sortByParam === 'size') {
            initialLabel = `Size (${sortDirParam === 'asc' ? 'Smallest' : 'Largest'})`;
        }
        currentSortLabel.textContent = initialLabel;

        // Also set the 'active' class on the correct sort dropdown item
        sortOptions.forEach(opt => {
            if (opt.dataset.sortBy === sortByParam && opt.dataset.sortDir === sortDirParam) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });
    }
    // --- End Sorting Control ---

}); 
