import logging
import functools

import sqlalchemy
from connexion import problem
from dateutil.parser import isoparse as date_parse

from rhub.lab import SHAREDCLUSTER_USER
from rhub.lab import model
from rhub.api import db, di, DEFAULT_PAGE_LIMIT
from rhub.auth import ADMIN_ROLE
from rhub.auth.utils import route_require_admin
from rhub.auth.keycloak import KeycloakClient
from rhub.api.utils import date_now


logger = logging.getLogger(__name__)


def _user_can_access_cluster(cluster, user_id):
    """Check if user can access cluster."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if cluster.user_id == user_id:
        return True
    if cluster.group_id is not None:
        return keycloak.user_check_group(user_id, cluster.group_id)
    return False


def _user_can_access_region(region, user_id):
    """Check if user can access region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if region.users_group is None:  # shared region
        return True
    return keycloak.user_check_group_any(
        user_id, [region.users_group, region.owner_group]
    )


def _user_can_create_reservation(region, user_id):
    """Check if user can create in reservations in the region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if region.reservations_enabled:
        return True
    return keycloak.user_check_group(user_id, region.owner_group)


def _user_can_set_lifespan(region, user_id):
    """Check if user can set/change lifespan expiration of cluster in the region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    return keycloak.user_check_group(user_id, region.owner_group)


