// KONFIRMASI SEBELUM SUBMIT
$("#formSimpanan").on("submit", function(e) {
    e.preventDefault();
    const form = this;

    const namaAnggota = $('#id_anggota option:selected').text() || "-";
    const jenisSimpanan = $('#id_jenis_simpanan option:selected').text() || "-";
    const jumlah = $('#id_jumlah').val() || "0";
    const tanggal = $('#id_tanggal').val() || "-";

    Swal.fire({
        title: "Konfirmasi Simpanan",
        html: `
            <div style="
                text-align: left;
                font-size: 14px;
                line-height: 2;
                background: #ffffff;
                border-radius: 12px;
                padding: 12px 16px;
                border-left: 4px solid #ffd700;
            ">
                <b>Anggota&nbsp;&nbsp;:</b> ${namaAnggota}<br>
                <b>Jenis&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:</b> ${jenisSimpanan}<br>
                <b>Jumlah&nbsp;&nbsp;&nbsp;&nbsp;:</b> Rp ${jumlah}<br>
                <b>Tanggal&nbsp;&nbsp; :</b> ${tanggal}
            </div>
        `,
        icon: "question",
        iconColor: "#ffd700",
        showCancelButton: true,
        confirmButtonColor: "#ffd700",
        cancelButtonColor: "#ffffff",
        confirmButtonText: '<span style="color: #281b19; font-weight: 600;">Ya, Simpan</span>',
        cancelButtonText: '<span style="color: #281b19; font-weight: 600;">Batal</span>',
        customClass: {
            popup: 'kopasmen-swal-popup',
            title: 'kopasmen-swal-title',
            confirmButton: 'kopasmen-confirm-btn',
            cancelButton: 'kopasmen-cancel-btn',
        },
        didOpen: () => {
            // Inject custom CSS sekali pakai
            if (!document.getElementById('kopasmen-swal-style')) {
                const style = document.createElement('style');
                style.id = 'kopasmen-swal-style';
                style.textContent = `
                    .kopasmen-swal-popup {
                        border-radius: 20px !important;
                        padding: 24px !important;
                        font-family: 'poppins', sans-serif !important;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.15) !important;
                    }
                    .kopasmen-swal-title {
                        font-size: 1.25rem !important;
                        font-weight: 700 !important;
                        color: #291B18 !important;
                        margin-bottom: 6px !important;
                    }
                    .kopasmen-confirm-btn {
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
                    .kopasmen-cancel-btn {
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
                    .kopasmen-confirm-btn:hover {
                        background-color: #e6c200 !important;
                    }
                    .kopasmen-cancel-btn:hover {
                        background: #fff8e1 !important;
                    }
                `;
                document.head.appendChild(style);
            }
        }
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: "Menyimpan...",
                text: "Mohon tunggu sebentar",
                iconColor: "#ffd700",
                allowOutsideClick: false,
                customClass: {
                    popup: 'kopasmen-swal-popup',
                    title: 'kopasmen-swal-title',
                },
                didOpen: () => {
                    Swal.showLoading();
                    // Warnai loader spinner
                    const loader = Swal.getLoader();
                    if (loader) loader.style.borderTopColor = '#ffd700';
                }
            });
            form.submit();
        }
    });
});