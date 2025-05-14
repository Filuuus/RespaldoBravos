document.addEventListener('DOMContentLoaded', function() {

    // --- Profile View Modal Functionality ---
    const profileViewModalElement = document.getElementById('profileViewModal');
    const profileModalStorageUsedSpan = document.getElementById('profileModalStorageUsed');

    async function fetchAndDisplayStorageInfo() {
        if (!profileModalStorageUsedSpan) return;

        profileModalStorageUsedSpan.textContent = 'Loading...'; // Initial text

        try {
            // Ensure this API route is correctly defined in your api_routes.py
            const response = await fetch('/api/get_user_storage_info'); 
            if (!response.ok) {
                console.error('Failed to fetch storage info:', response.statusText);
                profileModalStorageUsedSpan.textContent = 'Could not load storage info.';
                return;
            }
            const data = await response.json();
            if (data.success) {
                profileModalStorageUsedSpan.textContent = data.storage_used_formatted || '0 B';
            } else {
                profileModalStorageUsedSpan.textContent = data.error || 'Error loading storage info.';
            }
        } catch (error) {
            console.error('Error fetching storage info:', error);
            profileModalStorageUsedSpan.textContent = 'Error connecting to server.';
        }
    }

    if (profileViewModalElement) {
        profileViewModalElement.addEventListener('show.bs.modal', function(event) {

            // Fetch and display storage usage
            fetchAndDisplayStorageInfo();
        });
    }
    // --- End Profile View Modal ---

}); 
