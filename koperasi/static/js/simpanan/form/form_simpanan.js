// KONFIRMASI SEBELUM SUBMIT
$("#formSimpanan").on("submit", function(e) {
    e.preventDefault();
    const form = this;

    // validasi client-side dulu (sama seperti sebelumnya)
    let valid = true;
    $('.error-jenis, .error-jumlah, .error-dana').text('');
    $('.select-jenis, .rupiah-input').removeClass('is-invalid');

    $('#tbody-simpanan .baris-simpanan').each(function () {
        const $baris = $(this);
        const jenis = $baris.find('.select-jenis').val();
        const jumlahRaw = $baris.find('[name^="jumlah_"]').val() || '';
        const jumlah = parseInt(jumlahRaw.replace(/\D/g, '')) || 0;

        if (!jenis) {
            $baris.find('.select-jenis').addClass('is-invalid');
            $baris.find('.error-jenis').text('Jenis simpanan wajib dipilih.');
            valid = false;
        }
        if (jumlah <= 0) {
            $baris.find('[name^="jumlah_"]').addClass('is-invalid');
            $baris.find('.error-jumlah').text('Jumlah harus lebih dari 0.');
            valid = false;
        } else if (jumlah < 1000) {
            $baris.find('[name^="jumlah_"]').addClass('is-invalid');
            $baris.find('.error-jumlah').text('Minimal simpanan Rp 1.000.');
            valid = false;
        }
    });

    if (!valid) return;

    // inject hidden field jumlah_baris
    $('[name="jumlah_baris"]').remove();
    $('<input>').attr({
        type: 'hidden',
        name: 'jumlah_baris',
        value: $('#tbody-simpanan .baris-simpanan').length
    }).appendTo('#formSimpanan');

    // =============================================
    // Kumpulkan data semua baris untuk ditampilkan
    // =============================================
    const namaAnggota = $('#id_anggota option:selected').text().trim() || "-";
    const tanggal     = $('#id_tanggal').val() || "-";

    let totalKeseluruhan = 0;
    let barisHtml = '';

    $('#tbody-simpanan .baris-simpanan').each(function () {
        const $baris     = $(this);
        const namaJenis  = $baris.find('.select-jenis option:selected').text().trim();
        const jumlahRaw  = parseInt(($baris.find('[name^="jumlah_"]').val() || '0').replace(/\D/g, '')) || 0;
        const danaRaw    = parseInt(($baris.find('[name^="dana_sosial_"]').val() || '0').replace(/\D/g, '')) || 0;
        const isDanaShow = $baris.find('.cell-dana').hasClass('show');

        totalKeseluruhan += jumlahRaw;
        if (isDanaShow) totalKeseluruhan += danaRaw;

        // baris jumlah simpanan
        barisHtml += `
            <tr>
                <td style="padding: 4px 8px; color: #555;">${namaJenis}</td>
                <td style="padding: 4px 8px; text-align:right; font-weight:600;">
                    Rp ${jumlahRaw.toLocaleString('id-ID')}
                </td>
            </tr>`;

        // baris dana sosial (jika ada)
        if (isDanaShow && danaRaw > 0) {
            barisHtml += `
            <tr>
                <td style="padding: 2px 8px 6px 16px; color: #888; font-size:12px;">└ Dana Sosial</td>
                <td style="padding: 2px 8px 6px; text-align:right; color:#888; font-size:12px;">
                    Rp ${danaRaw.toLocaleString('id-ID')}
                </td>
            </tr>`;
        }
    });

    Swal.fire({
        title: "Konfirmasi Simpanan",
        html: `
            <div style="text-align:left; font-size:14px; background:#fff;
                        border-radius:12px; padding:12px 16px;
                        border-left:4px solid #ffd700;">
                <div style="margin-bottom:8px; line-height:1.8;">
                    <b>Anggota &nbsp;:</b> ${namaAnggota}<br>
                    <b>Tanggal &nbsp;&nbsp;:</b> ${tanggal}
                </div>
                <table style="width:100%; border-top:1px solid #eee; margin-top:6px;">
                    <thead>
                        <tr>
                            <th style="padding:6px 8px; text-align:left; font-size:12px;
                                       color:#888; font-weight:600;">Jenis</th>
                            <th style="padding:6px 8px; text-align:right; font-size:12px;
                                       color:#888; font-weight:600;">Jumlah</th>
                        </tr>
                    </thead>
                    <tbody>${barisHtml}</tbody>
                    <tfoot>
                        <tr style="border-top:1px solid #eee;">
                            <td style="padding:8px 8px 4px; font-weight:700;">Total</td>
                            <td style="padding:8px 8px 4px; text-align:right; font-weight:700; color:#d4a000;">
                                Rp ${totalKeseluruhan.toLocaleString('id-ID')}
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `,
        icon: "question",
        iconColor: "#ffd700",
        showCancelButton: true,
        confirmButtonColor: "#ffd700",
        cancelButtonColor: "#ffffff",
        confirmButtonText: '<span style="color:#281b19; font-weight:600;">Ya, Simpan</span>',
        cancelButtonText:  '<span style="color:#281b19; font-weight:600;">Batal</span>',
        customClass: {
            popup:         'kopasmen-swal-popup',
            title:         'kopasmen-swal-title',
            confirmButton: 'kopasmen-confirm-btn',
            cancelButton:  'kopasmen-cancel-btn',
        },
        didOpen: () => {
            if (!document.getElementById('kopasmen-swal-style')) {
                const style = document.createElement('style');
                style.id = 'kopasmen-swal-style';
                style.textContent = `
                    .kopasmen-swal-popup {
                        border-radius: 20px !important;
                        padding: 24px !important;
                        font-family: 'Poppins', sans-serif !important;
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
                        border: none !important;
                        border-radius: 6px !important;
                        padding: 9px 22px !important;
                        font-weight: 700 !important;
                        font-size: 0.9rem !important;
                    }
                    .kopasmen-cancel-btn {
                        background: #ffffff !important;
                        border: 2px solid #FFD700 !important;
                        border-radius: 6px !important;
                        padding: 9px 22px !important;
                        font-weight: 600 !important;
                        font-size: 0.9rem !important;
                    }
                    .kopasmen-confirm-btn:hover { background-color: #e6c200 !important; }
                    .kopasmen-cancel-btn:hover  { background: #fff8e1 !important; }
                `;
                document.head.appendChild(style);
            }
        }
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: "Menyimpan...",
                text: "Mohon tunggu sebentar",
                allowOutsideClick: false,
                customClass: {
                    popup: 'kopasmen-swal-popup',
                    title: 'kopasmen-swal-title',
                },
                didOpen: () => {
                    Swal.showLoading();
                    const loader = Swal.getLoader();
                    if (loader) loader.style.borderTopColor = '#ffd700';
                }
            });
            form.submit();
        }
    });
});