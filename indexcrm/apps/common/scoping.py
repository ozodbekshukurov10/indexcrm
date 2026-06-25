from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import (
    user_branch_scope_ids,
    user_has_branch_access,
    user_has_store_access,
    user_is_owner_or_admin,
)


BRANCH_SCOPE_ERROR = "You do not have access to this branch."
STORE_SCOPE_ERROR = "You do not have access to this store."
SCOPE_ERROR_CODE = "scope_denied"


def _scope_error(message):
    return {"code": SCOPE_ERROR_CODE, "message": message, "detail": message}


def require_branch_access(user, branch):
    if not user_has_branch_access(user, branch=branch):
        raise PermissionDenied(_scope_error(BRANCH_SCOPE_ERROR))


def require_store_access(user, store):
    if not user_has_store_access(user, store):
        raise PermissionDenied(_scope_error(STORE_SCOPE_ERROR))


def require_warehouse_access(user, warehouse):
    require_branch_access(user, warehouse.branch)


def require_cashbox_access(user, cashbox):
    require_branch_access(user, cashbox.branch)


def scoped_branch_query_value(user, requested_branch):
    if user_is_owner_or_admin(user) or getattr(user, "is_superuser", False):
        return requested_branch

    branch_ids = user_branch_scope_ids(user)
    if branch_ids is None:
        return requested_branch

    if requested_branch:
        if str(requested_branch) in {str(branch_id) for branch_id in branch_ids}:
            return requested_branch
        raise PermissionDenied(BRANCH_SCOPE_ERROR)

    if not branch_ids:
        raise PermissionDenied(_scope_error("No branch is assigned to this user."))
    if len(branch_ids) == 1:
        return next(iter(branch_ids))
    raise PermissionDenied(
        _scope_error("Choose a branch before viewing this scoped report.")
    )
