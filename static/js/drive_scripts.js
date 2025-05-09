document.addEventListener('DOMContentLoaded', function() {
    const burgerCheckbox = document.getElementById('burger');
    const sidebar = document.querySelector('.drive-sidebar');
    const mainContent = document.querySelector('.drive-main-content');

    if (burgerCheckbox && sidebar) {
        burgerCheckbox.addEventListener('change', function() {
            // SWAPPED LOGIC:
            if (this.checked) { // Burger is X (visually, menu is 'open', X is to 'close' it)
                // Action: We want the sidebar to BECOME COLLAPSED (closed)
                sidebar.classList.add('collapsed');
                if(mainContent) mainContent.classList.add('sidebar-collapsed'); // Add class to main content
            } else { // Burger is 3-lines (visually, menu is 'closed', 3-lines is to 'open' it)
                // Action: We want the sidebar to BECOME VISIBLE (un-collapsed)
                sidebar.classList.remove('collapsed');
                if(mainContent) mainContent.classList.remove('sidebar-collapsed'); // Remove class from main content
            }
        });

        if (window.innerWidth < 768) {
            burgerCheckbox.checked = true; // So it starts as 'X', and sidebar starts collapsed
            sidebar.classList.add('collapsed');
            if(mainContent) mainContent.classList.add('sidebar-collapsed');
        }
    }
});