document.addEventListener('DOMContentLoaded', function() {

    // --- List/Grid View Toggle Functionality ---
    const fileFolderContainer = document.getElementById('file-folder-container');
    const listViewBtn = document.getElementById('listViewBtn');
    const gridViewBtn = document.getElementById('gridViewBtn');
    const gridSortControl = document.getElementById('gridSortControl');

    function setView(viewType) {
        if (!fileFolderContainer || !listViewBtn || !gridViewBtn) { return; }
        if (viewType === 'grid') {
            fileFolderContainer.classList.remove('list-view-active');
            fileFolderContainer.classList.add('grid-view-active');
            listViewBtn.classList.remove('active');
            gridViewBtn.classList.add('active');
            if (gridSortControl) gridSortControl.style.display = 'inline-block';
            localStorage.setItem('driveViewPreference', 'grid');
            renderPdfPreviews(); // Call PDF renderer specifically when grid view is activated
        } else { 
            fileFolderContainer.classList.remove('grid-view-active');
            fileFolderContainer.classList.add('list-view-active');
            gridViewBtn.classList.remove('active');
            listViewBtn.classList.add('active');
            if (gridSortControl) gridSortControl.style.display = 'inline-block';
            localStorage.setItem('driveViewPreference', 'list');
            // PDFs are typically not shown in list view, but if they were, call renderPdfPreviews() here too.
        }
    }

    if (listViewBtn) { listViewBtn.addEventListener('click', function() { setView('list'); }); }
    if (gridViewBtn) { gridViewBtn.addEventListener('click', function() { setView('grid'); }); }

    if (fileFolderContainer) { // This block is specific to drive_home.html
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
        
        if (typeof pdfjsLib === 'undefined' || !pdfjsLib.GlobalWorkerOptions.workerSrc) {
            console.error('PDF.js or its worker is not loaded correctly.');
            pdfCanvases.forEach(canvas => { /* ... (fallback UI as before) ... */ });
            return;
        }

        if (pdfCanvases.length === 0) {
            // console.log("No PDF canvases found to render on this page.");
            return;
        }
        // console.log(`Found ${pdfCanvases.length} PDF canvases to render.`);

        pdfCanvases.forEach(async (canvas) => {
            const pdfUrl = canvas.dataset.pdfUrl;
            const spinnerId = canvas.id.replace('pdf-preview-', 'pdf-spinner-');
            const spinnerElement = document.getElementById(spinnerId);
            const parentPreviewArea = canvas.parentElement;

            if (!pdfUrl) { if (spinnerElement) spinnerElement.style.display = 'none'; return; }
            if (canvas.dataset.rendered === 'true') { 
                if (canvas.style.display === 'none' && parentPreviewArea && !parentPreviewArea.querySelector('.pdf-render-error')) {
                     canvas.style.display = 'block';
                }
                if (spinnerElement) spinnerElement.style.display = 'none';
                return; 
            }

            if (parentPreviewArea) { /* ... (clear previous error/fallback messages) ... */ }
            if (spinnerElement) spinnerElement.style.display = 'block';
            canvas.style.display = 'none';

            try {
                const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
                const pdf = await loadingTask.promise;
                const page = await pdf.getPage(1);
                const desiredWidth = parentPreviewArea.clientWidth;
                
                if (desiredWidth <= 0) { /* ... (handle parent width 0) ... */ return; }

                const viewport = page.getViewport({ scale: 1 });
                const scale = desiredWidth / viewport.width;
                const scaledViewport = page.getViewport({ scale: scale });
                canvas.height = scaledViewport.height;
                canvas.width = scaledViewport.width;
                
                const renderContext = { canvasContext: canvas.getContext('2d'), viewport: scaledViewport };
                await page.render(renderContext).promise;
                
                canvas.style.display = 'block';
                canvas.dataset.rendered = 'true';
            } catch (reason) { /* ... (error handling as before) ... */ } 
            finally { if (spinnerElement) spinnerElement.style.display = 'none'; }
        });
    }
    window.renderPdfPreviews = renderPdfPreviews; // Expose the function globally 
    // --- End PDF.js Preview Rendering Logic ---

}); 
