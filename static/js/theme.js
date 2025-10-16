document.addEventListener('DOMContentLoaded', () => {
    const themeDropdown = document.getElementById('themeDropdown');
    const currentTheme = localStorage.getItem('theme') || 'dark'; // 'dark' is the default

    // Set the initial theme
    document.documentElement.setAttribute('data-theme', currentTheme);
    if (themeDropdown) {
        themeDropdown.textContent = currentTheme.charAt(0).toUpperCase() + currentTheme.slice(1);
    }

    // Add event listeners to dropdown items
    document.querySelectorAll('.theme-select').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const theme = item.getAttribute('data-theme');

            // Apply the theme
            document.documentElement.setAttribute('data-theme', theme);

            // Save theme to localStorage
            localStorage.setItem('theme', theme);

            // Update the dropdown button text
            if (themeDropdown) {
                themeDropdown.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
            }
        });
    });
});