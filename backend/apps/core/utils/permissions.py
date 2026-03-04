from functools import wraps
from django.http import JsonResponse
from apps.core.model.authorize.models import UserAuth
from apps.configuration.models import UserPermissionDetail


def get_user_actions(user):
    """Return a set of action strings where status=True for user's assigned permissions."""
    if not user or not user.is_authenticated:
        return set()

    # root user bypass: user with id == 1 has all permissions
    try:
        if getattr(user, 'id', None) == 1:
            all_actions = UserPermissionDetail.objects.filter(status=True).values_list('action', flat=True).distinct()
            return set(a for a in all_actions if a)
    except Exception:
        # fall back to normal path on any error
        pass

    qs = UserAuth.objects.filter(user=user, user_permission__isnull=False).select_related('user_permission')
    actions = set()
    for ua in qs:
        details = UserPermissionDetail.objects.filter(user_permission=ua.user_permission, status=True).values_list('action', flat=True)
        for a in details:
            actions.add(a)
    return actions


def require_action(*action_names):
    # Support calling with one or more action strings: @require_action('A') or @require_action('A','B')
    # If used incorrectly as @require_action (no args), the first arg will be the view function.
    if len(action_names) == 1 and callable(action_names[0]):
        raise TypeError("require_action must be called with action name(s), e.g. @require_action('Action')")

    # normalize allowed actions into a set
    allowed_actions = set()
    for a in action_names:
        if isinstance(a, (list, tuple, set)):
            allowed_actions.update(a)
        else:
            allowed_actions.add(a)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'detail': 'Authentication required'}, status=401)

            try:
                if getattr(request.user, 'id', None) == 1:
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass

            user_actions = get_user_actions(request.user)
            if not (allowed_actions & user_actions):
                return JsonResponse({'detail': 'Access Denied'}, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
