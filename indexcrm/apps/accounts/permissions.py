from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import UserRole

ROLE_LEVELS = {
    UserRole.CASHIER: 10,
    UserRole.MANAGER: 20,
    UserRole.ADMIN: 30,
    UserRole.OWNER: 40,
}


def user_role_codes(user, *, branch=None):
    if not getattr(user, "is_authenticated", False):
        return set()

    role_codes = {user.role}
    assignments = user.role_assignments.select_related("role").filter(
        is_active=True,
        role__is_active=True,
    )
    if branch is not None:
        assignments = assignments.filter(branch__in=[branch, None])

    role_codes.update(assignments.values_list("role__code", flat=True))
    return role_codes


def user_has_role(user, allowed_roles, *, branch=None):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return bool(user_role_codes(user, branch=branch).intersection(set(allowed_roles)))


def user_is_owner_or_admin(user):
    return user_has_role(user, [UserRole.OWNER, UserRole.ADMIN])


def user_has_minimum_role(user, minimum_role, *, branch=None):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True

    minimum_level = ROLE_LEVELS.get(minimum_role, 0)
    return any(
        ROLE_LEVELS.get(role_code, 0) >= minimum_level
        for role_code in user_role_codes(user, branch=branch)
    )


def user_has_permission(user, permission_code, *, branch=None):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user_has_role(user, [UserRole.OWNER, UserRole.ADMIN]):
        return True

    assignments = user.role_assignments.select_related("role").filter(
        is_active=True,
        role__is_active=True,
    )
    if branch is not None:
        assignments = assignments.filter(branch__in=[branch, None])

    return (
        assignments.filter(
            role__permissions__code=permission_code,
            role__permissions__is_active=True,
        ).exists()
        or assignments.filter(
            role__permission_groups__permissions__code=permission_code,
            role__permission_groups__permissions__is_active=True,
            role__permission_groups__is_active=True,
        ).exists()
    )


class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return user_has_role(request.user, [UserRole.OWNER, UserRole.ADMIN])


class IsOwnerAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return user_has_minimum_role(request.user, UserRole.MANAGER)


class IsReadOnlyOrOwnerAdmin(BasePermission):
    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_is_owner_or_admin(request.user)


class IsReadOnlyOrOwnerAdminManager(BasePermission):
    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_minimum_role(request.user, UserRole.MANAGER)


class IsSelfOrOwnerAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        target_user = getattr(obj, "user", obj)
        return target_user == request.user or user_has_role(
            request.user, [UserRole.OWNER, UserRole.ADMIN]
        )


def user_branch_scope_ids(user):
    """Return None for unrestricted users, otherwise the branch UUIDs they may use."""
    if not getattr(user, "is_authenticated", False):
        return set()
    if user_is_owner_or_admin(user) or user.is_superuser:
        return None

    assignments = user.role_assignments.select_related("role").filter(
        is_active=True,
        role__is_active=True,
    )
    if assignments.filter(branch__isnull=True).exists():
        return None

    branch_ids = set(
        assignments.exclude(branch__isnull=True).values_list("branch_id", flat=True)
    )

    try:
        profile_branch_id = user.profile.branch_id
    except ObjectDoesNotExist:
        profile_branch_id = None
    if profile_branch_id:
        branch_ids.add(profile_branch_id)

    branch_ids.update(user.managed_branches.values_list("id", flat=True))
    return {branch_id for branch_id in branch_ids if branch_id}


def user_has_branch_access(user, branch=None, branch_id=None):
    branch_id = branch_id or getattr(branch, "id", None)
    if branch_id is None:
        return False

    branch_ids = user_branch_scope_ids(user)
    if branch_ids is None:
        return True
    return str(branch_id) in {str(allowed_branch_id) for allowed_branch_id in branch_ids}


def user_has_store_access(user, store):
    if user_is_owner_or_admin(user) or getattr(user, "is_superuser", False):
        return True
    if getattr(store, "owner_id", None) == getattr(user, "id", None):
        return True

    branch_ids = user_branch_scope_ids(user)
    if branch_ids is None:
        return True
    if not branch_ids:
        return False
    return store.branches.filter(id__in=branch_ids).exists()


def filter_queryset_by_branch_scope(queryset, user, branch_lookup):
    branch_ids = user_branch_scope_ids(user)
    if branch_ids is None:
        return queryset
    if not branch_ids:
        return queryset.none()
    return queryset.filter(**{f"{branch_lookup}__in": branch_ids})


def filter_queryset_by_store_scope(queryset, user, store_lookup=""):
    branch_ids = user_branch_scope_ids(user)
    if branch_ids is None:
        return queryset

    prefix = f"{store_lookup}__" if store_lookup else ""
    scope_filter = Q(**{f"{prefix}owner": user})
    if branch_ids:
        scope_filter |= Q(**{f"{prefix}branches__id__in": branch_ids})
    return queryset.filter(scope_filter).distinct()