def _user_can_disable_expiration(region, user_id):
    """Check if user can disable cluster reservation expiration."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    return keycloak.user_check_group(user_id, region.owner_group)


@functools.lru_cache()
def _get_sharedcluster_user_id():
    keycloak = di.get(KeycloakClient)
    user_search = keycloak.user_list({'username': SHAREDCLUSTER_USER})
    if user_search:
        return user_search[0]['id']
    return None


def list_clusters(keycloak: KeycloakClient,
                  user, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    if keycloak.user_check_role(user, ADMIN_ROLE):
        clusters = model.Cluster.query
    else:
        user_groups = [group['id'] for group in keycloak.user_group_list(user)]
        user_list = [user]
        if sharedcluster_user_id := _get_sharedcluster_user_id():
            user_list.append(sharedcluster_user_id)
        clusters = model.Cluster.query.filter(sqlalchemy.or_(
            model.Cluster.user_id.in_(user_list),
            model.Cluster.group_id.in_(user_groups),
        ))

    if 'name' in filter_:
        clusters = clusters.filter(model.Cluster.name.ilike(filter_['name']))

    if 'region_id' in filter_:
        clusters = clusters.filter(model.Cluster.region_id == filter_['region_id'])

    if 'user_id' in filter_:
        clusters = clusters.filter(model.Cluster.user_id == filter_['user_id'])

    if 'group_id' in filter_:
        clusters = clusters.filter(model.Cluster.group_id == filter_['group_id'])

    if 'shared' in filter_:
        if sharedcluster_user_id := _get_sharedcluster_user_id():
            if filter_['shared']:
                clusters = clusters.filter(
                    model.Cluster.user_id == sharedcluster_user_id
                )
            else:
                clusters = clusters.filter(
                    model.Cluster.user_id != sharedcluster_user_id
                )

    return {
        'data': [
            cluster.to_dict() for cluster in clusters.limit(limit).offset(page * limit)
        ],
        'total': clusters.count(),
    }


def create_cluster(body, user):
    region = model.Region.query.get(body['region_id'])
    if not region:
        return problem(404, 'Not Found', f'Region {body["region_id"]} does not exist')

    if not _user_can_access_region(region, user):
        return problem(403, 'Forbidden',
                       "You don't have permissions to use selected region")

    if not region.enabled:
        return problem(403, 'Forbidden', 'Selected region is disabled')

    if not _user_can_create_reservation(region, user):
        return problem(403, 'Forbidden',
                       'Reservations are disabled in the selected region, only admin '
                       'and region owners are allowed to create new reservations.')

    query = model.Cluster.query.filter(model.Cluster.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Cluster with name {body["name"]!r} already exists',
        )

    product = model.Product.query.get(body['product_id'])
    if not product:
        return problem(404, 'Not Found', f'Product {body["product_id"]} does not exist')

    cluster_data = body.copy()
    cluster_data['user_id'] = user
    cluster_data['created'] = date_now()

    if region.lifespan_enabled:
        if 'lifespan_expiration' in cluster_data:
            if not _user_can_set_lifespan(region, user):
                return problem(
                    403, 'Forbidden',
                    'Only admin and region owner can set lifespan expiration '
                    'on clusters in the selected region.'
                )
            if cluster_data['lifespan_expiration'] is not None:
                cluster_data['lifespan_expiration'] = date_parse(
                    cluster_data['lifespan_expiration']
                )
        else:
            cluster_data['lifespan_expiration'] = (
                cluster_data['created'] + region.lifespan_delta
            )
    else:
        cluster_data['lifespan_expiration'] = None

    reservation_expiration = date_parse(cluster_data['reservation_expiration'])
    cluster_data['reservation_expiration'] = reservation_expiration

    if region.reservation_expiration_max:
        if cluster_data['reservation_expiration'] is None:
            if not _user_can_disable_expiration(region, user):
                return problem(
                    403, 'Forbidden',
                    'Only admin and region owner can set create clusters without '
                    'expiration in the selected region.'
                )
        else:
            reservation_expiration_max = (
                cluster_data['created'] + region.reservation_expiration_max_delta
            )
            if reservation_expiration > reservation_expiration_max:
                return problem(
                    403, 'Forbidden', 'Exceeded maximal reservation time.',
                    ext={'reservation_expiration_max': reservation_expiration_max},
                )

    cluster_data['product_params'] = (
        product.parameters_defaults | body['product_params']
    )

    try:
        cluster = model.Cluster.from_dict(cluster_data)
        db.session.add(cluster)
    except ValueError as e:
        return problem(400, 'Bad Request', str(e))

    try:
        product.validate_cluster_params(cluster.product_params)
    except Exception as e:
        db.session.rollback()
        return problem(400, 'Bad Request', 'Invalid product parameters.',
                       ext={'invalid_product_params': e.args[0]})

    try:
        tower_client = region.tower.create_tower_client()
        tower_template = tower_client.template_get(
            template_name=product.tower_template_name_create,
        )

        logger.info(
            f'Launching Tower template {tower_template["name"]} '
            f'(id={tower_template["id"]}), '
            f'extra_vars={cluster.tower_launch_extra_vars!r}'
        )
        tower_job = tower_client.template_launch(
            tower_template['id'],
            {'extra_vars': cluster.tower_launch_extra_vars},
        )

        cluster_event = model.ClusterTowerJobEvent(
            cluster_id=cluster.id,
            tower_id=region.tower_id,
            tower_job_id=tower_job['id'],
            status=model.ClusterStatus.QUEUED,
        )
        db.session.add(cluster_event)

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return problem(500, 'Internal Server Error',
                       'Failed to trigger cluster creation.')

    db.session.commit()
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) created by user {user}')

    return cluster.to_dict()


def get_cluster(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return cluster.to_dict()


def update_cluster(cluster_id, body, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    cluster_data = body.copy()

    for key in ['name', 'region_id']:
        if key in cluster_data:
            return problem(400, 'Bad Request',
                           f'Cluster {key} field cannot be changed.')

    if 'lifespan_expiration' in cluster_data:
        if cluster.region.lifespan_enabled:
            if _user_can_set_lifespan(cluster.region, user):
                if cluster_data['lifespan_expiration'] is not None:
                    cluster_data['lifespan_expiration'] = date_parse(
                        cluster_data['lifespan_expiration']
                    )
            else:
                return problem(
                    403, 'Forbidden',
                    'Only admin and region owner can set lifespan expiration '
                    'on clusters in the selected region.'
                )
        else:
            del cluster_data['lifespan_expiration']

    if 'reservation_expiration' in cluster_data:
        if cluster_data['reservation_expiration'] is None:
            if not _user_can_disable_expiration(cluster.region, user):
                return problem(
                    403, 'Forbidden',
                    'Only admin and region owner can set create clusters without '
                    'expiration in the selected region.'
                )
        else:
            reservation_expiration = date_parse(cluster_data['reservation_expiration'])
            cluster_data['reservation_expiration'] = reservation_expiration
            if cluster.region.reservation_expiration_max:
                reservation_expiration_max = (
                    (cluster.reservation_expiration or date_now())
                    + cluster.region.reservation_expiration_max_delta
                )
                if cluster.lifespan_expiration:
                    reservation_expiration_max = min(reservation_expiration_max,
                                                     cluster.lifespan_expiration)
                if reservation_expiration > reservation_expiration_max:
                    return problem(
                        403, 'Forbidden', 'Exceeded maximal reservation time.',
                        ext={'reservation_expiration_max': reservation_expiration_max},
                    )

    cluster.update_from_dict(cluster_data)

    db.session.commit()
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) updated by user {user}')

    return cluster.to_dict()


def delete_cluster(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    try:
        tower_client = cluster.region.tower.create_tower_client()
        tower_template = tower_client.template_get(
            template_name=cluster.product.tower_template_name_delete,
        )

        logger.info(
            f'Launching Tower template {tower_template["name"]} '
            f'(id={tower_template["id"]}), '
            f'extra_vars={cluster.tower_launch_extra_vars!r}'
        )
        tower_client.template_launch(
            tower_template['id'],
            {'extra_vars': cluster.tower_launch_extra_vars},
        )

    except Exception as e:
        logger.exception(e)

    db.session.delete(cluster)
    db.session.commit()


def list_cluster_events(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return [event.to_dict() for event in cluster.events]
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) deleted by user {user}')


def get_cluster_event(event_id, user):
    event = model.ClusterEvent.query.get(event_id)
    if not event:
        return problem(404, 'Not Found', f'Event {event_id} does not exist')

    if not _user_can_access_cluster(event.cluster, user):
        return problem(403, 'Forbidden', "You don't have access to related cluster.")

    return event.to_dict()


def get_cluster_event_stdout(event_id, user):
    event = model.Event.query.get(event_id)
    if not event:
        return problem(404, 'Not Found', f'Event {event_id} does not exist')

    if not _user_can_access_cluster(event.cluster, user):
        return problem(403, 'Forbidden', "You don't have access to related cluster.")

    return event.get_tower_job_output()


def list_cluster_hosts(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return [host.to_dict() for host in cluster.hosts]


@route_require_admin
def create_cluster_hosts(cluster_id, body, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    hosts = [
        model.ClusterHost.from_dict({'cluster_id': cluster_id, **host_data})
        for host_data in body
    ]
    db.session.add_all(hosts)
    db.session.commit()

    return [host.to_dict() for host in hosts]


@route_require_admin
def delete_cluster_hosts(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    for host in cluster.hosts:
        db.session.delete(host)
    db.session.commit()
