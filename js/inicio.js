document.addEventListener('DOMContentLoaded', function() {
    // Get the user icon and dropdown elements
    const userIcon = document.getElementById('userIcon');
    const userDropdown = document.getElementById('userDropdown');
    
    // Toggle dropdown when user icon is clicked
    userIcon.addEventListener('click', function(e) {
      e.stopPropagation(); // Prevent event from bubbling up
      userDropdown.classList.toggle('active');
    });
    
    // Close dropdown when clicking anywhere else on the page
    document.addEventListener('click', function(e) {
      if (!userIcon.contains(e.target)) {
        userDropdown.classList.remove('active');
      }
    });
  });