import functools

from werkzeug.exceptions import Forbidden

from rhub.api import get_keycloak
from rhub.auth import ADMIN_ROLE


def user_is_admin(user_id):
    """Check if user is admin, has ADMIN_ROLE role."""
    return get_keycloak().user_check_role(user_id, ADMIN_ROLE)


def route_require_role(*roles,
                       forbidden_message="You don't have permissions for this."):
    """
    Decorator to require user role to use API endpoint route. If user doesn't
    have any of the specified role Forbidden exception will be raised to prevent
    user from using the endpoint.

    Decorated handler must have `user` in its parameters!
    """
    if not roles:
        raise ValueError('At least one role is required')

    def decorator(fn):
        if 'user' not in fn.__code__.co_varnames:
            raise ValueError(
                f'Function `{fn.__module__}.{fn.__name__}` does not accept `user` '
                'in arguments! `user` argument is required to get user in decorators.'
            )

        @functools.wraps(fn)
        def inner(*args, **kwargs):
            user = kwargs['user']
            if not user or not any(get_keycloak().user_check_role(user, role)
                                   for role in roles):
                raise Forbidden(forbidden_message)
            return fn(*args, **kwargs)
        return inner

    return decorator


def route_require_admin(fn):
    """Shortcut to require admin role to use API endpoint."""
    return route_require_role(ADMIN_ROLE)(fn)
