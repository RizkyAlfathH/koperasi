/* ===== KOPASMEN SWAL THEME ===== */
const kopasSwal = Swal.mixin({
    customClass: {
        popup:             'kopas-popup',
        title:             'kopas-title',
        htmlContainer:     'kopas-text',
        confirmButton:     'kopas-btn-confirm',
        cancelButton:      'kopas-btn-cancel',
        icon:              'kopas-icon',
        loader:            'kopas-loader',
    },
    buttonsStyling: false,
    background: '#ffffff',
    color: '#1a1a1a',
});

/* ===== INJECT STYLE ===== */
(function injectKopasStyle() {
    const style = document.createElement('style');
    style.textContent = `
        /* Popup card */
        .kopas-popup {
            border-radius: 20px !important;
            padding: 32px 28px 28px !important;
            box-shadow: 0 8px 40px rgba(0,0,0,0.13) !important;
            font-family: inherit !important;
        }

        /* Title */
        .kopas-title {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: #1a1a1a !important;
            margin-bottom: 8px !important;
        }

        /* Body text */
        .kopas-text {
            font-size: 0.95rem !important;
            color: #555 !important;
        }

        .swal2-actions {
            gap: 12px !important;
        }

        /* Confirm button — kuning solid */
        .kopas-btn-confirm {
            background: #FFC107 !important;
            color: #1a1a1a !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 10px 28px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            cursor: pointer !important;
            transition: background 0.2s, transform 0.15s !important;
        }
        .kopas-btn-confirm:hover {
            background: #e6ac00 !important;
            transform: translateY(-1px) !important;
        }
        .kopas-btn-confirm:active {
            transform: translateY(0) !important;
        }

        /* Cancel button — outline kuning */
        .kopas-btn-cancel {
            background: #fff !important;
            color: #1a1a1a !important;
            border: 2px solid #FFC107 !important;
            border-radius: 10px !important;
            padding: 10px 28px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            cursor: pointer !important;
            transition: background 0.2s, transform 0.15s !important;
        }
        .kopas-btn-cancel:hover {
            background: #fff8e1 !important;
            transform: translateY(-1px) !important;
        }

        /* Icon warna override — question & loading */
        .kopas-icon.swal2-question {
            border-color: #FFC107 !important;
            color: #FFC107 !important;
        }
        .kopas-icon.swal2-success {
            border-color: #FFC107 !important;
            color: #FFC107 !important;
        }
        .kopas-icon.swal2-success [class^=swal2-success-line] {
            background-color: #FFC107 !important;
        }
        .kopas-icon.swal2-success .swal2-success-ring {
            border-color: #ffe082 !important;
        }

        /* Loader spinner */
        .kopas-loader {
            border-color: #FFC107 transparent #FFC107 transparent !important;
        }
    `;
    document.head.appendChild(style);
})();


/* ===== TOGGLE SHOW / HIDE PASSWORD ===== */
$(document).on('click', '.toggle-password', function () {
    const input = $(this).siblings('input');
    const icon  = $(this);

    if (input.attr('type') === 'password') {
        input.attr('type', 'text');
        icon.removeClass('bi-eye-slash-fill').addClass('bi-eye-fill');
    } else {
        input.attr('type', 'password');
        icon.removeClass('bi-eye-fill').addClass('bi-eye-slash-fill');
    }
});


/* ===== HELPER: dialog konfirmasi simpan ===== */
function konfirmasiSimpan(formEl) {
    kopasSwal.fire({
        title:              'Konfirmasi',
        text:               'Apakah data ingin disimpan?',
        icon:               'question',
        showCancelButton:   true,
        confirmButtonText:  'Ya, simpan',
        cancelButtonText:   'Batal',
    }).then((result) => {
        if (result.isConfirmed) {
            kopasSwal.fire({
                title:             'Menyimpan...',
                text:              'Mohon tunggu',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });
            formEl.submit();
        }
    });
}


/* ===== FORM ADMIN ===== */
$("#formAdmin").on("submit", function (e) {
    e.preventDefault();
    konfirmasiSimpan(this);
});


/* ===== FORM ANGGOTA ===== */
$("#formAnggota").on("submit", function (e) {
    e.preventDefault();
    konfirmasiSimpan(this);
});


/* ===== TOGGLE FIELD NONAKTIF ===== */
function toggleNonaktifField() {
    const status  = $('[name="status"]').val();
    const alasan  = $('.field-alasan_nonaktif');
    const tanggal = $('.field-tanggal_nonaktif');

    if (status && status.toLowerCase() === 'nonaktif') {
        alasan.show();
        tanggal.show();
    } else {
        alasan.hide();
        tanggal.hide();
    }
}

$(document).ready(function () {
    toggleNonaktifField();
    $(document).on('change', '[name="status"]', toggleNonaktifField);
});