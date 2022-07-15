import logging

import sqlalchemy
import sqlalchemy.exc
from connexion import problem
from flask import request, url_for
from werkzeug.exceptions import Forbidden

from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.lab.cluster import _user_can_access_region
from rhub.api.utils import db_sort
from rhub.api.vault import Vault
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient, KeycloakGetError
from rhub.lab import model
from rhub.tower import model as tower_model


logger = logging.getLogger(__name__)


VAULT_PATH_PREFIX = 'kv/lab/region'
"""Vault path prefix to create new credentials in Vault."""


def _region_href(region):
    href = {
        'region': url_for('.rhub_api_lab_region_get_region',
                          region_id=region.id),
        'region_usage': url_for('.rhub_api_lab_region_get_usage',
                                region_id=region.id),
        'region_products': url_for('.rhub_api_lab_region_list_region_products',
                                   region_id=region.id),
        'tower': url_for('.rhub_api_tower_get_server',
                         server_id=region.tower_id),
        'owner_group': url_for('.rhub_api_auth_group_get_group',
                               group_id=region.owner_group_id),
        'openstack_cloud': url_for('.rhub_api_openstack_cloud_get',
                                   cloud_id=region.openstack_id),
    }
    if region.satellite_id:
        href['satellite_server'] = url_for('.rhub_api_satellite_server_get',
                                           server_id=region.satellite_id)
    if region.dns_id:
        href['dns_server'] = url_for('.rhub_api_dns_server_get',
                                     server_id=region.dns_id)
    if region.users_group_id:
        href['users_group'] = url_for('.rhub_api_auth_group_get_group',
                                      group_id=region.users_group_id)
    return href


def list_regions_with_permissions(keycloak, user):
    # list regions for users with valid permissions
    if keycloak.user_check_role(user, ADMIN_ROLE):
        return model.Region.query
    else:
        user_groups = [group['id'] for group in keycloak.user_group_list(user)]
        return model.Region.query.filter(sqlalchemy.or_(
            model.Region.users_group_id.is_(None),
            model.Region.users_group_id.in_(user_groups),
            model.Region.owner_group_id.in_(user_groups),
        ))


def list_regions(keycloak: KeycloakClient,
                 user, filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    regions = list_regions_with_permissions(keycloak, user)

    if 'name' in filter_:
        regions = regions.filter(model.Region.name.ilike(filter_['name']))

    if 'location' in filter_:
        regions = (
            regions
            .outerjoin(model.Location)
            .filter(model.Location.name.ilike(filter_['location']))
        )

    if 'enabled' in filter_:
        regions = regions.filter(model.Region.enabled == filter_['enabled'])

    if 'reservations_enabled' in filter_:
        regions = regions.filter(
            model.Region.reservations_enabled == filter_['reservations_enabled']
        )

    if sort:
        regions = db_sort(regions, sort)

    return {
        'data': [
            region.to_dict() | {'_href': _region_href(region)}
            for region in regions.limit(limit).offset(page * limit)
        ],
        'total': regions.count(),
    }


def create_region(keycloak: KeycloakClient, vault: Vault, body, user):
    for key in ['owner_group_id', 'users_group_id']:
        try:
            if group_id := body.get(key):
                keycloak.group_get(group_id)
        except KeycloakGetError as e:
            logger.exception(e)
            return problem(400, 'Group does not exist',
                           f'Group {body[key]} does not exist in Keycloak, '
                           'you have to create group first or use existing group.')

    tower = tower_model.Server.query.get(body['tower_id'])
    if not tower:
        return problem(400, 'Not Found',
                       f'Tower instance with ID {body["tower_id"]} does not exist')

    query = model.Region.query.filter(model.Region.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Region with name {body["name"]!r} already exists',
        )

    region = model.Region.from_dict(body)

    db.session.add(region)
    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) created by user {user}')

    return region.to_dict() | {'_href': _region_href(region)}


def get_region(keycloak: KeycloakClient, region_id, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if region.users_group_id is not None:
        if not keycloak.user_check_role(user, ADMIN_ROLE):
            if not keycloak.user_check_group_any(
                    user, [region.users_group_id, region.owner_group_id]):
                raise Forbidden("You don't have access to this region.")

    return region.to_dict() | {'_href': _region_href(region)}


def update_region(keycloak: KeycloakClient, vault: Vault, region_id, body, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group_id):
            raise Forbidden("You don't have write access to this region.")

    for key in ['owner_group_id', 'users_group_id']:
        try:
            if group_id := body.get(key):
                keycloak.group_get(group_id)
        except KeycloakGetError as e:
            logger.exception(e)
            return problem(400, 'Group does not exist',
                           f'Group {body[key]} does not exist in Keycloak, '
                           'you have to create group first or use existing group.')

    region.update_from_dict(body)

    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) updated by user {user}')

    return region.to_dict() | {'_href': _region_href(region)}


