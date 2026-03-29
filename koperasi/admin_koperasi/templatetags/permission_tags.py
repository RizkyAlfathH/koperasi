from django import template
from admin_koperasi.models import RolePermission

register = template.Library()

@register.simple_tag
def can_access(user, code):
    if user.role in ["admin"]:
        return True

    return RolePermission.objects.filter(
        role=user.role,
        permission_code=code
    ).exists()
