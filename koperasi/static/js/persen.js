document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".persen-format").forEach(el => {

        // Ambil nilai dari input ATAU text biasa
        let raw = el.value !== undefined 
            ? el.value 
            : el.textContent;

        raw = raw.replace("%", "").replace(",", ".").trim();

        if (!raw) return;

        let num = Number(raw);
        if (isNaN(num)) return;

        let formatted = num.toFixed(2)
            .replace(/\.00$/, "")   // 1.00 -> 1
            .replace(/0$/, "")      // 1.50 -> 1.5
            .replace(".", ",");

        // Kembalikan ke elemen sesuai jenisnya
        if (el.value !== undefined) {
            el.value = formatted + "%";
        } else {
            el.textContent = formatted + "%";
        }
    });
});
