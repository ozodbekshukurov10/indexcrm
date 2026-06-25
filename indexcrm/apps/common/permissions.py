from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole
from apps.accounts.permissions import user_has_role


class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return user_has_role(request.user, [UserRole.OWNER, UserRole.ADMIN])
