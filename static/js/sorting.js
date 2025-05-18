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
            renderPdfPreviews(); // Call PDF renderer when grid view is activated
        } else { // Default to list view
            fileFolderContainer.classList.remove('grid-view-active');
            fileFolderContainer.classList.add('list-view-active');

            gridViewBtn.classList.remove('active');
            listViewBtn.classList.add('active');

            // Decide if sort control is also for list view or should be hidden
            if (gridSortControl) gridSortControl.style.display = 'inline-block';
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
    if (fileFolderContainer) {
        const preferredView = localStorage.getItem('driveViewPreference') || 'list';
        setView(preferredView); // This will call renderPdfPreviews if view is 'grid'
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

            window.location.href = currentUrl.toString();
        });
    });

    // Initialize sort label on page load based on URL parameters
    if (currentSortLabel) {
        const urlParams = new URLSearchParams(window.location.search);
        const sortByParam = urlParams.get('sort_by') || 'name';
        const sortDirParam = urlParams.get('sort_dir') || 'asc';
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

        sortOptions.forEach(opt => {
            if (opt.dataset.sortBy === sortByParam && opt.dataset.sortDir === sortDirParam) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });
    }
    // --- End Sorting Control ---

    // --- PDF.js Preview Rendering Logic ---
function renderPdfPreviews() {
    const pdfCanvases = document.querySelectorAll('canvas.drive-file-card-pdf-preview');
    
    // Check if PDF.js library is loaded and worker is configured
    if (typeof pdfjsLib === 'undefined' || !pdfjsLib.GlobalWorkerOptions.workerSrc) {
        console.error('PDF.js or its worker is not loaded correctly. Ensure pdf.min.js and pdf.worker.min.js are included and workerSrc is set in base_drive_layout.html.');
        // Optionally, provide a fallback UI for each canvas
        pdfCanvases.forEach(canvas => {
            const parentPreviewArea = canvas.parentElement;
            if (parentPreviewArea) {
                let fallbackMsg = parentPreviewArea.querySelector('.pdf-render-fallback');
                if (!fallbackMsg) { // Add fallback message only if not already present
                    fallbackMsg = document.createElement('small');
                    fallbackMsg.className = 'text-muted pdf-render-fallback';
                    fallbackMsg.textContent = 'PDF preview unavailable';
                    parentPreviewArea.appendChild(fallbackMsg);
                    canvas.style.display = 'none'; // Hide canvas if it cannot be rendered
                }
            }
        });
        return;
    }

    pdfCanvases.forEach(async (canvas) => {
        const pdfUrl = canvas.dataset.pdfUrl;
        const spinnerId = canvas.id.replace('pdf-preview-', 'pdf-spinner-');
        const spinnerElement = document.getElementById(spinnerId);
        const parentPreviewArea = canvas.parentElement; // This is .drive-file-card-preview

        if (!pdfUrl) {
            // console.warn('PDF URL not found for canvas:', canvas.id);
            if (spinnerElement) spinnerElement.style.display = 'none';
            return;
        }

        // Avoid re-rendering if already done
        if (canvas.dataset.rendered === 'true') {
            // Ensure canvas is visible if it was previously hidden during a failed load
            if (canvas.style.display === 'none' && parentPreviewArea && !parentPreviewArea.querySelector('.pdf-render-error')) {
                 canvas.style.display = 'block';
            }
            if (spinnerElement) spinnerElement.style.display = 'none';
            return;
        }

        // Clear previous error/fallback messages from this canvas's parent
        if (parentPreviewArea) {
            const existingError = parentPreviewArea.querySelector('.pdf-render-error');
            if (existingError) existingError.remove();
            const existingFallback = parentPreviewArea.querySelector('.pdf-render-fallback');
            if (existingFallback) existingFallback.remove();
        }

        if (spinnerElement) spinnerElement.style.display = 'block';
        canvas.style.display = 'none'; // Hide canvas while loading/rendering

        try {
            const loadingTask = pdfjsLib.getDocument({ 
                url: pdfUrl
                // Consider adding 'withCredentials: true' if your S3 presigned URLs
                // ever require cookies for access, though typically they don't.
            });
            const pdf = await loadingTask.promise;
            const pageNumber = 1; // We are rendering the first page
            const page = await pdf.getPage(pageNumber);

            // Get the desired width from the parent container (.drive-file-card-preview)
            // The parent container should have a fixed height (e.g., 200px from CSS)
            const desiredWidth = parentPreviewArea.clientWidth;
            
            if (desiredWidth <= 0) {
                console.warn("PDF Preview: Parent width is 0 for canvas", canvas.id, "Cannot render.");
                if (spinnerElement) spinnerElement.style.display = 'none';
                // Optionally display a fallback message here if parent width is 0
                if (parentPreviewArea) {
                    let noRenderMsg = parentPreviewArea.querySelector('.pdf-render-fallback');
                    if(!noRenderMsg) {
                        noRenderMsg = document.createElement('small');
                        noRenderMsg.className = 'text-muted pdf-render-fallback';
                        noRenderMsg.textContent = 'Preview area not ready';
                        parentPreviewArea.appendChild(noRenderMsg);
                    }
                }
                return;
            }

            const viewport = page.getViewport({ scale: 1 }); // Get natural viewport at scale 1
            const scale = desiredWidth / viewport.width;     // Calculate scale to fit the container's width
            const scaledViewport = page.getViewport({ scale: scale });

            canvas.height = scaledViewport.height;
            canvas.width = scaledViewport.width;

            // Ensure canvas fits within the 200px height of parentPreviewArea if it's taller
            // This might cause letterboxing if the PDF page is very narrow.
            // The CSS max-height: 100% on the canvas helps contain it within the parent.
            
            const renderContext = {
                canvasContext: canvas.getContext('2d'),
                viewport: scaledViewport
            };
            await page.render(renderContext).promise;
            
            canvas.style.display = 'block'; // Show canvas after rendering
            canvas.dataset.rendered = 'true'; // Mark as rendered

        } catch (reason) {
            console.error('Error rendering PDF:', pdfUrl, reason);
            if (parentPreviewArea) {
                let errorMsg = parentPreviewArea.querySelector('.pdf-render-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('small');
                    errorMsg.className = 'text-danger pdf-render-error';
                    parentPreviewArea.appendChild(errorMsg);
                }
                errorMsg.textContent = 'Preview failed';
            }
        } finally {
            if (spinnerElement) spinnerElement.style.display = 'none';
        }
    });
}
    // --- End PDF.js Preview Rendering Logic ---]

}); 
