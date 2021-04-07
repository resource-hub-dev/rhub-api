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

    def login(self, username, password, totp=None):
        return self.openid.token(username, password, totp=None)

    def token_refresh(self, refresh_token):
        return self.openid.refresh_token(refresh_token)

    def token_info(self, token):
        return self.openid.introspect(token)

    def user_info(self, user_id):
        return self.admin.get_user(user_id)