def delete_region(keycloak: KeycloakClient, region_id, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group_id):
            raise Forbidden("You don't have write access to this region.")

    q = model.RegionProduct.query.filter(
        model.RegionProduct.region_id == region.id,
    )
    if q.count() > 0:
        for relation in q.all():
            db.session.delete(relation)
        db.session.flush()

    db.session.delete(region)

    db.session.commit()
    logger.info(f'Region {region.name} (id {region.id}) deleted by user {user}')


def list_region_products(keycloak: KeycloakClient, region_id, user, filter_):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if region.users_group_id is not None:
        if not keycloak.user_check_role(user, ADMIN_ROLE):
            if not keycloak.user_check_group_any(
                    user, [region.users_group_id, region.owner_group_id]):
                raise Forbidden("You don't have access to this region.")

    products_relation = region.products_relation

    if 'name' in filter_:
        products_relation = products_relation.filter(
            model.Region.name.ilike(filter_['enabled']),
        )

    if 'enabled' in filter_:
        products_relation = products_relation.filter(
            model.Product.enabled == filter_['enabled'],
        )

    from rhub.api.lab.product import _product_href
    return [
        {
            'region_id': r.region.id,
            'product_id': r.product.id,
            'product': r.product.to_dict(),
            'enabled': r.enabled,
        } | {
            '_href': _region_href(r.region) | _product_href(r.product)
        }
        for r in products_relation
    ]


def add_region_product(keycloak: KeycloakClient, region_id, body, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group_id):
            raise Forbidden("You don't have write access to this region.")

    product = model.Product.query.get(body['id'])
    if not product:
        return problem(404, 'Not Found', f'Product {body["id"]} does not exist')

    q = model.RegionProduct.query.filter(sqlalchemy.and_(
        model.RegionProduct.region_id == region.id,
        model.RegionProduct.product_id == product.id,
    ))
    if q.count() == 0:
        relation = model.RegionProduct(
            region_id=region.id,
            product_id=product.id,
            enabled=body.get('enabled', True),
        )
        db.session.add(relation)
        db.session.commit()
        logger.info(
            f'Added Product {product.name} (id {product.id}) to Region {region.name} '
            f'(id {region.id}) by user {user}'
        )
    elif 'enabled' in body:
        for relation in q.all():
            relation.enabled = body['enabled']
        db.session.commit()


def delete_region_product(keycloak: KeycloakClient, region_id, user):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not keycloak.user_check_role(user, ADMIN_ROLE):
        if not keycloak.user_check_group(user, region.owner_group_id):
            raise Forbidden("You don't have write access to this region.")

    product = model.Product.query.get(request.json['id'])
    if not product:
        return problem(404, 'Not Found', f'Product {request.json["id"]} does not exist')

    q = model.RegionProduct.query.filter(sqlalchemy.and_(
        model.RegionProduct.region_id == region.id,
        model.RegionProduct.product_id == product.id,
    ))
    if q.count() > 0:
        for relation in q.all():
            db.session.delete(relation)
        db.session.commit()


def region_to_usage(region, user):
    return {
        'user_quota': region.user_quota.to_dict() if region.user_quota else None,
        'user_quota_usage': region.get_user_quota_usage(user),
        'total_quota': region.total_quota.to_dict() if region.total_quota else None,
        'total_quota_usage': region.get_total_quota_usage(),
    }


def get_usage(region_id, user, with_openstack_limits=None):
    region = model.Region.query.get(region_id)
    if not region:
        return problem(404, 'Not Found', f'Region {region_id} does not exist')

    if not _user_can_access_region(region, user):
        raise Forbidden("You don't have access to this region.")

    data = region_to_usage(region, user)

    return data


def get_all_usage(keycloak: KeycloakClient, user):
    regions = [
        region for region in list_regions_with_permissions(keycloak, user)
    ]
    if not regions:
        return problem(404, 'Not Found', 'No regions exist')
    data = {"all": region_to_usage(regions[0], user)}
    data[str(regions[0].id)] = region_to_usage(regions[0], user)

    def add_usage(usage1, usage2):
        result = {}
        for key in usage1.keys():
            try:
                result[key] = usage1[key] + usage2[key]
            except Exception:
                if usage1[key]:
                    result[key] = usage1[key]
                elif usage2[key]:
                    result[key] = usage2[key]
                else:
                    result[key] = None
        return result

    for i in range(1, len(regions)):
        current_region_usage = region_to_usage(regions[i], user)
        data[str(regions[i].id)] = current_region_usage
        current_usage_all_region = {}
        current_usage_all_region['user_quota'] = add_usage(
            data['all']['user_quota'], current_region_usage['user_quota'])
        current_usage_all_region['user_quota_usage'] = add_usage(
            data['all']['user_quota_usage'], current_region_usage['user_quota_usage'])
        current_usage_all_region['total_quota'] = add_usage(
            data['all']['total_quota'], current_region_usage['total_quota'])
        current_usage_all_region['total_quota_usage'] = add_usage(
            data['all']['total_quota_usage'], current_region_usage['total_quota_usage'])
        data['all'] = current_usage_all_region
    return data
