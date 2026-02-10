from django.urls import path
from . import views

app_name = "laporan"

urlpatterns = [
    path("", views.laporan, name="laporan"),
    path("export/", views.export_laporan, name="export_laporan"),
]
