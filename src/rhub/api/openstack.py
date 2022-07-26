import logging

from connexion import problem
from flask import url_for
from werkzeug.exceptions import Forbidden

from rhub.api import DEFAULT_PAGE_LIMIT, db, di
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient, KeycloakGetError
from rhub.openstack import model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/openstack'
"""Vault path prefix to create new credentials in Vault."""


def _cloud_href(cloud):
    href = {
        'cloud': url_for('.rhub_api_openstack_cloud_get',
                         cloud_id=cloud.id),
        'owner_group': url_for('.rhub_api_auth_group_get_group',
                               group_id=cloud.owner_group_id)
    }
    return href


def _project_href(project):
    href = {
        'project': url_for('.rhub_api_openstack_project_get',
                           project_id=project.id),
        'project_limits': url_for('.rhub_api_openstack_project_limits_get',
                                  project_id=project.id),
        'cloud': url_for('.rhub_api_openstack_cloud_get',
                         cloud_id=project.cloud_id),
        'owner': url_for('.rhub_api_auth_user_get_user',
                         user_id=project.owner_id)
    }
    return href


def _user_can_access_project(project, user_id):
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if project.owner_id == user_id:
        return True
    if keycloak.user_check_group(user_id, project.cloud.owner_group_id):
        return True
    return False


def cloud_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    clouds = model.Cloud.query

    if 'name' in filter_:
        clouds = clouds.filter(model.Cloud.name.ilike(filter_['name']))

    if 'owner_group_id' in filter_:
        clouds = clouds.filter(model.Cloud.owner_group_id == filter_['owner_group_id'])

    if sort:
        clouds = db_sort(clouds, sort)

    return {
        'data': [
            cloud.to_dict() | {'_href': _cloud_href(cloud)}
            for cloud in clouds.limit(limit).offset(page * limit)
        ],
        'total': clouds.count(),
    }


def cloud_create(keycloak: KeycloakClient, vault: Vault, body, user):
    try:
        if body.get('owner_group_id'):
            keycloak.group_get(body['owner_group_id'])
    except KeycloakGetError as e:
        logger.exception(e)
        return problem(
            400, 'Owner group does not exist',
            f'Owner group {body["owner_group_id"]} does not exist in Keycloak, '
            'you have to create group first or use existing group.'
        )

    query = model.Cloud.query.filter(model.Cloud.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Cloud with name {body["name"]!r} already exists',
        )

    credentials = body['credentials']
    if not isinstance(credentials, str):
        credentials_path = f'{VAULT_PATH_PREFIX}/{body["name"]}'
        vault.write(credentials_path, credentials)
        body['credentials'] = credentials_path

    cloud = model.Cloud.from_dict(body)

    db.session.add(cloud)
    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) created by user {user}')

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_get(cloud_id):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')
    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_update(keycloak: KeycloakClient, vault: Vault, cloud_id, body, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, cloud.owner_group_id):
            raise Forbidden('You are not owner of this cloud.')

    credentials = body.get('credentials', cloud.credentials)
    if not isinstance(credentials, str):
        vault.write(cloud.credentials, credentials)
        del body['credentials']

    cloud.update_from_dict(body)

    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) updated by user {user}')

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_delete(keycloak: KeycloakClient, cloud_id, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, cloud.owner_group_id):
            raise Forbidden('You are not owner of this cloud.')

    db.session.delete(cloud)
    db.session.commit()
    logger.info(f'Cloud {cloud.name} (id {cloud.id}) deleted by user {user}')


def project_list(keycloak: KeycloakClient,
                 user, filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    if keycloak.user_check_role(user, ADMIN_ROLE):
        projects = model.Project.query
    else:
        user_groups = [group['id'] for group in keycloak.user_group_list(user)]
        projects = model.Project.query.filter(
            db.or_(
                model.Project.owner_id == user,
                model.Cloud.owner_group_id.in_(user_groups),
            )
        )

    if 'cloud_id' in filter_:
        projects = projects.filter(model.Project.cloud_id == filter_['cloud_id'])

    if 'name' in filter_:
        projects = projects.filter(model.Project.name.ilike(filter_['name']))

    if 'owner_id' in filter_:
        projects = projects.filter(model.Project.owner_id == filter_['owner_id'])

    if sort:
        projects = db_sort(projects, sort, {
            'name': 'openstack_project.name'
        })

    return {
        'data': [
            project.to_dict() | {'_href': _project_href(project)}
            for project in projects.limit(limit).offset(page * limit)
        ],
        'total': projects.count(),
    }


def project_create(body, user):
    query = model.Project.query.filter(
        db.and_(
            model.Project.name == body['name'],
            model.Project.cloud_id == body['cloud_id'],
        )
    )
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Project with the same name {body["name"]!r} in the cloud '
            f'{body["cloud_id"]!r} already exists'
        )

    if 'owner_id' not in body:
        body['owner_id'] = user

    project = model.Project.from_dict(body)

    db.session.add(project)
    db.session.commit()
    logger.info(f'Project {project.name} (id {project.id}) created by user {user}')

    return project.to_dict() | {'_href': _project_href(project)}


def project_get(project_id, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    return project.to_dict() | {'_href': _project_href(project)}


def project_update(project_id, body, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    project.update_from_dict(body)

    db.session.commit()
    logger.info(f'Project {project.name} (id {project.id}) updated by user {user}')

    return project.to_dict() | {'_href': _project_href(project)}


def project_delete(project_id, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    db.session.delete(project)
    db.session.commit()
    logger.info(f'Project {project.name} (id {project.id}) deleted by user {user}')


def project_limits_get(project_id, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    return project.get_openstack_limits() | {'_href': _project_href(project)}
