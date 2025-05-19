document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('toggle-theme-btn');
    // Cargar preferencia guardada
    const userTheme = localStorage.getItem('theme');
    if (userTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }

    btn.addEventListener('click', function () {
        document.body.classList.toggle('dark-theme');
        // Guardar preferencia
        const isDark = document.body.classList.contains('dark-theme');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
});