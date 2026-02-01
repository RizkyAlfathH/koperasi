from admin_koperasi.models import RolePermission

def has_page_permission(user, code):
    # Ketua & admin bebas
    if user.role in ["admin"]:
        return True

    return RolePermission.objects.filter(
        role=user.role,
        permission_code=code
    ).exists()
