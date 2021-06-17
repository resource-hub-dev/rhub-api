import json

from connexion import problem
from keycloak import KeycloakOpenID, KeycloakAdmin


class KeycloakClient:
    """Wrapper for Keycloak OpenID and admin clients."""

    def __init__(self, server, resource, realm, secret, admin_user, admin_pass):
        self.openid = KeycloakOpenID(
            server_url=server,
            client_id=resource,
            realm_name=realm,
            client_secret_key=secret,
        )

        self.admin = KeycloakAdmin(
            server_url=server,
            client_id=resource,
            realm_name=realm,
            client_secret_key=secret,
            username=admin_user,
            password=admin_pass,
        )

    def login(self, username, password):
        return self.openid.token(username, password, totp=None)

    def token_refresh(self, refresh_token):
        return self.openid.refresh_token(refresh_token)

    def token_info(self, token):
        return self.openid.introspect(token)

    def user_list(self, query=None):
        return self.admin.get_users(query)

    def user_get(self, user_id):
        return self.admin.get_user(user_id)

    def user_create(self, data):
        data = data.copy()
        data.setdefault('enabled', True)

        if 'password' in data:
            data['credentials'] = [
                {'type': 'password', 'value': data['password']},
            ]
            del data['password']

        return self.admin.create_user(data)

    def user_update(self, user_id, data):
        data = data.copy()

        if 'password' in data:
            data['credentials'] = [
                {'type': 'password', 'value': data['password']},
            ]
            del data['password']

        self.admin.update_user(user_id, data)

    def user_delete(self, user_id):
        self.admin.delete_user(user_id)

    def user_group_list(self, user_id):
        """Get list of groups user belongs to."""
        return self.admin.get_user_groups(user_id)

    def user_role_list(self, user_id):
        """
        Get set of all user roles !! ROLE NAMES !!, directly assigned and also
        inherited from a group.
        """
        roles = set()

        # directly assigned roles
        roles = {i['name'] for i in self.admin.get_realm_roles_of_user(user_id)}

        # iherited roles from group
        for group in self.user_group_list(user_id):
            roles |= {i['name'] for i in self.admin.get_group_realm_roles(group['id'])}

        return roles

    def user_check_group(self, user_id, group_id):
        """Check if user belongs to the given group."""
        return self.user_check_group_any(user_id, [group_id])

    def user_check_group_any(self, user_id, group_id_list):
        """Check if user belongs to any of the given groups."""
        return any(group['id'] in group_id_list
                   for group in self.user_group_list(user_id))

    def user_check_role(self, user_id, role_name):
        """Check if user has role."""
        return role_name in self.user_role_list(user_id)

    def group_list(self):
        return self.admin.get_groups()

    def group_get(self, group_id):
        return self.admin.get_group(group_id)

    def group_create(self, data):
        # `create_group` always returns b''
        self.admin.create_group(data)

        for group in self.group_list():
            if group['name'] == data['name']:
                return group['id']

    def group_update(self, group_id, data):
        self.admin.update_group(group_id, data)

    def group_delete(self, group_id):
        self.admin.delete_group(group_id)

    def group_user_list(self, group_id):
        """Get list of users in group."""
        return self.admin.get_group_members(group_id)

    def group_user_add(self, user_id, group_id):
        """Add user to group."""
        self.admin.group_user_add(user_id, group_id)

    def group_user_remove(self, user_id, group_id):
        """Remove user from group."""
        self.admin.group_user_remove(user_id, group_id)

    def group_role_list(self, group_id):
        return self.admin.get_group_realm_roles(group_id)

    def group_role_add(self, role_name, group_id):
        """Add role to group. !! Role NAME, not ID !!"""
        role = self.role_get(role_name)
        self.admin.assign_group_realm_roles(group_id, [role])

    def group_role_remove(self, role_name, group_id):
        """Remove role from group. !! Role NAME, not ID !!"""
        role = self.role_get(role_name)
        self.admin.delete_group_realm_roles(group_id, [role])

    def role_list(self):
        return self.admin.get_realm_roles()

    def role_get(self, role_name):
        """Get role by name. !! NAME, not ID !!"""
        return self.admin.get_realm_role(role_name)

    def role_create(self, data):
        # `create_role` always returns b''
        self.admin.create_realm_role(data)

        for role in self.role_list():
            if role['name'] == data['name']:
                return role['name']

    def role_update(self, role_id, data):
        self.admin.update_realm_role(role_id, data)

    def role_delete(self, role_id):
        self.admin.delete_realm_role(role_id)


def problem_from_keycloak_error(e):
    """Utility to create `connexion.problem` from `KeycloakError` exception."""
    detail = e.response_body.decode()
    ext = None
    try:
        ext = json.loads(detail)
        if 'message' in ext:
            detail = ext.pop('message')
        elif 'error' in ext:
            detail = ext.pop('error')
    except json.JSONDecodeError:
        pass
    return problem(e.response_code, 'Keycloak Error', detail, ext=ext)
