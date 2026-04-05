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
                background: #f9f9f9;
                border-radius: 12px;
                padding: 12px 16px;
                border-left: 4px solid #F5C518;
            ">
                <b>Anggota &nbsp;&nbsp;:</b> ${namaAnggota}<br>
                <b>Jenis &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:</b> ${jenisSimpanan}<br>
                <b>Jumlah &nbsp;&nbsp;&nbsp;:</b> Rp ${jumlah}<br>
                <b>Tanggal &nbsp;&nbsp;:</b> ${tanggal}
            </div>
        `,
        icon: "question",
        iconColor: "#F5C518",
        showCancelButton: true,
        confirmButtonColor: "#F5C518",
        cancelButtonColor: "#ffffff",
        confirmButtonText: '<span style="color: #1a1a1a; font-weight: 600;">Ya, Simpan</span>',
        cancelButtonText: '<span style="color: #e53935; font-weight: 600;">Batal</span>',
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
                        font-family: 'Segoe UI', sans-serif;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.15) !important;
                    }
                    .kopasmen-swal-title {
                        font-size: 20px !important;
                        font-weight: 700 !important;
                        color: #1a1a1a !important;
                    }
                    .kopasmen-confirm-btn {
                        border-radius: 10px !important;
                        padding: 10px 28px !important;
                        font-size: 14px !important;
                        border: none !important;
                        box-shadow: 0 4px 12px rgba(245, 197, 24, 0.45) !important;
                    }
                    .kopasmen-cancel-btn {
                        border-radius: 10px !important;
                        padding: 10px 28px !important;
                        font-size: 14px !important;
                        border: 2px solid #e53935 !important;
                        box-shadow: none !important;
                    }
                    .kopasmen-confirm-btn:hover {
                        background-color: #e6b800 !important;
                    }
                    .kopasmen-cancel-btn:hover {
                        background-color: #ffeaea !important;
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
                iconColor: "#F5C518",
                allowOutsideClick: false,
                customClass: {
                    popup: 'kopasmen-swal-popup',
                    title: 'kopasmen-swal-title',
                },
                didOpen: () => {
                    Swal.showLoading();
                    // Warnai loader spinner
                    const loader = Swal.getLoader();
                    if (loader) loader.style.borderTopColor = '#F5C518';
                }
            });
            form.submit();
        }
    });
});