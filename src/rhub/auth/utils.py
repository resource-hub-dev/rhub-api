import base64
import functools
import struct

from werkzeug.exceptions import Forbidden

from rhub.auth import model


def is_user_in_group(user_id, *group_name):
    q = (
        model.User.query
        .filter(model.User.id == user_id)
        .join(model.Group, model.User.groups)
        .filter(model.Group.name.in_(group_name))
    )
    return q.count() > 0


def user_is_admin(user_id):
    """Check if user is admin, belongs to :const:`rhub.auth.ADMIN_GROUP` group."""
    return model.User.query.get(user_id).is_admin


def user_group_ids(user_id):
    """Returns a set of group IDs to which the user belongs."""
    q = model.UserGroup.query.filter(model.UserGroup.user_id == user_id)
    return set(row.group_id for row in q)


def route_require_role(role: model.Role,
                       forbidden_message="You don't have permissions for this."):
    """
    Decorator to require user role to use API endpoint route. If user doesn't
    have specified role and the user is not admin, Forbidden exception will be
    raised to prevent user from using the endpoint.

    Decorated handler must have `user` in its parameters!
    """
    def decorator(fn):
        if 'user' not in fn.__code__.co_varnames:
            raise ValueError(
                f'Function `{fn.__module__}.{fn.__name__}` does not accept `user` '
                'in arguments! `user` argument is required to get user in decorators.'
            )

        @functools.wraps(fn)
        def inner(*args, **kwargs):
            user = model.User.query.get(kwargs['user'])
            if role not in user.roles and not user.is_admin:
                raise Forbidden(forbidden_message)
            return fn(*args, **kwargs)
        return inner

    return decorator


def route_require_admin(fn):
    """
    Shortcut to require admin role (:const:`rhub.auth.model.Role.ADMIN`) to use
    API endpoint.
    """
    return route_require_role(model.Role.ADMIN)(fn)


def normalize_ssh_key(ssh_key):
    """
    Normalize SSH key format - can fix malformed SSH keys and removes comment
    from the key.
    """
    # RFC 4253, Section 6.6; RFC 4251, Section 5
    def norm(blob_b64):
        blob = base64.b64decode(blob_b64)
        key_type_len, *_ = struct.unpack('!I', blob[:4])
        key_type = blob[4:4 + key_type_len].decode('ASCII')
        return f'{key_type} {blob_b64}'

    for i in ssh_key.split():
        try:
            return norm(i)
        except Exception:
            pass

    raise ValueError('invalid SSH key')
