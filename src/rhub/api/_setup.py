import logging

import retrying

from rhub.api import db, get_keycloak
from rhub.auth import ADMIN_USER, ADMIN_GROUP, ADMIN_ROLE
from rhub.tower import model as tower_model  # noqa: F401
from rhub.lab import SHAREDCLUSTER_USER
from rhub.lab import model as lab_model  # noqa: F401
from rhub.policies import model as policies_model  # noqa: F401
from rhub.scheduler import model as scheduler_model  # noqa: F401


logger = logging.getLogger(__name__)


# This function must be idempotent. In container, it may be called on every
# start.
@retrying.retry(stop_max_attempt_number=3, wait_fixed=5000)
def setup():
    db.create_all()

    keycloak = get_keycloak()

    groups = {group['name']: group for group in keycloak.group_list()}
    roles = {role['name']: role for role in keycloak.role_list()}

    if ADMIN_GROUP not in groups:
        logger.info(f'Creating admin group "{ADMIN_GROUP}"')
        groups[ADMIN_GROUP] = keycloak.group_create({'name': ADMIN_GROUP})

    if ADMIN_ROLE not in roles:
        logger.info(f'Creating admin role "{ADMIN_ROLE}"')
        roles[ADMIN_ROLE] = keycloak.role_create({'name': ADMIN_ROLE})

    if not any(role['name'] == ADMIN_ROLE
               for role in keycloak.group_role_list(groups[ADMIN_GROUP]['id'])):
        logger.info(f'Adding admin role "{ADMIN_ROLE}" to admin group "{ADMIN_GROUP}"')
        keycloak.group_role_add(ADMIN_ROLE, groups[ADMIN_GROUP]['id'])

    if not keycloak.user_list({'username': ADMIN_USER}):
        logger.info(f'Creating admin account "{ADMIN_USER}"')
        keycloak.user_create({
            'username': ADMIN_USER,
            'email': 'nobody@redhat.com',
            'firstName': 'Admin',
            'lastName': 'RHub',
        })

    admin_user = keycloak.user_list({'username': ADMIN_USER})[0]
    if not any(group['name'] == ADMIN_GROUP
               for group in keycloak.user_group_list(admin_user['id'])):
        logger.info(f'Adding admin user "{ADMIN_USER}" to admin group "{ADMIN_GROUP}"')
        keycloak.group_user_add(admin_user['id'], groups[ADMIN_GROUP]['id'])

    for i in ['lab-owner', 'policy-owner']:
        if i not in roles:
            logger.info(f'Creating "{i}" role')
            roles[i] = keycloak.role_create({'name': i})

    if not keycloak.user_list({'username': SHAREDCLUSTER_USER}):
        logger.info(f'Creating sharedclusters account "{SHAREDCLUSTER_USER}"')
        keycloak.user_create({
            'username': SHAREDCLUSTER_USER,
            'email': f'nobody+{SHAREDCLUSTER_USER}@redhat.com',
            'firstName': 'Shared Cluster',
            'lastName': 'RHub',
        })
