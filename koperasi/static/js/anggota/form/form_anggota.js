/* ================= sweetalert theme ================= */
const kopasSwal = Swal.mixin({
    customClass: {
        popup:         'kopas-popup',
        title:         'kopas-title',
        htmlContainer: 'kopas-text',
        confirmButton: 'kopas-btn-confirm',
        cancelButton:  'kopas-btn-cancel',
        icon:          'kopas-icon',
        loader:        'kopas-loader',
    },
    buttonsStyling: true,
    background: '#ffffff',
    color: '#291B18',
});


/* ================= inject custom style ================= */
(function injectKopasStyle() {
    const style = document.createElement('style');
    style.textContent = `

        /* popup card */
        .kopas-popup {
            border-radius: 16px !important;
            padding: 26px 24px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
            font-family: inherit !important;
            width: 30% !important;
            text-align: center !important;
        }

        /* title */
        .kopas-title {
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            color: #291B18 !important;
            margin-bottom: 6px !important;
        }

        /* text / content */
        .kopas-text {
            font-size: 0.92rem !important;
            color: #666 !important;
            margin-bottom: 12px !important;
        }

        /* icon spacing */
        .kopas-icon {
            margin: 10px auto 12px auto !important;
        }

        /* action buttons wrapper */
        .swal2-actions {
            justify-content: center !important;
            margin-top: 10px !important;
        }

        /* tombol confirm */
        .kopas-btn-confirm {
            background: #FFD700 !important;
            color: #291B18 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 9px 22px !important;
            font-weight: 700 !important;
            font-size: 0.9rem !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        .kopas-btn-confirm:hover {
            background: #e6c200 !important;
        }

        /* tombol cancel */
        .kopas-btn-cancel {
            background: #ffffff !important;
            color: #291B18 !important;
            border: 2px solid #FFD700 !important;
            border-radius: 6px !important;
            padding: 9px 22px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        .kopas-btn-cancel:hover {
            background: #fff8e1 !important;
        }

        /* icon warna */
        .kopas-icon.swal2-question,
        .kopas-icon.swal2-success {
            border-color: #FFD700 !important;
            color: #FFD700 !important;
        }

        .kopas-icon.swal2-success [class^=swal2-success-line] {
            background-color: #FFD700 !important;
        }

        .kopas-icon.swal2-success .swal2-success-ring {
            border-color: #ffe082 !important;
        }

        /* loader spinner */
        .kopas-loader {
            border-color: #FFD700 transparent #FFD700 transparent !important;
        }

    `;
    document.head.appendChild(style);
})();


/* ================= toggle show / hide password ================= */
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


/* ================= helper konfirmasi simpan ================= */
function konfirmasiSimpan(formEl) {
    kopasSwal.fire({
        title: 'Konfirmasi',
        text: 'Apakah data ingin disimpan?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '<span style="color: #281b19; font-weight: 600;">Ya, Simpan</span>',
        cancelButtonText: '<span style="color: #281b19; font-weight: 600;">Batal</span>',
    }).then((result) => {

        /* jika user konfirmasi */
        if (result.isConfirmed) {
            kopasSwal.fire({
                title: 'Menyimpan...',
                text: 'Mohon tunggu',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            formEl.submit();
        }
    });
}


/* ================= form admin ================= */
$("#formAdmin").on("submit", function (e) {
    e.preventDefault();
    konfirmasiSimpan(this);
});


/* ================= form anggota ================= */
$("#formAnggota").on("submit", function (e) {
    e.preventDefault();
    konfirmasiSimpan(this);
});


/* ================= toggle field status nonaktif ================= */
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


/* ================= init ================= */
$(document).ready(function () {
    toggleNonaktifField();
    $(document).on('change', '[name="status"]', toggleNonaktifField);
});