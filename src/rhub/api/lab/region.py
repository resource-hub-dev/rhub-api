import logging

import sqlalchemy
import sqlalchemy.exc
from connexion import problem
from werkzeug.exceptions import Forbidden
import dpath.util as dpath

from rhub.lab import model
from rhub.tower import model as tower_model
from rhub.api import db, DEFAULT_PAGE_LIMIT
from rhub.api.vault import Vault
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/lab/region'
"""Vault path prefix to create new credentials in Vault."""


def list_regions(keycloak: KeycloakClient,
                 user, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    if keycloak.user_check_role(user, ADMIN_ROLE):
        regions = model.Region.query
    else:
        user_groups = [group['id'] for group in keycloak.user_group_list(user)]
        regions = model.Region.query.filter(sqlalchemy.or_(
            model.Region.users_group.is_(None),
            model.Region.users_group.in_(user_groups),
            model.Region.owner_group.in_(user_groups),
        ))

    if 'name' in filter_:
        regions = regions.filter(model.Region.name.ilike(filter_['name']))

    if 'location' in filter_:
        regions = regions.filter(model.Region.location.ilike(filter_['location']))

    return {
        'data': [
            region.to_dict() for region in regions.limit(limit).offset(page * limit)
        ],
        'total': regions.count(),
    }


def create_region(keycloak: KeycloakClient, vault: Vault, body, user):
    try:
        if body.get('users_group'):
            keycloak.group_get(body['users_group'])
    except KeycloakGetError as e:
        logger.exception(e)
        return problem(400, 'Users group does not exist',
                       f'Users group {body["users_group"]} does not exist in Keycloak, '
                       'you have to create group first or use existing group.')

    tower = tower_model.Server.query.get(body['tower_id'])
    if not tower:
        return problem(404, 'Not Found',
                       f'Tower instance with ID {body["tower_id"]} does not exist')

    query = model.Region.query.filter(model.Region.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Region with name {body["name"]!r} already exists',
        )

    try:
        owners_id = keycloak.group_create({
            'name': f'{body["name"]}-owners',
        })
        logger.info(f'Created owners group {owners_id}')
        body['owner_group'] = owners_id

        keycloak.group_user_add(user, owners_id)
        logger.info(f'Added {user} to owners group {owners_id}')

    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error',
                       f'Failed to create owner group in Keycloak, {e}')

    openstack_credentials = dpath.get(body, 'openstack/credentials')
    if not isinstance(openstack_credentials, str):
        openstack_credentials_path = f'{VAULT_PATH_PREFIX}/{body["name"]}/openstack'
        vault.write(openstack_credentials_path, openstack_credentials)
        dpath.set(body, 'openstack/credentials', openstack_credentials_path)

    satellite_credentials = dpath.get(body, 'satellite/credentials')
    if not isinstance(satellite_credentials, str):
        satellite_credentials_path = f'{VAULT_PATH_PREFIX}/{body["name"]}/satellite'
        vault.write(satellite_credentials_path, satellite_credentials)
        dpath.set(body, 'satellite/credentials', satellite_credentials_path)

    dns_server_key = dpath.get(body, 'dns_server/key')
    if not isinstance(dns_server_key, str):
        dns_server_key_path = f'{VAULT_PATH_PREFIX}/{body["name"]}/dns_server'
        vault.write(dns_server_key_path, dns_server_key)
        dpath.set(body, 'dns_server/key', dns_server_key_path)

    region = model.Region.from_dict(body)

    try:
        db.session.add(region)
        db.session.commit()
        logger.info(f'Region {region.name} (id {region.id}) created by user {user}')
    except sqlalchemy.exc.SQLAlchemyError:
        # If database transaction failed remove group in Keycloak.
        keycloak.group_delete(owners_id)
        raise

    return region.to_dict()


def get_region(keycloak: KeycloakClient, region_id, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if region.users_group is not None:
        if not keycloak.user_check_role(user, ADMIN_ROLE):
            if not keycloak.user_check_group_any(
                    user, [region.users_group, region.owner_group]):
                raise Forbidden("You don't have access to this region.")

    return region.to_dict()


def update_region(keycloak: KeycloakClient, vault: Vault, region_id, body, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group):
            raise Forbidden("You don't have write access to this region.")

    try:
        if body.get('users_group'):
            keycloak.group_get(body['users_group'])
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

    openstack_credentials = dpath.get(body, 'openstack/credentials',
                                      default=region.openstack_credentials)
    if not isinstance(openstack_credentials, str):
        vault.write(region.openstack_credentials, openstack_credentials)
        dpath.delete(body, 'openstack/credentials')

    satellite_credentials = dpath.get(body, 'satellite/credentials',
                                      default=region.satellite_credentials)
    if not isinstance(satellite_credentials, str):
        vault.write(region.satellite_credentials, satellite_credentials)
        dpath.delete(body, 'satellite/credentials')

    dns_server_key = dpath.get(body, 'dns_server/key',
                               default=region.dns_server_key)
    if not isinstance(dns_server_key, str):
        vault.write(region.dns_server_key, dns_server_key)
        dpath.delete(body, 'dns_server/key')

    region.update_from_dict(body)

    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) updated by user {user}')

    return region.to_dict()


def delete_region(keycloak: KeycloakClient, region_id, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group):
            raise Forbidden("You don't have write access to this region.")

    db.session.delete(region)

    try:
        owner_group = keycloak.group_get(region.owner_group)
        keycloak.group_delete(owner_group['id'])
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


def list_region_templates(region_id):
    raise NotImplementedError


def add_region_template(region_id, body):
    raise NotImplementedError


def delete_region_template(region_id, body):
    raise NotImplementedError
