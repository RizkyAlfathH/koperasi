document.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById("global-loader");

    // Hilangkan loader setelah halaman siap
    window.addEventListener("load", () => {
        setTimeout(() => {
            loader.classList.add("hide");
        }, 300);
    });

    // Tampilkan loader saat klik link
    document.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", e => {
            const href = link.getAttribute("href");

            if (
                href &&
                !href.startsWith("#") &&
                !href.startsWith("javascript") &&
                !link.hasAttribute("target")
            ) {
                loader.classList.remove("hide");
            }
        });
    });

    // Tampilkan loader saat submit form
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", () => {
            loader.classList.remove("hide");
        });
    });
});
