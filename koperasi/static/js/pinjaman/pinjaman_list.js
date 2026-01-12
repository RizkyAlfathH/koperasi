document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('searchInput');
    const form = document.getElementById('searchForm');

    let typingTimer;
    input.addEventListener('input', function () {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => form.submit(), 600);
    });
});
