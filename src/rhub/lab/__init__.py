import logging

import retrying

from rhub.api import get_keycloak


logger = logging.getLogger(__name__)


# This function must be idempotent. In container, it may be called on every
# start.
@retrying.retry(stop_max_attempt_number=3, wait_fixed=5000)
def init():
    keycloak = get_keycloak()

    groups = {group['name']: group for group in keycloak.group_list()}
    roles = {role['name']: role for role in keycloak.role_list()}

    if 'rhub-admin' not in groups:
        logger.info('Creating "rhub-admin" group')
        groups['rhub-admin'] = keycloak.group_create({'name': 'rhub-admin'})

    if 'rhub-admin' not in roles:
        logger.info('Creating "rhub-admin" role')
        roles['rhub-admin'] = keycloak.role_create({'name': 'rhub-admin'})

    if not any(role['name'] == 'rhub-admin'
               for role in keycloak.group_role_list(groups['rhub-admin']['id'])):
        logger.info('Adding "rhub-admin" role to "rhub-admin" group')
        keycloak.group_role_add('rhub-admin', groups['rhub-admin']['id'])

    for i in ['lab-owner', 'policy-owner']:
        if i not in roles:
            logger.info(f'Creating "{i}" role')
            roles[i] = keycloak.role_create({'name': i})

    if not keycloak.user_list({'username': 'admin'}):
        logger.info('Creating "admin" account')
        keycloak.user_create({
            'username': 'admin',
            'email': 'nobody@redhat.com',
            'firstName': 'Admin',
            'lastName': 'RHub',
        })

    admin_user = keycloak.user_list({'username': 'admin'})[0]
    if not any(group['name'] == 'rhub-admin'
               for group in keycloak.user_group_list(admin_user['id'])):
        logger.info('Adding "admin" user to "rhub-admin" group')
        keycloak.group_user_add(admin_user['id'], groups['rhub-admin']['id'])
