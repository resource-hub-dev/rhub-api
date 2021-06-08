import logging

import sqlalchemy
from connexion import problem
from keycloak import KeycloakGetError
from werkzeug.exceptions import Forbidden

from rhub.lab import model
from rhub.api import db, get_keycloak, ADMIN_ROLE
from rhub.api.utils import row2dict
from rhub.auth.keycloak import problem_from_keycloak_error


logger = logging.getLogger(__name__)


def list_regions(user):
    if get_keycloak().user_check_role(user, ADMIN_ROLE):
        regions = model.Region.query.all()
    else:
        user_groups = [group['id'] for group in get_keycloak().user_group_list(user)]
        regions = model.Region.query.filter(sqlalchemy.or_(
            model.Region.users_group.is_(None),
            model.Region.users_group.in_(user_groups),
            model.Region.owner_group.in_(user_groups),
        ))

    return [row2dict(region) for region in regions]


def create_region(body, user):
    try:
        owners_id = get_keycloak().group_create({
            'name': f'{body["name"]}-owners',
        })
        logger.info(f'Created owners group {owners_id}')
        body['owner_group'] = owners_id

        get_keycloak().group_user_add(user, owners_id)
        logger.info(f'Added {user} to owners group {owners_id}')

    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error',
                       f'Failed to create owner group in Keycloak, {e}')

    if 'quota' in body:
        if body['quota']:
            quota = model.Quota(**body['quota'])
        else:
            quota = None
        del body['quota']
    else:
        quota = None

    try:
        if body.get('users_group'):
            get_keycloak().group_get(body['users_group'])
    except KeycloakGetError as e:
        logger.exception(e)
        return problem(400, 'Users group does not exist',
                       f'Users group {body["users_group"]} does not exist in Keycloak, '
                       'you have to create group first or use existing group.')

    region = model.Region(**body)
    region.quota = quota

    db.session.add(region)
    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) created by user {user}')

    return row2dict(region)


def get_region(id, user):
    region = model.Region.query.get(id)
    if not region:
        return problem(404, 'Not Found', f'Region {id} does not exist')

    if region.users_group is not None:
        if not get_keycloak().user_check_role(user, ADMIN_ROLE):
            if not get_keycloak().user_check_group_any(
                    user, [region.users_group, region.owner_group]):
                raise Forbidden("You don't have access to this region.")

    return row2dict(region)


def update_region(id, body, user):
    region = model.Region.query.get(id)
    if not region:
        return problem(404, 'Not Found', f'Region {id} does not exist')

    if not get_keycloak().user_check_role(user, ADMIN_ROLE):
        if not get_keycloak().user_check_group(user, region.owner_group):
            raise Forbidden("You don't have write access to this region.")

    try:
        if body.get('users_group'):
            get_keycloak().group_get(body['users_group'])
    except KeycloakGetError as e:
        logger.exception(e)
        return problem(400, 'Users group does not exist',
                       f'Users group {body["users_group"]} does not exist in Keycloak, '
                       'you have to create group first or use existing group.')

    if 'quota' in body:
        if body['quota']:
            if region.quota is None:
                region.quota = model.Quota(**body['quota'])
            else:
                for k, v in body['quota'].items():
                    setattr(region.quota, k, v)
        else:
            region.quota = None
        del body['quota']

    for k, v in body.items():
        setattr(region, k, v)

    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) updated by user {user}')

    return row2dict(region)


def delete_region(id, user):
    region = model.Region.query.get(id)
    if not region:
        return problem(404, 'Not Found', f'Region {id} does not exist')

    if not get_keycloak().user_check_role(user, ADMIN_ROLE):
        if not get_keycloak().user_check_group(user, region.owner_group):
            raise Forbidden("You don't have write access to this region.")

    db.session.delete(region)

    try:
        owner_group = get_keycloak().group_get(region.owner_group)
        get_keycloak().group_delete(owner_group['id'])
        logger.info(f'Deleted owners group {owner_group["id"]}')

    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error',
                       f'Failed to delete owner group in Keycloak, {e}')

    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) deleted by user {user}')


def list_region_templates(id):
    raise NotImplementedError


def add_region_template(id, body):
    raise NotImplementedError


def delete_region_template(id, body):
    raise NotImplementedError
