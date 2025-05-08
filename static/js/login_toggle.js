// static/js/login_toggle.js
document.addEventListener('DOMContentLoaded', function() {
    const nipInput = document.getElementById('nip');
    const toggleButton = document.getElementById('toggleNipVisibility');
    const toggleIcon = document.getElementById('toggleNipIcon');

    if (nipInput && toggleButton && toggleIcon) {
        toggleButton.addEventListener('click', function() {
            // Toggle the type attribute
            const type = nipInput.getAttribute('type') === 'password' ? 'text' : 'password';
            nipInput.setAttribute('type', type);

            // Toggle the icon
            if (type === 'password') {
                // Show the eye icon
                toggleIcon.classList.remove('bi-eye-slash-fill');
                toggleIcon.classList.add('bi-eye-fill');
            } else {
                // Show the crossed-out eye icon
                toggleIcon.classList.remove('bi-eye-fill');
                toggleIcon.classList.add('bi-eye-slash-fill');
            }
        });
    } else {
        console.error("Could not find NIP input or toggle button elements.");
    }
});