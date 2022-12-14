import logging

import injector
import ldap3


logger = logging.getLogger(__name__)


class LdapClient:
    def __init__(self, config):
        self.config = config

    def _connect(self):
        return ldap3.Connection(
            ldap3.Server(self.config['server']),
            auto_bind=True,
        )

    def get(self, dn):
        conn = self._connect()
        conn.search(dn, '(objectClass=*)', search_scope=ldap3.BASE, attributes=['*'])
        return conn.entries

    def search(self, base, query):
        conn = self._connect()
        conn.search(base, query, search_scope=ldap3.SUBTREE, attributes=['*'])
        return conn.entries

    def search_users(self, query):
        object_class = '(objectClass=person)'
        users_filter = self.config.get('users_filter', '')
        return self.search(
            self.config['users_base'],
            f'(&{object_class}{users_filter}{query})',
        )

    def search_groups(self, query):
        object_class = '(|(objectClass=groupOfNames)(objectClass=groupOfUniqueNames))'
        groups_filter = self.config.get('groups_filter', '')
        return self.search(
            self.config['groups_base'],
            f'(&{object_class}{groups_filter}{query})',
        )

    def _user_to_dict(self, user):
        user_dict = {
            'ldap_dn': user.entry_dn,
            'groups': [{'ldap_dn': i} for i in user['memberOf'].value],
        }

        for dict_key, ldap_attr in self.config['user_attrs'].items():
            if dict_key == 'ssh_keys':
                if ldap_attr in user:
                    user_dict[dict_key] = self._extract_ssh_keys(user, ldap_attr)
                else:
                    user_dict[dict_key] = []
            else:
                if ldap_attr in user:
                    user_dict[dict_key] = user[ldap_attr].value
                else:
                    user_dict[dict_key] = None

        return user_dict

    def _group_to_dict(self, group):
        def extract_users(group):
            users_set = set()
            for k in ['member', 'uniqueMember']:
                if k in group:
                    users_set |= set(group[k].value)
            return list(users_set)

        group_dict = {
            'ldap_dn': group.entry_dn,
            'users': extract_users(group),
        }

        for dict_key, ldap_attr in self.config['group_attrs'].items():
            if ldap_attr in group:
                group_dict[dict_key] = group[ldap_attr].value
            else:
                group_dict[dict_key] = None

        return group_dict

    def get_user(self, ldap_dn):
        users = self.get(ldap_dn)
        if len(users) != 1:
            raise ValueError(f'User {ldap_dn=} not found.')
        return self._user_to_dict(users[0])

    def get_user_by_uuid(self, external_uuid):
        users = self.search_users(self.config['users_search'].format(external_uuid))
        if len(users) != 1:
            raise ValueError(f'User {external_uuid=} not found in LDAP.')
        return self._user_to_dict(users[0])

    def get_group(self, ldap_dn):
        groups = self.get(ldap_dn)
        if len(groups) != 1:
            raise ValueError(f'Group {ldap_dn=} not found in LDAP.')
        return self._group_to_dict(groups[0])

    def _extract_ssh_keys(self, entry, attr):
        values = entry[attr].value
        if not isinstance(values, list):
            values = [values]

        def remove_ssh_key_comment(ssh_key):
            return ' '.join(ssh_key.split()[:2])

        return [remove_ssh_key_comment(i.decode()) for i in values]


class LdapModule(injector.Module):
    def __init__(self, app):
        self.app = app

    def configure(self, binder):
        try:
            binder.bind(
                LdapClient,
                to=self._create_ldap_client(),
                scope=injector.singleton,
            )
        except Exception:
            logging.exception('Failed to create LDAP client.')

    def _create_ldap_client(self):
        return LdapClient(self.app.config['LDAP'])
