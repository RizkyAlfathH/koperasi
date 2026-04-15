/* ── POPUP IMPORT EXCEL ── */
document.getElementById("btnImport").addEventListener("click", function () {
    Swal.fire({
        icon: "question",
        title: "Import Data Anggota",
        customClass: {
            popup: "swal-small",
            title: "swal-small-title",
            confirmButton: "swal-small-btn",
            cancelButton: "swal-small-btn"
        },
        html: `
            <div style="margin-top:10px; text-align:left;">
                <p style="margin-bottom:10px; color:#7a6000;">Pastikan file Excel memenuhi syarat:</p>
                <ul style="font-size:14px; color:#a07800; padding-left:20px; line-height:1.8;">
                    <li>Format file <b>xlsx</b> atau <b>.xls</b></li>
                    <li>Kolom sesuai template yang tersedia</li>
                    <li>Data tidak duplikat dengan yang sudah ada</li>
                </ul>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: "Pilih File & Import",
        cancelButtonText: "Batal",
        confirmButtonColor: "#f5a623",
        cancelButtonColor: "#e0c060",
        background: "#fffdf0",
        color: "#3d2e00",
        iconColor: "#f5a623"
    }).then(function (result) {
        if (result.isConfirmed) {
            setTimeout(function () {
                document.getElementById("excelInput").click();
            }, 300);
        }
    });
});

/* auto submit saat file excel dipilih */
document.getElementById("excelInput").addEventListener("change", function () {
    if (this.files.length === 0) return;

    const form = this.closest("form");
    const formData = new FormData(form);

    Swal.fire({
        title: "Mengimport Data...",
        background: "#fffdf0",
        color: "#3d2e00",
        html: `
            <p style="color:#a07800; font-size:13px; margin-bottom:16px;">Mohon tunggu sebentar</p>
            <div style="
                background:#fde68a;
                border-radius:999px;
                overflow:hidden;
                height:16px;
                width:100%;
                margin-bottom:8px;
            ">
                <div id="importProgressBar" style="
                    height:100%;
                    width:0%;
                    background: linear-gradient(90deg, #f5a623, #fcd34d);
                    border-radius:999px;
                    transition: width 0.4s ease;
                    box-shadow: 0 0 8px #f5a62366;
                "></div>
            </div>
            <p id="importProgressText" style="
                font-size:13px;
                font-weight:700;
                color:#f5a623;
            ">0%</p>
        `,
        allowOutsideClick: false,
        showConfirmButton: false,
        didOpen: function () {
            const bar  = document.getElementById("importProgressBar");
            const text = document.getElementById("importProgressText");
            let pct = 0;

            window._importInterval = setInterval(function () {
                if (pct < 85) {
                    pct += Math.random() * 7 + 2;
                    if (pct > 85) pct = 85;
                    bar.style.width  = pct.toFixed(0) + "%";
                    text.textContent = pct.toFixed(0) + "%";
                }
            }, 300);

            fetch(form.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                clearInterval(window._importInterval);
                bar.style.width  = "100%";
                text.textContent = "100%";

                setTimeout(function () {

                    /* ── BERHASIL SEMUA ── */
                    if (data.success && !data.failed) {
                        Swal.fire({
                            title: "Import Berhasil!",
                            background: "#fffdf0",
                            color: "#3d2e00",
                            customClass: {
                                popup:         "swal-small",
                                title:         "swal-small-title",
                                confirmButton: "swal-small-btn"
                            },
                            html: `
                                <div style="margin-top:14px;">
                                    <div style="font-size:48px; line-height:1; margin-bottom:12px;">✅</div>
                                    <div style="
                                        background:#fefce8;
                                        border:1px solid #fcd34d;
                                        border-radius:10px;
                                        padding:12px 20px;
                                        font-size:15px;
                                        font-weight:600;
                                        color:#92400e;
                                    ">
                                        ${data.imported} data berhasil diimport
                                    </div>
                                </div>
                            `,
                            confirmButtonText:  "Oke",
                            confirmButtonColor: "#f5a623",
                            showConfirmButton:  true
                        }).then(function () { location.reload(); });

                    /* ── BERHASIL SEBAGIAN ── */
                    } else if (data.imported > 0 && data.failed > 0) {
                        const errItems = Array.isArray(data.errors) && data.errors.length
                            ? data.errors.slice(0, 5).map(function (e) {
                                return `<li style="margin-bottom:3px;">${e}</li>`;
                              }).join("") +
                              (data.errors.length > 5
                                ? `<li style="color:#d97706;">... dan ${data.errors.length - 5} lainnya</li>`
                                : "")
                            : "";

                        Swal.fire({
                            title: "Import Selesai",
                            background: "#fffdf0",
                            color: "#3d2e00",
                            customClass: {
                                popup:         "swal-small",
                                title:         "swal-small-title",
                                confirmButton: "swal-small-btn",
                                cancelButton:  "swal-small-btn"
                            },
                            html: `
                                <div style="margin-top:12px; text-align:left;">
                                    <div style="
                                        background:#fefce8;
                                        border:1px solid #fcd34d;
                                        border-radius:8px;
                                        padding:10px 14px;
                                        font-size:14px;
                                        font-weight:600;
                                        color:#92400e;
                                        margin-bottom:8px;
                                        display:flex; align-items:center; gap:8px;
                                    ">
                                        ✅ ${data.imported} data berhasil diimport
                                    </div>
                                    <div style="
                                        background:#fef2f2;
                                        border:1px solid #fecaca;
                                        border-radius:8px;
                                        padding:10px 14px;
                                        font-size:14px;
                                        font-weight:600;
                                        color:#dc2626;
                                        margin-bottom:${errItems ? "10px" : "0"};
                                        display:flex; align-items:center; gap:8px;
                                    ">
                                        ❌ ${data.failed} data gagal diimport
                                    </div>
                                    ${errItems ? `
                                    <p style="font-size:12px; color:#a07800; margin:8px 0 4px;">Detail baris yang gagal:</p>
                                    <ul style="
                                        font-size:12px; color:#78350f;
                                        padding:10px 10px 10px 24px;
                                        background:#fef9e7;
                                        border:1px solid #fde68a;
                                        border-radius:8px;
                                        line-height:1.8;
                                        max-height:110px;
                                        overflow-y:auto;
                                        margin:0;
                                    ">${errItems}</ul>` : ""}
                                </div>
                            `,
                            showCancelButton:   true,
                            confirmButtonText:  "Oke",
                            cancelButtonText:   "Coba Lagi",
                            confirmButtonColor: "#f5a623",
                            cancelButtonColor:  "#d97706"
                        }).then(function (r) {
                            if (r.isConfirmed) {
                                location.reload();
                            } else {
                                document.getElementById("excelInput").value = "";
                                document.getElementById("excelInput").click();
                            }
                        });

                    /* ── GAGAL SEMUA ── */
                    } else {
                        const errItems = Array.isArray(data.errors) && data.errors.length
                            ? data.errors.slice(0, 5).map(function (e) {
                                return `<li style="margin-bottom:3px;">${e}</li>`;
                              }).join("") +
                              (data.errors.length > 5
                                ? `<li style="color:#d97706;">... dan ${data.errors.length - 5} lainnya</li>`
                                : "")
                            : "";

                        Swal.fire({
                            title: "Import Gagal",
                            background: "#fffdf0",
                            color: "#3d2e00",
                            customClass: {
                                popup:         "swal-small",
                                title:         "swal-small-title",
                                confirmButton: "swal-small-btn",
                                cancelButton:  "swal-small-btn"
                            },
                            html: `
                                <div style="margin-top:12px;">
                                    <div style="font-size:48px; line-height:1; margin-bottom:12px;">❌</div>
                                    <div style="
                                        background:#fef2f2;
                                        border:1px solid #fecaca;
                                        border-radius:8px;
                                        padding:10px 14px;
                                        font-size:14px;
                                        font-weight:600;
                                        color:#dc2626;
                                        margin-bottom:${errItems ? "10px" : "0"};
                                        text-align:left;
                                    ">
                                        ${data.failed ?? "Semua"} data gagal diimport
                                    </div>
                                    ${errItems ? `
                                    <p style="font-size:12px; color:#a07800; margin:8px 0 4px; text-align:left;">Detail kesalahan:</p>
                                    <ul style="
                                        font-size:12px; color:#78350f;
                                        padding:10px 10px 10px 24px;
                                        background:#fef9e7;
                                        border:1px solid #fde68a;
                                        border-radius:8px;
                                        line-height:1.8;
                                        max-height:110px;
                                        overflow-y:auto;
                                        margin:0;
                                        text-align:left;
                                    ">${errItems}</ul>` : ""}
                                </div>
                            `,
                            showCancelButton:   true,
                            confirmButtonText:  "Coba Lagi",
                            cancelButtonText:   "Tutup",
                            confirmButtonColor: "#f5a623",
                            cancelButtonColor:  "#d97706"
                        }).then(function (r) {
                            if (r.isConfirmed) {
                                document.getElementById("excelInput").value = "";
                                document.getElementById("excelInput").click();
                            }
                        });
                    }

                }, 400);
            })
            .catch(function () {
                clearInterval(window._importInterval);
                Swal.fire({
                    title: "Terjadi Kesalahan",
                    text: "Gagal terhubung ke server. Coba lagi.",
                    background: "#fffdf0",
                    color: "#3d2e00",
                    confirmButtonText:  "Oke",
                    confirmButtonColor: "#f5a623",
                    iconColor: "#f5a623",
                    customClass: {
                        popup:         "swal-small",
                        title:         "swal-small-title",
                        confirmButton: "swal-small-btn"
                    }
                });
            });
        }
    });
});

/* ── POPUP EXPORT EXCEL ── */
document.getElementById("btnExportExcel").addEventListener("click", function (e) {
    e.preventDefault();
    const url = this.getAttribute("href");

    const jumlahAnggota = document.querySelectorAll("table .badge-aktif, table .badge-nonaktif, table .badge-default").length;

    if (jumlahAnggota === 0) {
        Swal.fire({
            icon: "warning",
            iconColor: "#f5a623",
            title: "Tidak Ada Data",
            background: "#fffdf0",
            color: "#3d2e00",
            customClass: {
                popup:         "swal-small",
                title:         "swal-small-title",
                confirmButton: "swal-small-btn"
            },
            html: `
                <div style="margin-top:12px;">
                    <div style="font-size:44px; margin-bottom:12px;">📭</div>
                    <p style="color:#92400e; font-size:14px;">
                        Belum ada data anggota yang bisa diekspor.<br>
                        <span style="font-size:13px; color:#a07800;">Tambahkan anggota terlebih dahulu.</span>
                    </p>
                </div>
            `,
            confirmButtonText:  "Oke",
            confirmButtonColor: "#f5a623"
        });
        return;
    }

    Swal.fire({
        icon: "question",
        iconColor: "#f5a623",
        title: "Export Data Anggota",
        background: "#fffdf0",
        color: "#3d2e00",
        customClass: {
            popup: "swal-small",
            title: "swal-small-title",
            confirmButton: "swal-small-btn",
            cancelButton: "swal-small-btn"
        },
        html: `
            <div style="margin-top:10px;">
                <p style="color:#92400e; margin-bottom:12px;">
                    Anda akan mengekspor seluruh data anggota dalam format:
                </p>
                <div style="
                    display:inline-flex; align-items:center; gap:8px;
                    background:#fefce8; border:1px solid #fcd34d;
                    padding:10px 20px; border-radius:8px;
                    font-weight:600; font-size:15px; color:#92400e;
                ">
                    <i class="ph-bold ph-file-xls" style="font-size:20px;"></i>
                    Excel (.xlsx)
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: "Ya, Export Sekarang",
        cancelButtonText: "Batal",
        confirmButtonColor: "#f5a623",
        cancelButtonColor: "#d97706"
    }).then(function (result) {
        if (result.isConfirmed) {
            Swal.close();
            const a = document.createElement("a");
            a.href = url;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });
});

/* ── POPUP EXPORT PDF ── */
document.getElementById("btnExportPdf").addEventListener("click", function (e) {
    e.preventDefault();
    const url = this.getAttribute("href");

    const jumlahAnggota = document.querySelectorAll("table .badge-aktif, table .badge-nonaktif, table .badge-default").length;

    if (jumlahAnggota === 0) {
        Swal.fire({
            icon: "warning",
            iconColor: "#f5a623",
            title: "Tidak Ada Data",
            background: "#fffdf0",
            color: "#3d2e00",
            customClass: {
                popup:         "swal-small",
                title:         "swal-small-title",
                confirmButton: "swal-small-btn"
            },
            html: `
                <div style="margin-top:12px;">
                    <div style="font-size:44px; margin-bottom:12px;">📭</div>
                    <p style="color:#92400e; font-size:14px;">
                        Belum ada data anggota yang bisa diekspor.<br>
                        <span style="font-size:13px; color:#a07800;">Tambahkan anggota terlebih dahulu.</span>
                    </p>
                </div>
            `,
            confirmButtonText:  "Oke",
            confirmButtonColor: "#f5a623"
        });
        return;
    }

    Swal.fire({
        icon: "question",
        iconColor: "#f5a623",
        title: "Export Data Anggota",
        background: "#fffdf0",
        color: "#3d2e00",
        customClass: {
            popup: "swal-small",
            title: "swal-small-title",
            confirmButton: "swal-small-btn",
            cancelButton: "swal-small-btn"
        },
        html: `
            <div style="margin-top:10px;">
                <p style="color:#92400e; margin-bottom:12px;">
                    Anda akan mengekspor seluruh data anggota dalam format:
                </p>
                <div style="
                    display:inline-flex; align-items:center; gap:8px;
                    background:#fefce8; border:1px solid #fcd34d;
                    padding:10px 20px; border-radius:8px;
                    font-weight:600; font-size:15px; color:#b45309;
                ">
                    <i class="ph-bold ph-file-pdf" style="font-size:20px;"></i>
                    PDF (.pdf)
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: "Ya, Export Sekarang",
        cancelButtonText: "Batal",
        confirmButtonColor: "#f5a623",
        cancelButtonColor: "#d97706"
    }).then(function (result) {
        if (result.isConfirmed) {
            Swal.close();
            const a = document.createElement("a");
            a.href = url;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });
});

document.querySelectorAll(".action-delete").forEach(function(btn) {
    btn.addEventListener("click", async function(e) {
        e.preventDefault();

        const url    = this.getAttribute("href");
        const name   = this.dataset.name;
        const type   = this.dataset.type;
        const cekUrl = this.dataset.cekUrl;

        // cek saldo dulu kalau ini anggota
        if (type === "anggota" && cekUrl) {

            Swal.fire({
                title: "Memeriksa data...",
                background: "#fffdf0",
                color: "#3d2e00",
                allowOutsideClick: false,
                showConfirmButton: false,
                didOpen: () => Swal.showLoading()
            });

            try {
                const res  = await fetch(cekUrl);
                const data = await res.json();

                // kalau masih ada saldo → tampilkan peringatan, stop
                if (data.saldo > 0) {
                    const formatted = new Intl.NumberFormat("id-ID", {
                        style: "currency",
                        currency: "IDR",
                        minimumFractionDigits: 0
                    }).format(data.saldo);

                    // ambil nomor anggota dari cekUrl
                    // contoh url: /anggota/cek-saldo/AN 01/
                    const rawNomor = cekUrl.split("/cek-saldo/")[1].replace(/\/$/, "");
                    const nomorAnggota = decodeURIComponent(rawNomor);
                    const penarikanUrl = `/simpanan/${encodeURIComponent(nomorAnggota)}/`; // ke halaman simpanan anggota

                    Swal.fire({
                        icon: "error",
                        iconColor: "#dc2626",
                        title: "Tidak Dapat Dihapus",
                        background: "#fffdf0",
                        color: "#3d2e00",
                        customClass: {
                            popup:         "swal-small",
                            title:         "swal-small-title",
                            confirmButton: "swal-small-btn",
                            cancelButton:  "swal-small-btn"
                        },
                        html: `
                            <p style="margin-bottom:8px; color:#92400e;">
                                Anggota <b>${name}</b> masih memiliki saldo simpanan:
                            </p>
                            <div style="
                                background:#fef2f2;
                                border:1px solid #fca5a5;
                                padding:10px;
                                border-radius:6px;
                                font-weight:700;
                                font-size:18px;
                                color:#dc2626;
                                margin-bottom:12px;
                            ">
                                ${formatted}
                            </div>
                            <p style="font-size:13px; color:#a07800;">
                                Lakukan <b>penarikan semua simpanan</b> terlebih dahulu 
                                sebelum menghapus anggota ini.
                            </p>
                        `,
                        showCancelButton: true,
                        confirmButtonText: 'Ke Halaman Penarikan',
                        cancelButtonText: "Tutup",
                        confirmButtonColor: "#d97706",
                        cancelButtonColor: "#dc3545",
                    }).then((result) => {
                        if (result.isConfirmed) {
                            window.location.href = penarikanUrl;
                        }
                    });
                    return;
                }

            } catch (err) {
                Swal.fire({
                    icon: "error",
                    title: "Gagal memeriksa data",
                    text: "Terjadi kesalahan saat mengecek saldo anggota.",
                    confirmButtonColor: "#dc3545",
                });
                return;
            }
        }

        // lanjut ke konfirmasi hapus normal (saldo 0 atau bukan anggota)
        Swal.fire({
            icon: "warning",
            iconColor: "#f5a623",
            title: "Konfirmasi Penghapusan",
            background: "#fffdf0",
            color: "#3d2e00",
            customClass: {
                popup:         "swal-small",
                title:         "swal-small-title",
                input:         "swal-small-input",
                confirmButton: "swal-small-btn",
                cancelButton:  "swal-small-btn"
            },
            html: `
                <div style="margin-top:10px">
                    <p style="margin-bottom:8px; color:#92400e;">
                        Anda akan menghapus <b>${type}</b> berikut:
                    </p>
                    <div style="
                        background:#fefce8;
                        border:1px solid #fcd34d;
                        padding:10px;
                        border-radius:6px;
                        font-weight:600;
                        color:#78350f;
                        margin-bottom:15px;
                    ">
                        ${name}
                    </div>
                    <p style="font-size:14px; color:#a07800;">
                        untuk melanjutkan ketik 
                        <b style="color:#dc2626;">hapus</b> di bawah ini
                    </p>
                </div>
            `,
            input: "text",
            inputPlaceholder: "ketik 'hapus'",
            inputAttributes: {
                style: "border:1.5px solid #fcd34d; background:#fffdf0; color:#3d2e00;"
            },
            showCancelButton: true,
            confirmButtonText: "Hapus Data",
            cancelButtonText: "Batal",
            confirmButtonColor: "#dc3545",
            cancelButtonColor: "#d97706",

            preConfirm: (value) => {
                if (!value) {
                    Swal.showValidationMessage("Silakan ketik 'hapus' terlebih dahulu");
                    return false;
                }
                if (value.toLowerCase() !== "hapus") {
                    Swal.showValidationMessage("Kata konfirmasi harus 'hapus'");
                    return false;
                }
                return true;
            }

        }).then((result) => {
            if (result.isConfirmed) {
                Swal.fire({
                    title: "Menghapus Data...",
                    text: "Mohon tunggu sebentar",
                    background: "#fffdf0",
                    color: "#3d2e00",
                    allowOutsideClick: false,
                    showConfirmButton: false,
                    didOpen: () => Swal.showLoading()
                });

                setTimeout(() => {
                    window.location.href = url;
                }, 600);
            }
        });

    });
});