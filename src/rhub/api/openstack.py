import logging

import sqlalchemy
from connexion import problem
from flask import url_for
from werkzeug.exceptions import Forbidden

from rhub import auth
from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import model as auth_model
from rhub.openstack import model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/openstack'
"""Vault path prefix to create new credentials in Vault."""


def _cloud_href(cloud):
    href = {
        'cloud': url_for('.rhub_api_openstack_cloud_get',
                         cloud_id=cloud.id),
        'owner_group': url_for('.rhub_api_auth_group_group_get',
                               group_id=cloud.owner_group_id),
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
        'owner': url_for('.rhub_api_auth_user_user_get',
                         user_id=project.owner_id),
    }
    if project.group:
        href['group'] = url_for('.rhub_api_auth_group_group_get',
                                group_id=project.group_id)
    return href


def _user_can_access_project(project, user_id):
    if auth.utils.user_is_admin(user_id):
        return True
    if project.owner_id == user_id:
        return True
    if project.cloud.owner_group_id in auth.utils.user_group_ids(user_id):
        return True
    return False


def cloud_list(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    clouds = model.Cloud.query

    if 'name' in filter_:
        clouds = clouds.filter(model.Cloud.name.ilike(filter_['name']))

    if 'owner_group_id' in filter_:
        clouds = clouds.filter(model.Cloud.owner_group_id == filter_['owner_group_id'])

    if 'owner_group_name' in filter_:
        clouds = clouds.outerjoin(
            auth_model.Group,
            auth_model.Group.id == model.Cloud.owner_group_id,
        )
        clouds = clouds.filter(auth_model.Group.name == filter_['owner_group_name'])

    if sort:
        clouds = db_sort(clouds, sort)

    if sort:
        clouds = db_sort(clouds, sort)

    return {
        'data': [
            cloud.to_dict() | {'_href': _cloud_href(cloud)}
            for cloud in clouds.limit(limit).offset(page * limit)
        ],
        'total': clouds.count(),
    }


def cloud_create(vault: Vault, body, user):
    credentials = body.pop('credentials')
    if isinstance(credentials, str):
        body['credentials'] = credentials
    else:
        body['credentials'] = f'{VAULT_PATH_PREFIX}/{body["name"]}'

    cloud = model.Cloud.from_dict(body)

    db.session.add(cloud)
    db.session.flush()

    if isinstance(credentials, dict):
        vault.write(cloud.credentials, credentials)

    db.session.commit()

    logger.info(
        f'Cloud {cloud.name} (id {cloud.id}) created by user {user}',
        extra={'user_id': user, 'cloud_id': cloud.id},
    )

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_get(cloud_id):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')
    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_update(vault: Vault, cloud_id, body, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not auth.utils.user_is_admin(user):
        if cloud.owner_group_id not in auth.utils.user_group_ids(user):
            raise Forbidden('You are not owner of this cloud.')

    credentials = body.pop('credentials', None)
    if isinstance(credentials, str):
        cloud.credentials = credentials

    cloud.update_from_dict(body)
    db.session.flush()

    if isinstance(credentials, dict):
        vault.write(cloud.credentials, credentials)

    db.session.commit()

    logger.info(
        f'Cloud {cloud.name} (id {cloud.id}) updated by user {user}',
        extra={'user_id': user, 'cloud_id': cloud.id},
    )

    return cloud.to_dict() | {'_href': _cloud_href(cloud)}


def cloud_delete(cloud_id, user):
    cloud = model.Cloud.query.get(cloud_id)
    if not cloud:
        return problem(404, 'Not Found', f'Cloud {cloud_id} does not exist')

    if not auth.utils.user_is_admin(user):
        if cloud.owner_group_id not in auth.utils.user_group_ids(user):
            raise Forbidden('You are not owner of this cloud.')

    db.session.delete(cloud)
    db.session.commit()

    logger.info(
        f'Cloud {cloud.name} (id {cloud.id}) deleted by user {user}',
        extra={'user_id': user, 'cloud_id': cloud.id},
    )


def project_list(user, filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    if auth.utils.user_is_admin(user):
        projects = model.Project.query
    else:
        user_groups = auth.utils.user_group_ids(user)
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

    if 'owner_name' in filter_:
        owner = sqlalchemy.orm.aliased(auth_model.User)
        projects = projects.outerjoin(owner, owner.id == model.Project.owner_id)
        projects = projects.filter(owner.name == filter_['owner_name'])

    if 'group_id' in filter_:
        projects = projects.filter(model.Project.group_id == filter_['group_id'])

    if 'group_name' in filter_:
        group = sqlalchemy.orm.aliased(auth_model.Group)
        projects = projects.outerjoin(group, group.id == model.Project.group_id)
        projects = projects.filter(group.name == filter_['group_name'])

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
    project = model.Project.from_dict(body)

    db.session.add(project)
    db.session.commit()

    logger.info(
        f'Project {project.name} (id {project.id}) created by user {user}',
        extra={'user_id': user, 'project_id': project.id},
    )

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

    for key in ['name', 'cloud_id']:
        if key in body:
            return problem(400, 'Bad Request',
                           f'Project {key} field cannot be changed.')

    project.update_from_dict(body)

    db.session.commit()

    logger.info(
        f'Project {project.name} (id {project.id}) updated by user {user}',
        extra={'user_id': user, 'project_id': project.id},
    )

    return project.to_dict() | {'_href': _project_href(project)}


def project_delete(project_id, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    db.session.delete(project)
    db.session.commit()

    logger.info(
        f'Project {project.name} (id {project.id}) deleted by user {user}',
        extra={'user_id': user, 'project_id': project.id},
    )


def project_limits_get(project_id, user):
    project = model.Project.query.get(project_id)
    if not project:
        return problem(404, 'Not Found', f'Project {project_id} does not exist')

    if not _user_can_access_project(project, user):
        return problem(403, 'Forbidden', "You don't have access to this project.")

    return project.get_openstack_limits() | {'_href': _project_href(project)}
