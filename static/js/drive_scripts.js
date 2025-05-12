// RespaldoBravos/static/js/drive_scripts.js
document.addEventListener('DOMContentLoaded', function() {
    // --- Burger Menu Sidebar Toggle Logic ---
    const burgerCheckbox = document.getElementById('burger');
    const sidebar = document.querySelector('.drive-sidebar');
    const mainContent = document.querySelector('.drive-main-content');

    if (burgerCheckbox && sidebar) {
        burgerCheckbox.addEventListener('change', function() {
            if (this.checked) { // Burger is X (e.g., menu is now closed/collapsed)
                sidebar.classList.add('collapsed');
                if(mainContent) mainContent.classList.add('sidebar-collapsed');
            } else { // Burger is 3-lines (e.g., menu is now open/visible)
                sidebar.classList.remove('collapsed');
                if(mainContent) mainContent.classList.remove('sidebar-collapsed');
            }
        });


        if (window.innerWidth < 768) {
            burgerCheckbox.checked = false;
             sidebar.classList.add('collapsed'); 
             if(mainContent) mainContent.classList.add('sidebar-collapsed');
        }
    }

    // --- Profile Menu Dropdown Logic ---
    const profileMenuIcon = document.getElementById('profileMenuIcon');
    const profileDropdownMenu = document.getElementById('profileDropdownMenu');

    if (profileMenuIcon && profileDropdownMenu) {
        profileMenuIcon.addEventListener('click', function(event) {
            event.stopPropagation(); // Prevent click from bubbling up to document
            profileDropdownMenu.classList.toggle('active');
        });

        // Close dropdown if clicked outside
        document.addEventListener('click', function(event) {
            if (profileDropdownMenu.classList.contains('active') &&
                !profileMenuIcon.contains(event.target) &&
                !profileDropdownMenu.contains(event.target)) {
                profileDropdownMenu.classList.remove('active');
            }
        });
    }
});