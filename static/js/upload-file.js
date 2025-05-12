// RespaldoBravos/static/js/upload-file.js
document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Element References ---
    const uploadModalElement = document.getElementById("upload-modal");
    const fileInput = document.getElementById("file-input");
    const uploadButton = document.getElementById("upload-button"); // Button inside drop area
    const previewContainer = document.getElementById("preview-container");
    const previewImage = document.getElementById("preview-image");
    const previewName = document.getElementById("preview-name");
    const previewType = document.getElementById("preview-type");
    const previewSize = document.getElementById("preview-size");

    // References for select elements and other inputs in the modal
    // Ensure these IDs match your _upload_file_modal.html
    const categorySelect = document.getElementById("category-select-upload");
    const destinationFolderSelect = document.getElementById("destination-folder-select-upload");
    const descriptionInput = document.getElementById("modal-descripcion-upload");
    const favoriteCheckbox = document.getElementById("modal-favorito-upload");
    const periodoInicioInput = document.getElementById("uploadModalPeriodoInicio");
    const periodoFinInput = document.getElementById("uploadModalPeriodoFin");

    const uploadForm = document.getElementById("upload-form");
    const submitUploadButton = document.getElementById("submit-upload-button");
    // const cancelUploadButton = document.getElementById("cancel-upload-button"); // Bootstrap handles this via data-bs-dismiss

    const fileNameInput = document.getElementById("file-name"); // For custom file name
    const dropArea = document.getElementById("drop-area");

    let bsUploadModalInstance = null;
    if (uploadModalElement) {
        // Initialize Bootstrap modal instance
        bsUploadModalInstance = bootstrap.Modal.getOrCreateInstance(uploadModalElement);
    }

    // --- Event Listener for Bootstrap Modal 'show.bs.modal' event ---
    // This fires when the modal is about to be shown.
    if (uploadModalElement) {
        uploadModalElement.addEventListener('show.bs.modal', function () {
            // console.log("Upload modal 'show.bs.modal' event triggered");
            resetForm(); // Reset form to ensure a clean state for new upload
            populateCategorySelect();
            populateDestinationFolderSelect();
        });

        // Optional: Event listener for when the modal is fully hidden
        uploadModalElement.addEventListener('hidden.bs.modal', function () {
            // console.log("Upload modal 'hidden.bs.modal' event triggered");
            resetForm(); // Reset form after modal is hidden
        });
    }


    // --- Event Listener for "Select file" Button Inside Modal ---
    if (uploadButton && fileInput) {
        uploadButton.addEventListener("click", () => fileInput.click());
    }

    // --- File Input Change Handler ---
    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                displayFilePreview(file);
            }
        });
    }

    // --- Drag and Drop Handlers ---
    if (dropArea) {
        ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        ["dragenter", "dragover"].forEach((eventName) => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        ["dragleave", "drop"].forEach((eventName) => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        dropArea.addEventListener("drop", handleDrop, false);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        if (dropArea) dropArea.classList.add("highlight");
    }

    function unhighlight() {
        if (dropArea) dropArea.classList.remove("highlight");
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        if (file && fileInput) {
            fileInput.files = dt.files; // Assign dropped file to the hidden file input
            displayFilePreview(file);
        }
    }

    // --- Display File Preview Function ---
    function displayFilePreview(file) {
        const dragTextElement = document.getElementById("drag-text");
        const dragIconElement = document.getElementById("drag-icon");

        if (dragTextElement) dragTextElement.style.display = "none";
        if (dragIconElement) dragIconElement.style.display = "none";
        if (previewContainer) previewContainer.style.display = "flex";

        // Set the custom file name input if it's empty, otherwise leave user's input
        if (fileNameInput && fileNameInput.value.trim() === "") {
            const originalFileName = file.name;
            // Set the input to the filename without extension
            fileNameInput.value = originalFileName.substring(0, originalFileName.lastIndexOf(".")) || originalFileName;
        }

        if (previewName) previewName.textContent = file.name;
        if (previewType) previewType.textContent = file.type || "Unknown";
        if (previewSize) previewSize.textContent = formatFileSize(file.size);

        if (previewImage) {
            previewImage.style.display = "block"; // Make sure image tag is visible
            if (file.type.startsWith("image/")) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                };
                reader.readAsDataURL(file);
            } else {
                // Fallback SVG icons for common file types
                // (Ensure these SVGs are correctly formatted and paths are valid if external)
                if (file.type.includes("pdf")) { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMzIwIDQ2NEgxMjhhODIuOTQgODIuOTQgMCAwIDEtMjYuMjQtNC4wNmwtNjkuMTggMTcuMjlBMTUuOTkgMTUuOTkgMCAwIDEgMCA0NjEuOTFWMTUwLjA5YTE1Ljk5IDE1Ljk5IDAgMCAxIDMyLjU4LTE1LjQybDY1LjM2IDE2LjM0QTgzLjI1IDgzLjI1IDAgMCAxIDEyOCAxNDhIMzIwYTc5Ljk5IDc5Ljk5IDAgMCAxIDgwIDgwdjE1NmE3OS45OSA3OS55OSAwIDAgMS04MCA4MHptMC0yMTZIMTI4djE1NmgxOTJ6Ii8+PC9zdmc+"; }
                else if (file.type.includes("word") || file.name.endsWith(".doc") || file.name.endsWith(".docx")) { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em01Ny4xIDMwLjZjLTEwLjQgMTQuOC0yMi45IDI4LjEtMzYuNiAzOS40LTQuOCA0LTkuOCA3LjgtMTQuOSAxMS40djEuMWgxMDEuOXYtNjIuMmgtNTAuNHYxMC4zek0yNTYgMHYxMzZoMTM2TDI1NiAwem0tMTguOCAzMDYuOWMtLjggMS42LTEuOCAzLjUtMi41IDUuMWwtNjQuOSAxNDIuNmgtMzguNWw4MC44LTE3Ni42YzEuMS0yLjQgMi4xLTQuNiAyLjgtNi45bC0uMi0uMWMtMTUuOSA5LjAtMzIuMiAxNS41LTQ5LjkgMTkuMXY0Ny4yYzI5LjgtOC4xIDUyLjQtMjIuMiA2Ni4xLTQxLjdsLjIuMXoiLz48L3N2Zz4="; }
                else if (file.type.includes("excel") || file.name.endsWith(".xls") || file.name.endsWith(".xlsx")) { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em0yNS42IDIwNS4zYy0yLjEgNS41LTYuOSA5LjQtMTIuOCA5LjRoLTExLjNjLTMuNSAwLTYuOC0xLjUtOS4xLTQuMWwtNTYuMi02NC4ydi44MWMwIDUuNy00LjYgMTAuMy0xMC4zIDEwLjNoLTExLjNjLTUuNyAwLTEwLjMtNC42LTEwLjMtMTAuM3YtMTEzYzAtNS43IDQuNi0xMC4zIDEwLjMtMTAuM2gxMS4zYzUuNyAwIDEwLjMgNC42IDEwLjMgMTAuM3Y0NS44bDU2LjItNjQuMmMyLjMtMi42IDUuNi00LjEgOS4xLTQuMWgxMS4zYzUuOSAwIDEwLjggMy45IDEyLjggOS40IDEuOCA1LjEtLjIgMTAuOC00LjQgMTQuMWwtNTEuMSA1MS4xIDUxLjEgNTEuMWM0LjEgMy4zIDYuMSA5IDQuMyAxNC4xek0yNTYgMHYxMzZoMTM2TDI1NiAweiIvPjwvc3ZnPg=="; }
                else if (file.type.includes("powerpoint") || file.name.endsWith(".ppt") || file.name.endsWith(".pptx")) { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjI0IDEzNlYwSDI0QzEwLjcgMCAwIDEwLjcgMCAyNHY0NjRjMCAxMy4zIDEwLjcgMjQgMjQgMjRoMzM2YzEzLjMgMCAyNC0xMC43IDI0LTI0VjE2MEgyNDhjLTEzLjIgMC0yNC0xMC44LTI0LTI0em02My41IDExMy4xbC04Mi4zIDc3LjZjLTguMyA3LjgtMjEuNCAyLjUtMjEuNC04LjVWMjc1SDY0Yy0xNy43IDAtMzItMTQuMy0zMi0zMnYtMzJjMC0xNy43IDE0LjMtMzIgMzItMzJoMTIwdi00My4ybGgyLjVjMS40IDAgMi44LjUgMy45IDEuNGw4Mi4zIDc3LjZjMi4yIDIuMSAzLjMgNSAzLjMgOC4xcy0xLjEgNi0zLjMgOC4xek0yNTYgMHYxMzZoMTM2TDI1NiAweiIvPjwvc3ZnPg=="; }
                else if (file.type.includes("text") || file.name.endsWith(".txt")) { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMjg4IDI0OHYyOGMwIDYuNi01LjQgMTItMTIgMTJIMTA4YTEyIDEyIDAgMCAxLTEyLTEydi0yOGMwLTYuNiA1LjQtMTIgMTItMTJoMTY4YzYuNiAwIDEyIDUuNCAxMiAxMnptLTEyIDcySDEwOGExMiAxMiAwIDAgMC0xMiAxMnYyOGMwIDYuNiA1LjQgMTIgMTIgMTJoMTY4YzYuNiAwIDEyLTUuNCAxMi0xMnYtMjhjMC02LjYtNS40LTEyLTEyLTEyem0wLTE5MkgxMDhhMTIgMTIgMCAwIDAtMTIgMTJ2MjhjMCA2LjYgNS40IDEyIDEyIDEyaDE2OGM2LjYgMCAxMi01LjQgMTItMTJ2LTI4YzAtNi42LTUuNC0xMi0xMi0xMnpNMzg0IDEzMS45VjQ2NGMwIDI2LjUtMjEuNSA0OC00OCA0OEg0OGMtMjYuNSAwLTQ4LTIxLjUtNDgtNDhWNDhjMC0yNi41IDIxLjUtNDggNDgtNDhoMTU1LjlDMjE0LjkgMCAyMjYuMiA1LjkgMjM0LjggMTYuMkwzNjggMTYyYzYuNiA3LjkgMTAgMTcuNiAxMCAyNy45em0tMTkuNS0uNmMwLTEuOC0uNS0zLjYtMS40LTUuMkwyMjkuNSAyMS44Yy0xLjktMi4xLTQuNi0zLjgtNy40LTMuOEg0OEMyMi43IDE4IDIgMzguNyAyIDY0djM4NGMwIDI1LjMgMjAuNyA0NiA0NiA0NmgyODhjMjUuMyAwIDQ2LTIwLjcgNDYtNDZWMTMxLjl6Ii8+PC9zdmc+"; }
                else { previewImage.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzODQgNTEyIj48cGF0aCBmaWxsPSIjZDViMjVjIiBkPSJNMzY5LjkgOTcuOUwyODYgMTRDMjc3IDUgMjY0LjggLS4xIDI1Mi4xLS4xSDQ4QzIxLjUgMCAwIDIxLjUgMCA0OHY0MTZjMCAyNi41IDIxLjUgNDggNDggNDhoMjg4YzI2LjUgMCA0OC0yMS41IDQ4LTQ4VjEzMS45YzAtMTIuNy01LTI1LTEzLjktMzR6TTMzNiAxNjRoLTEyOFY0MGgxMi4xYzUuNyAwIDExLjEgMi4xIDE1LjEgNi4xbDk4LjggOTguOGM0IDQgNi4xIDkuNCAxLjEgMTUuMXYxMi4xek00OCA0NjRWNDhoMTYwdjEzNmMwIDEzLjMgMTAuNyAyNCAyNCAyNGgxMzZ2MjU2SDQ4eiIvPjwvc3ZnPg=="; }
            }
        }
    }

    // --- Format File Size Function ---
    function formatFileSize(bytes) {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    // --- Reset Form Function ---
    function resetForm() {
        if (uploadForm) uploadForm.reset(); // Resets all named form fields to their default values
        if (fileInput) fileInput.value = ""; // Specifically clear the file input

        const dragTextElement = document.getElementById("drag-text");
        const dragIconElement = document.getElementById("drag-icon");
        if (dragTextElement) dragTextElement.style.display = "flex"; // Or its original display
        if (dragIconElement) dragIconElement.style.display = "block"; // Or its original display

        if (previewContainer) previewContainer.style.display = "none";
        if (previewImage) previewImage.src = "";

        // No need to manually reset selects if uploadForm.reset() handles them
        // due to their <option selected> attributes.
        // If not, uncomment and ensure correct default values:
        // if (categorySelect) categorySelect.value = "";
        // if (destinationFolderSelect) destinationFolderSelect.value = "";
    }

    // --- Function to Populate Category Select Dynamically ---
    async function populateCategorySelect() {
        const CATEGORY_API_URL = '/api/get_categories'; // Ensure this route exists in app.py
        if (!categorySelect) return;

        try {
            const response = await fetch(CATEGORY_API_URL);
            if (!response.ok) {
                console.error("Failed to fetch categories:", response.statusText);
                categorySelect.innerHTML = '<option value="" disabled selected>Error loading categories</option>';
                return;
            }
            const categories = await response.json();

            categorySelect.innerHTML = '<option value="" selected>-- Select Category --</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });
        } catch (error) {
            console.error("Error populating categories:", error);
            categorySelect.innerHTML = '<option value="" disabled selected>Error loading categories</option>';
        }
    }

    // --- Function to Populate Destination Folder Select Dynamically ---
    async function populateDestinationFolderSelect() {
        const FOLDER_API_URL = '/api/get_user_folders'; // Ensure this route exists in app.py
        if (!destinationFolderSelect) return;

        try {
            const response = await fetch(FOLDER_API_URL);
            if (!response.ok) {
                console.error("Failed to fetch destination folders:", response.statusText);
                destinationFolderSelect.innerHTML = '<option value="">Error loading folders</option>';
                return;
            }
            const folders = await response.json();

            destinationFolderSelect.innerHTML = '<option value="">-- My Files (Root) --</option>'; // Default to root
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                option.textContent = folder.name;
                destinationFolderSelect.appendChild(option);
            });
        } catch (error) {
            console.error("Error populating destination folders:", error);
            destinationFolderSelect.innerHTML = '<option value="">Error loading folders</option>';
        }
    }

    // --- Submit Form Event Listener (Actual Upload Logic) ---
    if (submitUploadButton && uploadForm && fileInput) {
        submitUploadButton.addEventListener("click", async (e) => {
            e.preventDefault(); // Prevent default form submission

            // Use FormData to gather all named fields from the form
            const formData = new FormData(uploadForm);

            // The 'file' input should be picked up by FormData if it has name="file"
            // and a file is selected. Explicitly check if a file is selected via fileInput.
            if (!fileInput.files || fileInput.files.length === 0) {
                alert("Please select a file.");
                return;
            }
            // FormData should automatically include fileInput.files[0] if input name="file"

            const uploadUrl = uploadForm.dataset.uploadUrl;
            if (!uploadUrl) {
                alert("Error: Upload URL not configured. Ensure the <form> tag has 'data-upload-url'.");
                return;
            }

            submitUploadButton.textContent = "Uploading...";
            submitUploadButton.disabled = true;

            try {
                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    body: formData
                    // Headers are not explicitly set for FormData; browser handles multipart/form-data.
                });

                if (response.ok) {
                    alert("File uploaded! The page will now reload.");
                    if (bsUploadModalInstance) {
                        bsUploadModalInstance.hide(); // Hide Bootstrap modal
                    }
                    // Consider a more targeted update than full reload for better UX later
                    window.location.reload();
                } else {
                    let errorMessage = `Error ${response.status}: ${response.statusText}`;
                    try {
                        const errorData = await response.json(); // Try to parse server error
                        errorMessage = errorData.message || errorMessage;
                    } catch (jsonError) {
                        // Response was not JSON or error structure was different
                    }
                    alert(`Error uploading file: ${errorMessage}`);
                }
            } catch (error) {
                console.error("Upload error (fetch catch):", error);
                alert("Connection or server error during upload.");
            } finally {
                submitUploadButton.textContent = "Upload File";
                submitUploadButton.disabled = false;
                // resetForm() is called by the 'hidden.bs.modal' event now
            }
        });
    }
});
