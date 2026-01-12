// ===== FORMAT RUPIAH =====
function formatRupiah(angka) {
    if (!angka) return '';

    let number_string = angka.replace(/[^,\d]/g, '');
    let split = number_string.split(',');
    let sisa = split[0].length % 3;
    let rupiah = split[0].substr(0, sisa);
    let ribuan = split[0].substr(sisa).match(/\d{3}/gi);

    if (ribuan) {
        let separator = sisa ? '.' : '';
        rupiah += separator + ribuan.join('.');
    }

    return rupiah;
}

// ===== AMBIL ANGKA MURNI =====
function getRawNumber(rupiah) {
    return rupiah.replace(/\D/g, '');
}

// ===== FORMAT RUPIAH DISPLAY =====
function formatRupiahDisplay(number) {
    number = number.toString().replace(/\D/g, '');
    return 'Rp ' + number.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// ===== FORMAT SEMUA TEXT RUPIAH =====
function initRupiahText() {
    document.querySelectorAll('.rupiah-text').forEach(function (el) {
        if (el.innerText.trim() !== '') {
            el.innerText = formatRupiahDisplay(el.innerText);
        }
    });
}

function initRupiahInput() {
    document.querySelectorAll('.rupiah-input').forEach(function (input) {

        input.addEventListener('keyup', function () {
            this.value = 'Rp ' + formatRupiah(this.value);
        });

        input.addEventListener('blur', function () {
            if (this.value === 'Rp ') this.value = '';
        });

    });
}


// UPDATE DOM READY
document.addEventListener('DOMContentLoaded', function () {
    initRupiahInput();
    initRupiahText();
});
