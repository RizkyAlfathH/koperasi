// ================= RUPIAH UTIL =================

// Ambil angka murni (untuk submit & hitung)
function getRawNumber(value) {
    if (!value) return 0;
    return parseInt(value.replace(/\D/g, '')) || 0;
}

// Format angka jadi Rupiah TANPA dobel Rp
function formatRupiahNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// ================= INPUT RUPIAH =================
function initRupiahInput() {
    document.querySelectorAll('.rupiah-input').forEach(function (input) {

        input.addEventListener('input', function () {
            let raw = getRawNumber(this.value);

            if (raw > 0) {
                this.value = 'Rp ' + formatRupiahNumber(raw);
            } else {
                this.value = '';
            }
        });

        input.addEventListener('blur', function () {
            if (this.value === 'Rp ') {
                this.value = '';
            }
        });
    });
}

// ================= TEXT DISPLAY =================
function initRupiahText() {
    document.querySelectorAll('.rupiah-text').forEach(function (el) {
        let raw = getRawNumber(el.innerText);
        if (raw > 0) {
            el.innerText = 'Rp ' + formatRupiahNumber(raw);
        }
    });
}

// ================= DOM READY =================
document.addEventListener('DOMContentLoaded', function () {
    initRupiahInput();
    initRupiahText();
});
