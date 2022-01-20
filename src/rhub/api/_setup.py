import logging

import tenacity

from rhub.api import db, di
from rhub.auth import ADMIN_USER, ADMIN_GROUP, ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient
from rhub.tower import model as tower_model  # noqa: F401
from rhub.lab import SHAREDCLUSTER_USER, SHAREDCLUSTER_GROUP, SHAREDCLUSTER_ROLE
from rhub.lab import model as lab_model  # noqa: F401
from rhub.policies import model as policies_model  # noqa: F401
from rhub.scheduler import model as scheduler_model  # noqa: F401
from rhub.scheduler import jobs as scheduler_jobs


logger = logging.getLogger(__name__)


# This function must be idempotent. In container, it may be called on every
# start.
@tenacity.retry(wait=tenacity.wait_fixed(5000), stop=tenacity.stop_after_attempt(3))
def setup():
    db.create_all()

    keycloak = di.get(KeycloakClient)

    groups = {group['name']: group for group in keycloak.group_list()}
    roles = {role['name']: role for role in keycloak.role_list()}

    if ADMIN_GROUP not in groups:
        logger.info(f'Creating admin group "{ADMIN_GROUP}"')
        admin_group_id = keycloak.group_create({'name': ADMIN_GROUP})
        groups[ADMIN_GROUP] = keycloak.group_get(admin_group_id)

    if ADMIN_ROLE not in roles:
        logger.info(f'Creating admin role "{ADMIN_ROLE}"')
        admin_role_name = keycloak.role_create({'name': ADMIN_ROLE})
        roles[ADMIN_ROLE] = keycloak.role_get(admin_role_name)

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

    if SHAREDCLUSTER_GROUP not in groups:
        logger.info(f'Creating sharedcluster group "{SHAREDCLUSTER_GROUP}"')
        group_id = keycloak.group_create({'name': SHAREDCLUSTER_GROUP})
        groups[SHAREDCLUSTER_GROUP] = keycloak.group_get(group_id)

    if SHAREDCLUSTER_ROLE not in roles:
        logger.info(f'Creating sharedcluster role "{SHAREDCLUSTER_ROLE}"')
        role_name = keycloak.role_create({'name': SHAREDCLUSTER_ROLE})
        roles[SHAREDCLUSTER_ROLE] = keycloak.role_get(role_name)

    if not any(role['name'] == SHAREDCLUSTER_ROLE
               for role in keycloak.group_role_list(groups[SHAREDCLUSTER_GROUP]['id'])):
        logger.info(f'Adding sharedcluster role "{SHAREDCLUSTER_ROLE}" '
                    f'to sharedcluster group "{SHAREDCLUSTER_GROUP}"')
        keycloak.group_role_add(SHAREDCLUSTER_ROLE, groups[SHAREDCLUSTER_GROUP]['id'])

    if not keycloak.user_list({'username': SHAREDCLUSTER_USER}):
        logger.info(f'Creating sharedclusters account "{SHAREDCLUSTER_USER}"')
        keycloak.user_create({
            'username': SHAREDCLUSTER_USER,
            'email': f'nobody+{SHAREDCLUSTER_USER}@redhat.com',
            'firstName': 'Shared Cluster',
            'lastName': 'RHub',
        })

    sharedcluster_user = keycloak.user_list({'username': SHAREDCLUSTER_USER})[0]
    if not any(group['name'] == SHAREDCLUSTER_GROUP
               for group in keycloak.user_group_list(sharedcluster_user['id'])):
        logger.info(f'Adding sharedcluster user "{SHAREDCLUSTER_USER}" '
                    f'to sharedcluster group "{SHAREDCLUSTER_GROUP}"')
        keycloak.group_user_add(sharedcluster_user['id'],
                                groups[SHAREDCLUSTER_GROUP]['id'])

    query = scheduler_model.SchedulerCronJob.query.filter(
        scheduler_model.SchedulerCronJob.job_name
        == scheduler_jobs.delete_expired_clusters.name
    )
    if query.count() < 1:
        logger.info('Creating default delete_expired_clusters cron job.')
        row = scheduler_model.SchedulerCronJob(
            name='Delete expired clusters',
            description=(
                'Deletes clusters with expired `reservation_expiration` '
                'or `lifespan_expiration` in all regions.'
            ),
            enabled=True,
            time_expr='0 1 * * *',  # daily, 1 AM
            job_name=scheduler_jobs.delete_expired_clusters.name,
            job_params=None,
        )
        db.session.add(row)
        db.session.commit()
