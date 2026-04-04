from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q

from .models import Anggota
from .forms import AnggotaForm, AdminForm
from django.contrib.auth import get_user_model
from django.db.models import Case, When, Value, IntegerField

from django.http import HttpResponse
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from openpyxl import load_workbook
from datetime import datetime,date

from datetime import date
from dateutil.relativedelta import relativedelta

import re

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from simpanan.models import Simpanan, Penarikan
from pinjaman.models import Pinjaman, Angsuran
from collections import defaultdict

User = get_user_model()


# -- KONFIG ROLE -- #
ROLE_ADMIN = ["admin", "ketua", "sekretaris", "bendahara"]
ROLE_PENGURUS = ["ketua", "sekretaris", "bendahara"]


# --REDIRECT UTAMA SETELAH LOGIN -- #
@login_required
def dashboard_redirect(request):
    role = request.user.role

    if role == "ketua":
        return redirect("anggota:dashboard_ketua")
    elif role == "sekretaris":
        return redirect("anggota:dashboard_sekretaris")
    elif role == "bendahara":
        return redirect("anggota:dashboard_bendahara")
    elif role == "admin":
        return redirect("admin_koperasi:admin_dashboard")
    else:
        return redirect("admin_koperasi:admin_login")


# -- DASHBOARD PER ROLE --#
@login_required
def ketua_dashboard(request):
    if request.user.role != "ketua":
        return redirect("anggota:dashboard_redirect")

    # INFO CARD
    jumlah_admin = User.objects.filter(
        is_superuser=False,
        role__in=["ketua", "sekretaris", "bendahara"]
    ).count()

    jumlah_anggota = Anggota.objects.filter(status="aktif").count()

    jumlah_simpanan = (
        Simpanan.objects.aggregate(total=Sum("jumlah"))["total"] or 0
    )

    jumlah_pinjaman = (
        Pinjaman.objects
        .filter(status="aktif")
        .aggregate(total=Sum("sisa_pinjaman"))["total"] or 0
    )

    # DATA BULANAN
    bulan_labels = []
    simpanan_data = []
    pinjaman_data = []

    today = date.today()
    start = date(today.year - 1, today.month, 1)

    for i in range(12):

        bulan = start + relativedelta(months=i)

        akhir_bulan = (
            bulan + relativedelta(months=1)
        ) - relativedelta(days=1)
    
        # TOTAL SIMPANAN
        total_simpanan = (
            Simpanan.objects
            .filter(tanggal__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah"))["total"] or 0
        )

        # TOTAL PINJAMAN DIAMBIL
        total_pinjaman = (
            Pinjaman.objects
            .filter(tanggal_meminjam__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah_pinjaman"))["total"] or 0
        )

        # JUMLAH CICILAN SAMPAI BULAN ITU
        total_cicilan = (
            Angsuran.objects
            .filter(
                tanggal_bayar__lte=akhir_bulan,
                tipe_bayar="cicilan"
            )
            .values("id_pinjaman")
            .annotate(jumlah=Count("id_pembayaran"))
        )

        total_pokok_terbayar = 0

        for cicilan in total_cicilan:
            pinjaman = Pinjaman.objects.get(id_pinjaman=cicilan["id_pinjaman"])
            total_pokok_terbayar += cicilan["jumlah"] * pinjaman.angsuran_per_bulan

        # SISA PINJAMAN
        sisa_pinjaman = total_pinjaman - total_pokok_terbayar

        if sisa_pinjaman < 0:
            sisa_pinjaman = 0

        bulan_labels.append(bulan.strftime("%b %Y"))
        simpanan_data.append(float(total_simpanan))
        pinjaman_data.append(float(sisa_pinjaman))

    context = {
        "jumlah_admin": jumlah_admin,
        "jumlah_anggota": jumlah_anggota,
        "jumlah_simpanan": jumlah_simpanan,
        "jumlah_pinjaman": jumlah_pinjaman,
        "bulan_labels": bulan_labels,
        "simpanan_data": simpanan_data,
        "pinjaman_data": pinjaman_data,
    }

    return render(request, "dashboard/ketua.html", context)


@login_required
def sekretaris_dashboard(request):
    if request.user.role != "sekretaris":
        return redirect("anggota:dashboard_redirect")

    # INFO CARD
    jumlah_admin = User.objects.filter(
        is_superuser=False,
        role__in=["ketua", "sekretaris", "bendahara"]
    ).count()

    jumlah_anggota = Anggota.objects.filter(status="aktif").count()

    jumlah_simpanan = (
        Simpanan.objects.aggregate(total=Sum("jumlah"))["total"] or 0
    )

    jumlah_pinjaman = (
        Pinjaman.objects
        .filter(status="aktif")
        .aggregate(total=Sum("sisa_pinjaman"))["total"] or 0
    )

    # DATA BULANAN
    bulan_labels = []
    simpanan_data = []
    pinjaman_data = []

    today = date.today()
    start = date(today.year - 1, today.month, 1)

    for i in range(12):

        bulan = start + relativedelta(months=i)

        akhir_bulan = (
            bulan + relativedelta(months=1)
        ) - relativedelta(days=1)

        # TOTAL SIMPANAN
        total_simpanan = (
            Simpanan.objects
            .filter(tanggal__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah"))["total"] or 0
        )

        # TOTAL PINJAMAN DIAMBIL
        total_pinjaman = (
            Pinjaman.objects
            .filter(tanggal_meminjam__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah_pinjaman"))["total"] or 0
        )

        # JUMLAH CICILAN SAMPAI BULAN ITU
        total_cicilan = (
            Angsuran.objects
            .filter(
                tanggal_bayar__lte=akhir_bulan,
                tipe_bayar="cicilan"
            )
            .values("id_pinjaman")
            .annotate(jumlah=Count("id_pembayaran"))
        )

        total_pokok_terbayar = 0

        for cicilan in total_cicilan:
            pinjaman = Pinjaman.objects.get(id_pinjaman=cicilan["id_pinjaman"])
            total_pokok_terbayar += cicilan["jumlah"] * pinjaman.angsuran_per_bulan

        # SISA PINJAMAN
        sisa_pinjaman = total_pinjaman - total_pokok_terbayar

        if sisa_pinjaman < 0:
            sisa_pinjaman = 0

        bulan_labels.append(bulan.strftime("%b %Y"))
        simpanan_data.append(float(total_simpanan))
        pinjaman_data.append(float(sisa_pinjaman))

    context = {
        "jumlah_admin": jumlah_admin,
        "jumlah_anggota": jumlah_anggota,
        "jumlah_simpanan": jumlah_simpanan,
        "jumlah_pinjaman": jumlah_pinjaman,
        "bulan_labels": bulan_labels,
        "simpanan_data": simpanan_data,
        "pinjaman_data": pinjaman_data,
    }

    return render(request, "dashboard/sekretaris.html", context)


@login_required
def bendahara_dashboard(request):
    if request.user.role != "bendahara":
        return redirect("anggota:dashboard_redirect")

    # INFO CARD
    jumlah_admin = User.objects.filter(
        is_superuser=False,
        role__in=["ketua", "sekretaris", "bendahara"]
    ).count()

    jumlah_anggota = Anggota.objects.filter(status="aktif").count()

    jumlah_simpanan = (
        Simpanan.objects.aggregate(total=Sum("jumlah"))["total"] or 0
    )

    jumlah_pinjaman = (
        Pinjaman.objects
        .filter(status="aktif")
        .aggregate(total=Sum("sisa_pinjaman"))["total"] or 0
    )

    # DATA BULANAN
    bulan_labels = []
    simpanan_data = []
    pinjaman_data = []

    today = date.today()
    start = date(today.year - 1, today.month, 1)

    for i in range(12):

        bulan = start + relativedelta(months=i)

        akhir_bulan = (
            bulan + relativedelta(months=1)
        ) - relativedelta(days=1)

        # TOTAL SIMPANAN
        total_simpanan = (
            Simpanan.objects
            .filter(tanggal__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah"))["total"] or 0
        )

        # TOTAL PINJAMAN DIAMBIL
        total_pinjaman = (
            Pinjaman.objects
            .filter(tanggal_meminjam__lte=akhir_bulan)
            .aggregate(total=Sum("jumlah_pinjaman"))["total"] or 0
        )

        # JUMLAH CICILAN SAMPAI BULAN ITU
        total_cicilan = (
            Angsuran.objects
            .filter(
                tanggal_bayar__lte=akhir_bulan,
                tipe_bayar="cicilan"
            )
            .values("id_pinjaman")
            .annotate(jumlah=Count("id_pembayaran"))
        )

        total_pokok_terbayar = 0

        for cicilan in total_cicilan:
            pinjaman = Pinjaman.objects.get(id_pinjaman=cicilan["id_pinjaman"])
            total_pokok_terbayar += cicilan["jumlah"] * pinjaman.angsuran_per_bulan

        # SISA PINJAMAN
        sisa_pinjaman = total_pinjaman - total_pokok_terbayar

        if sisa_pinjaman < 0:
            sisa_pinjaman = 0

        bulan_labels.append(bulan.strftime("%b %Y"))
        simpanan_data.append(float(total_simpanan))
        pinjaman_data.append(float(sisa_pinjaman))

    context = {
        "jumlah_admin": jumlah_admin,
        "jumlah_anggota": jumlah_anggota,
        "jumlah_simpanan": jumlah_simpanan,
        "jumlah_pinjaman": jumlah_pinjaman,
        "bulan_labels": bulan_labels,
        "simpanan_data": simpanan_data,
        "pinjaman_data": pinjaman_data,
    }

    return render(request, "dashboard/bendahara.html", context)



# -- KELOLA AKUN (ROLE-BASED) -- #
from admin_koperasi.utils import has_page_permission

@login_required
def kelola_akun(request):
    if not has_page_permission(request.user, "kelola_anggota"):
        return redirect("dashboard")

    role = request.user.role

    search_admin = request.GET.get("searchAdmin", "")
    search_anggota = request.GET.get("searchAnggota", "")

    admins = User.objects.filter(role__in=ROLE_PENGURUS)
    if search_admin:
        admins = admins.filter(username__icontains=search_admin)

    paginator_admin = Paginator(admins.order_by("id"), 10)
    admins_page = paginator_admin.get_page(
        request.GET.get("page_admin", 1)
    )

    anggotas = Anggota.objects.annotate(
        status_order=Case(
            When(status__iexact="NONAKTIF", then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    )

    if search_anggota:
        anggotas = anggotas.filter(nama__icontains=search_anggota)

    paginator_anggota = Paginator(
        anggotas.order_by("status_order", "nomor_anggota"),
        10
    )
    anggotas_page = paginator_anggota.get_page(
        request.GET.get("page_anggota", 1)
    )

    return render(request, "kelola_akun/kelola_akun.html", {
        "admins": admins_page,
        "anggotas": anggotas_page,
        "searchAdmin": search_admin,
        "searchAnggota": search_anggota,
        "ROLE_ADMIN": ROLE_ADMIN,
    })


# -- CRUD ADMIN (KETUA / SEKRETARIS / BENDAHARA) -- #
@login_required
def tambah_admin(request):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    if request.method == "POST":
        form = AdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin berhasil ditambahkan.")
            return redirect("anggota:kelola_akun")

    else:
        form = AdminForm()

    return render(request, "kelola_akun/Form/form_admin.html", {
        "form": form,
        "judul": "Tambah Admin"
    })


@login_required
def edit_admin(request, user_id):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    admin = get_object_or_404(User, id=user_id, role__in=ROLE_PENGURUS)
    form = AdminForm(request.POST or None, instance=admin)

    if form.is_valid():
        form.save()
        messages.success(request, "Admin berhasil diperbarui.")
        return redirect("anggota:kelola_akun")

    return render(request, "kelola_akun/Form/form_admin.html", {
        "form": form,
        "judul": "Edit Admin"
    })


@login_required
def hapus_admin(request, user_id):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    admin = get_object_or_404(User, id=user_id, role__in=ROLE_PENGURUS)
    admin.delete()
    messages.success(request, "Admin berhasil dihapus.")
    return redirect("anggota:kelola_akun")

def detail_admin(request, user_id):
    admin = get_object_or_404(User, id=user_id)

    nomor_urut = User.objects.filter(id__lte=admin.id).count()

    context = {
        "admin": admin,
        "nomor_urut": nomor_urut,
    }
    return render(request, "kelola_akun/detail/detail_admin.html", context)


# -- CRUD ANGGOTA -- #
@login_required
def tambah_anggota(request):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    if request.method == "POST":
        form = AnggotaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Anggota berhasil ditambahkan.")
            return redirect("anggota:kelola_akun")
    else:
        form = AnggotaForm()

    return render(request, "kelola_akun/Form/form_anggota.html", {
        "form": form,
        "judul": "Tambah Anggota"
    })


@login_required
def edit_anggota(request, nomor_anggota):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    form = AnggotaForm(request.POST or None, instance=anggota)

    if form.is_valid():
        form.save()
        messages.success(request, "Anggota berhasil diperbarui.")
        return redirect("anggota:kelola_akun")

    return render(request, "kelola_akun/Form/form_anggota.html", {
        "form": form,
        "judul": "Edit Anggota"
    })


@login_required
def hapus_anggota(request, nomor_anggota):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    anggota.delete()
    messages.success(request, "Anggota berhasil dihapus.")
    return redirect("anggota:kelola_akun")

def detail_anggota(request, nomor_anggota):
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

    context = {
        "anggota": anggota,
    }
    return render(request, "kelola_akun/detail/detail_anggota.html", context)


# -- API VALIDASI -- #
@login_required
def cek_email(request):
    email = request.GET.get("email", "")
    return JsonResponse({
        "exists": Anggota.objects.filter(email=email).exists()
    })


def _thin_border(left=True, right=True, top=True, bottom=True):
    thin = Side(style="thin")
    no = Side(style=None)
    return Border(
        left=thin if left else no,
        right=thin if right else no,
        top=thin if top else no,
        bottom=thin if bottom else no,
    )


def _header_fill():
    # Theme color 6 (light blue/grey header) — matched from original file
    fill = PatternFill(fill_type="solid")
    fill.fgColor.theme = 6
    fill.fgColor.type = "theme"
    return fill

@login_required
def export_excel_anggota(request):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")
 
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
 
    # Lebar kolom (exact match dari template)
    col_widths = {
        "A": 12.140625, "B": 14.42578125, "C": 27.0,      "D": 6.85546875,
        "E": 5.0,        "F": 28.0,        "G": 28.0,      "H": 24.5703125,
        "I": 16.5703125, "J": 9.140625,    "K": 13.0,      "L": 12.5703125,
        "M": 12.140625,  "N": 12.7109375,  "O": 9.140625,
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width
 
    ws.row_dimensions[1].height = 18.75
    ws.row_dimensions[2].height = 15.75
    ws.row_dimensions[4].height = 75.0
 
    # Row 1 — judul utama
    ws.merge_cells("A1:O1")
    ws["A1"] = "ANGGOTA PERKUMPULAN KOPERASI"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
 
    # Row 2 — section header
    ws.merge_cells("A2:K2")
    ws["A2"] = "DITERIMA SEBAGAI ANGGOTA "
    ws["A2"].font = Font(bold=True, size=12)
    ws["A2"].fill = _header_fill()
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws["A2"].border = _thin_border()
    ws["K2"].border = Border(right=Side(style="thin"))
 
    ws.merge_cells("L2:O2")
    ws["L2"] = "BERHENTI SEBAGAI ANGGOTA"
    ws["L2"].font = Font(bold=True, size=12)
    ws["L2"].fill = _header_fill()
    ws["L2"].alignment = Alignment(horizontal="center", vertical="center")
    ws["L2"].border = _thin_border()
 
    # Row 3 — kosong (spacer)
 
    # Row 4 — header kolom
    headers = [
        ("A4", "Nomor Urut",                     False),
        ("B4", "NA",                              False),
        ("C4", "Nama",                            False),
        ("D4", "Umur",                            False),
        ("E4", "L/P",                             False),
        ("F4", "Pekerjaan",                       False),
        ("G4", "Alamat",                          False),
        ("H4", "Tanggal, Tahun, Bulan",           True),
        ("I4", "Tanggal masuk menjadi Anggota",   True),
        ("J4", "Tanda Tangan Anggota",            True),
        ("K4", "Tanda Tangan Ketua dan Tanggal",  True),
        ("L4", "Tanggal minta Berhenti",          True),
        ("M4", "Tanggal berhenti/dipecat",        True),
        ("N4", "Sebab-sebab berhenti/dipecat",    True),
        ("O4", "Tanda Tangan dan Tanggal",        True),
    ]
    for coord, text, wrap in headers:
        cell = ws[coord]
        cell.value = text
        cell.fill = _header_fill()
        cell.font = Font(size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=wrap)
        cell.border = _thin_border()
 
    # Row 5 — nomor kolom
    col_numbers = {
        "A5": 1,  "B5": None, "C5": 2,  "D5": 3,  "E5": 4,
        "F5": 5,  "G5": 6,    "H5": 7,  "I5": 8,  "J5": 9,
        "K5": 10, "L5": 11,   "M5": 12, "N5": 13, "O5": 14,
    }
    for coord, val in col_numbers.items():
        cell = ws[coord]
        cell.value = val
        cell.font = Font(size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _thin_border()
 
    # Row 6+ — data anggota
    for idx, anggota in enumerate(Anggota.objects.all().order_by("nomor_anggota"), start=1):
        row = idx + 5
        ws.row_dimensions[row].height = 60.0
 
        is_aktif = anggota.status == "aktif"
 
        # Nama: kuning = AKTIF, tanpa fill = NONAKTIF (sesuai konvensi file asli)
        nama_fill = (
            PatternFill(fill_type="solid", fgColor="FFFF00")
            if is_aktif
            else PatternFill(fill_type=None)
        )
 
        jk_export = (
            "L" if anggota.jenis_kelamin == "Laki-laki"
            else "P" if anggota.jenis_kelamin == "Perempuan"
            else anggota.jenis_kelamin
        )
 
        tgl_daftar_str   = anggota.tanggal_daftar.strftime("%d-%m-%Y")   if anggota.tanggal_daftar   else None
        tgl_nonaktif_str = anggota.tanggal_nonaktif.strftime("%d-%m-%Y") if anggota.tanggal_nonaktif else None
        alasan           = anggota.alasan_nonaktif if not is_aktif else None
 
        # (col_letter, value, halign, wrap, fill)
        row_data = [
            ("A", idx,                          "center", False, PatternFill(fill_type=None)),
            ("B", anggota.nomor_anggota,        "center", False, PatternFill(fill_type=None)),
            ("C", anggota.nama,                 "left",   False, nama_fill),
            ("D", getattr(anggota, "umur", None), "center", False, PatternFill(fill_type=None)),
            ("E", jk_export,                    "center", False, PatternFill(fill_type=None)),
            ("F", getattr(anggota, "pekerjaan", None) or "-", "center", False, PatternFill(fill_type=None)),
            ("G", anggota.alamat,               "center", True,  PatternFill(fill_type=None)),
            ("H", None,                         "center", True,  PatternFill(fill_type=None)),   # tanggal lahir — tidak ada di model
            ("I", tgl_daftar_str,               "center", False, PatternFill(fill_type=None)),   # tanggal_daftar
            ("J", None,                         "center", False, PatternFill(fill_type=None)),
            ("K", None,                         "center", False, PatternFill(fill_type=None)),
            ("L", tgl_nonaktif_str,             "center", False, PatternFill(fill_type=None)),   # tanggal_nonaktif
            ("M", tgl_nonaktif_str,             "center", False, PatternFill(fill_type=None)),   # tanggal_nonaktif
            ("N", alasan,                       "center", False, PatternFill(fill_type=None)),   # alasan_nonaktif
            ("O", None,                         "center", False, PatternFill(fill_type=None)),
        ]
 
        for col_letter, value, halign, wrap, fill in row_data:
            cell = ws[f"{col_letter}{row}"]
            cell.value = value
            cell.font = Font(size=11)
            cell.alignment = Alignment(horizontal=halign, vertical="center", wrap_text=wrap)
            cell.border = _thin_border()
            if fill.fill_type:
                cell.fill = fill
 
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Daftar_Anggota.xlsx"'
    wb.save(response)
    return response


# -- EXPORT PDF DATA ANGGOTA -- #
@login_required
def export_pdf_anggota(request):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="anggota_koperasi.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20, rightMargin=20, topMargin=30, bottomMargin=20
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontSize = 7

    data = [[
        "No. Anggota", "Nama", "NIP", "Alamat", "No. Telp",
        "Email", "JK", "Tgl Daftar", "Status", "Tgl Nonaktif", "Alasan"
    ]]

    for a in Anggota.objects.all().order_by("nomor_anggota"):
        data.append([
            a.nomor_anggota,
            Paragraph(a.nama or "-", normal),
            a.nip or "-",
            Paragraph(a.alamat or "-", normal),
            a.no_telp or "-",
            Paragraph(a.email or "-", normal),
            a.jenis_kelamin,
            a.tanggal_daftar.strftime("%d-%m-%Y") if a.tanggal_daftar else "-",
            a.status,
            a.tanggal_nonaktif.strftime("%d-%m-%Y") if a.tanggal_nonaktif else "-",
            Paragraph(a.alasan_nonaktif or "-", normal),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.yellow),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    doc.build([table])
    return response


# -- IMPORT EXCEL DATA ANGGOTA -- #
@login_required
def import_excel_anggota(request):
    if request.user.role not in ROLE_ADMIN:
        return redirect("dashboard")
 
    if request.method == "POST" and request.FILES.get("excel_file"):
        try:
            wb = load_workbook(request.FILES["excel_file"], data_only=True)
            ws = wb.active
        except Exception:
            messages.error(request, "File Excel tidak bisa dibaca")
            return redirect("anggota:kelola_akun")
 
        sukses = 0
        gagal  = 0
 
        # Baris 1=judul, 2=section header, 3=kosong, 4=header kolom, 5=nomor kolom
        # Data mulai baris 6
        for row in ws.iter_rows(min_row=6):
            try:
                nomor_anggota = str(row[1].value).strip() if row[1].value else None
                nama          = str(row[2].value).strip() if row[2].value else None
 
                if not nomor_anggota or not nama:
                    continue
 
                if not re.match(r"^NA\s*\d+", nomor_anggota):
                    continue
 
                # Jenis kelamin: L/P di file → Laki-laki/Perempuan di DB
                jk_raw = str(row[4].value).strip().upper() if row[4].value else ""
                if jk_raw == "L":
                    jenis_kelamin = "Laki-laki"
                elif jk_raw == "P":
                    jenis_kelamin = "Perempuan"
                else:
                    jenis_kelamin = "Laki-laki"
 
                umur      = row[3].value if isinstance(row[3].value, int) else None
                pekerjaan = str(row[5].value).strip() if row[5].value else "-"
                alamat    = str(row[6].value).strip() if row[6].value else "-"
 
                # Kolom I (index 8) = tanggal masuk menjadi anggota
                tgl_daftar = row[8].value
                if isinstance(tgl_daftar, datetime):
                    tgl_daftar = tgl_daftar.date()
                elif isinstance(tgl_daftar, str):
                    try:
                        tgl_daftar = datetime.strptime(tgl_daftar.strip(), "%d-%m-%Y").date()
                    except ValueError:
                        tgl_daftar = date.today()
                else:
                    tgl_daftar = date.today()
 
                # Kolom M (index 12) = tanggal berhenti/dipecat
                tgl_nonaktif = row[12].value
                if isinstance(tgl_nonaktif, datetime):
                    tgl_nonaktif = tgl_nonaktif.date()
                elif isinstance(tgl_nonaktif, str):
                    try:
                        tgl_nonaktif = datetime.strptime(tgl_nonaktif.strip(), "%d-%m-%Y").date()
                    except ValueError:
                        tgl_nonaktif = None
                else:
                    tgl_nonaktif = None
 
                # Kolom N (index 13) = sebab berhenti
                alasan_nonaktif = str(row[13].value).strip() if row[13].value else None
 
                # Status: nonaktif jika ada tanggal_nonaktif, aktif jika tidak
                status = "nonaktif" if tgl_nonaktif else "aktif"
 
                # Jika aktif, bersihkan data nonaktif
                if status == "aktif":
                    tgl_nonaktif    = None
                    alasan_nonaktif = None
 
                anggota, created = Anggota.objects.update_or_create(
                    nomor_anggota=nomor_anggota,
                    defaults={
                        "nama":             nama,
                        "umur":             umur,
                        "jenis_kelamin":    jenis_kelamin,
                        "pekerjaan":        pekerjaan,
                        "alamat":           alamat,
                        "tanggal_daftar":   tgl_daftar,
                        "tanggal_nonaktif": tgl_nonaktif,
                        "alasan_nonaktif":  alasan_nonaktif,
                        "status":           status,
                        "nip":              "-",
                        "no_telp":          "-",
                        "email":            "-",
                    }
                )
 
                if created:
                    anggota.set_password("12345")
                    anggota.save()
 
                sukses += 1
 
            except Exception:
                gagal += 1
 
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": gagal == 0,
                "imported": sukses,
                "failed": gagal,
                "errors": []
            })
        messages.success(request, f"Import selesai: {sukses} berhasil, {gagal} gagal")
        return redirect("anggota:kelola_akun")
 
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "imported": 0, "failed": 0, "errors": ["File Excel tidak valid"]})
    messages.error(request, "File Excel tidak valid")
    return redirect("anggota:kelola_akun")