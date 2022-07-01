import functools
import logging

import sqlalchemy
from connexion import problem
from dateutil.parser import isoparse as date_parse
from flask import Response, url_for

from rhub.api import DEFAULT_PAGE_LIMIT, db, di
from rhub.api.utils import date_now, db_sort
from rhub.auth import ADMIN_ROLE
from rhub.auth.keycloak import KeycloakClient
from rhub.auth.utils import route_require_admin
from rhub.lab import (CLUSTER_ADMIN_ROLE, SHAREDCLUSTER_GROUP, SHAREDCLUSTER_ROLE,
                      SHAREDCLUSTER_USER, model)
from rhub.lab import utils as lab_utils
from rhub.openstack import model as openstack_model


logger = logging.getLogger(__name__)


def _user_is_cluster_admin(user_id):
    """Check if user is cluster admin."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    return keycloak.user_check_role(user_id, CLUSTER_ADMIN_ROLE)


def _user_can_access_cluster(cluster, user_id):
    """Check if user can access cluster."""
    keycloak = di.get(KeycloakClient)
    if _user_is_cluster_admin(user_id):
        return True
    if cluster.owner_id == user_id:
        return True
    if cluster.group_id is not None:
        return keycloak.user_check_group(user_id, cluster.group_id)
    return False


def _user_can_access_region(region, user_id):
    """Check if user can access region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if region.users_group_id is None:  # shared region
        return True
    return keycloak.user_check_group_any(
        user_id, [region.users_group_id, region.owner_group_id]
    )


def _user_can_create_reservation(region, user_id):
    """Check if user can create in reservations in the region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if region.reservations_enabled:
        return True
    return keycloak.user_check_group(user_id, region.owner_group_id)


def _user_can_set_lifespan(region, user_id):
    """Check if user can set/change lifespan expiration of cluster in the region."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if keycloak.user_check_role(user_id, SHAREDCLUSTER_ROLE):
        return True
    return keycloak.user_check_group(user_id, region.owner_group_id)


def _user_can_disable_expiration(region, user_id):
    """Check if user can disable cluster reservation expiration."""
    keycloak = di.get(KeycloakClient)
    if keycloak.user_check_role(user_id, ADMIN_ROLE):
        return True
    if keycloak.user_check_role(user_id, SHAREDCLUSTER_ROLE):
        return True
    return keycloak.user_check_group(user_id, region.owner_group_id)


@functools.lru_cache()
def _get_sharedcluster_user_id():
    keycloak = di.get(KeycloakClient)
    user_search = keycloak.user_list({'username': SHAREDCLUSTER_USER})
    if user_search:
        return user_search[0]['id']
    return None


@functools.lru_cache()
def _get_sharedcluster_group_id():
    keycloak = di.get(KeycloakClient)
    for group in keycloak.group_list():
        if group['name'] == SHAREDCLUSTER_GROUP:
            return group['id']
    return None


def _cluster_href(cluster):
    href = {
        'cluster': url_for('.rhub_api_lab_cluster_get_cluster',
                           cluster_id=cluster.id),
        'cluster_events': url_for('.rhub_api_lab_cluster_list_cluster_events',
                                  cluster_id=cluster.id),
        'cluster_hosts': url_for('.rhub_api_lab_cluster_list_cluster_hosts',
                                 cluster_id=cluster.id),
        'cluster_reboot_hosts': url_for('.rhub_api_lab_cluster_reboot_hosts',
                                        cluster_id=cluster.id),
        'region': url_for('.rhub_api_lab_region_get_region',
                          region_id=cluster.region_id),
        'product': url_for('.rhub_api_lab_product_get_product',
                           product_id=cluster.product_id),
        'owner': url_for('.rhub_api_auth_user_get_user',
                         user_id=cluster.owner_id),
        'openstack': url_for('.rhub_api_openstack_cloud_get',
                             cloud_id=cluster.region.openstack_id),
        'project': url_for('.rhub_api_openstack_project_get',
                           project_id=cluster.project_id),
    }
    if cluster.group_id:
        href['group'] = url_for('.rhub_api_auth_group_get_group',
                                group_id=cluster.group_id)
    return href


def _cluster_event_href(cluster_event):
    href = {
        'cluster': url_for('.rhub_api_lab_cluster_get_cluster',
                           cluster_id=cluster_event.cluster_id),
        'event': url_for('.rhub_api_lab_cluster_get_cluster_event',
                         event_id=cluster_event.id)
    }
    if cluster_event.user_id:
        href['user'] = url_for('.rhub_api_auth_user_get_user',
                               user_id=cluster_event.user_id)
    if cluster_event.type == model.ClusterEventType.TOWER_JOB:
        href['tower'] = url_for('.rhub_api_tower_get_server',
                                server_id=cluster_event.tower_id)
        href['event_stdout'] = url_for('.rhub_api_lab_cluster_get_cluster_event_stdout',
                                       event_id=cluster_event.id)
    return href


def _cluster_host_href(cluster_host):
    href = {
        'cluster': url_for('.rhub_api_lab_cluster_get_cluster',
                           cluster_id=cluster_host.cluster_id),
    }
    return href


def list_clusters(keycloak: KeycloakClient,
                  user, filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    if _user_is_cluster_admin(user):
        clusters = model.Cluster.query
    else:
        user_groups = [group['id'] for group in keycloak.user_group_list(user)]
        if sharedcluster_group_id := _get_sharedcluster_group_id():
            user_groups.append(sharedcluster_group_id)
        clusters = model.Cluster.query.filter(sqlalchemy.or_(
            model.Cluster.owner_id == user,
            model.Cluster.group_id.in_(user_groups),
        ))

    if 'name' in filter_:
        clusters = clusters.filter(model.Cluster.name.ilike(filter_['name']))

    if 'region_id' in filter_:
        clusters = clusters.filter(model.Cluster.region_id == filter_['region_id'])

    if 'owner_id' in filter_:
        clusters = clusters.filter(model.Cluster.owner_id == filter_['owner_id'])

    if 'group_id' in filter_:
        clusters = clusters.filter(model.Cluster.group_id == filter_['group_id'])

    if 'status' in filter_:
        clusters = clusters.filter(
            model.Cluster.status == model.ClusterStatus(filter_['status'])
        )

    if 'status_flag' in filter_:
        clusters = clusters.filter(
            model.Cluster.status.in_(
                model.ClusterStatus.flag_statuses(filter_['status_flag'])
            )
        )

    if 'shared' in filter_:
        if sharedcluster_group_id := _get_sharedcluster_group_id():
            if filter_['shared']:
                clusters = clusters.filter(
                    model.Cluster.group_id == sharedcluster_group_id
                )
            else:
                clusters = clusters.filter(
                    model.Cluster.group_id != sharedcluster_group_id
                )

    if filter_.get('deleted', False):
        clusters = clusters.filter(
            model.Cluster.status == model.ClusterStatus.DELETED
        )
    else:
        clusters = clusters.filter(
            model.Cluster.status != model.ClusterStatus.DELETED
        )

    if sort:
        clusters = db_sort(clusters, sort)

    return {
        'data': [
            cluster.to_dict() | {'_href': _cluster_href(cluster)}
            for cluster in clusters.limit(limit).offset(page * limit)
        ],
        'total': clusters.count(),
    }


def create_cluster(keycloak: KeycloakClient, body, user):
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

    query = model.Cluster.query.filter(
        db.and_(
            model.Cluster.name == body['name'],
            model.Cluster.status != model.ClusterStatus.DELETED,
        )
    )
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Cluster with name {body["name"]!r} already exists',
        )

    product = model.Product.query.get(body['product_id'])
    if not product:
        return problem(404, 'Not Found', f'Product {body["product_id"]} does not exist')

    if not region.is_product_enabled(product.id):
        return problem(400, 'Bad request',
                       f'Product {product.id} is not enabled in the region')

    cluster_data = body.copy()
    cluster_data['created'] = date_now()

    shared = cluster_data.pop('shared', False)
    if shared or user == _get_sharedcluster_user_id():
        sharedcluster_group_id = _get_sharedcluster_group_id()

        if not sharedcluster_group_id:
            return problem(500, 'Internal error',
                           'Group for shared clusters does not exist.')

        if not (keycloak.user_check_role(user, SHAREDCLUSTER_ROLE)
                or keycloak.user_check_role(user, ADMIN_ROLE)):
            return problem(
                404, 'Forbidden',
                f'Only users with role {SHAREDCLUSTER_ROLE} can create shared clusters.'
            )

        cluster_data['lifespan_expiration'] = None
        cluster_data['reservation_expiration'] = None

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

    if cluster_data['reservation_expiration'] is not None:
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

    if 'project_id' in cluster_data:
        project_id = cluster_data['project_id']
        project = openstack_model.Project.query.get(project_id)
        if not project:
            return problem(404, 'Not Found', f'Project {project_id} does not exist')
        if project.cloud_id != region.openstack.id:
            return problem(400, 'Bad Request', 'TODO')
        if project.owner_id != user and not _user_is_cluster_admin(user):
            return problem(403, 'Forbidden', 'TODO')

    else:
        user_name = keycloak.user_get(user)['username']
        project_name = f'ql_{user_name}'

        project_query = openstack_model.Project.query.filter(
            db.and_(
                openstack_model.Project.cloud_id == region.openstack.id,
                openstack_model.Project.name == project_name,
            )
        )
        if project_query.count() > 0:
            project = project_query.first()
        else:
            project = openstack_model.Project(
                cloud_id=region.openstack.id,
                name=project_name,
                description='Project created by QuickCluster playbooks',
                owner_id=user,
                group_id=_get_sharedcluster_group_id() if shared else None
            )
            db.session.add(project)
            db.session.flush()

        cluster_data['project_id'] = project.id

    try:
        cluster = model.Cluster.from_dict(cluster_data)
        db.session.add(cluster)
        db.session.flush()
    except ValueError as e:
        return problem(400, 'Bad Request', str(e))

    try:
        product.validate_cluster_params(cluster.product_params)
    except Exception as e:
        db.session.rollback()
        return problem(400, 'Bad Request', 'Invalid product parameters.',
                       ext={'invalid_product_params': e.args[0]})

    if region.user_quota is not None and product.flavors is not None:
        current_user_quota_usage = region.get_user_quota_usage(user)
        user_quota = region.user_quota.to_dict()
        params = cluster.product_params
        node_params_keys = list(
            filter(lambda param: param.find('node') != -1, params.keys()))
        node_consumption = {}
        if ('num_nodes' in node_params_keys):  # Generic
            num_nodes = int(params['num_nodes'])
            for rsc in product.flavors[params['node_flavor']].keys():
                node_consumption[rsc] = num_nodes * \
                    product.flavors[params['node_flavor']][rsc]
        else:
            num_node_param_keys = list(
                filter(lambda param: param.find('num') != -1, node_params_keys))
            for key in num_node_param_keys:
                count = int(params[key])
                flavor_name = key[key.find('num_') + 4:]
                if key.find('master') != -1:
                    if count == 1:
                        flavor_name = [name for name in product.flavors
                                       if 'single' in name][0]
                    else:
                        flavor_name = [name for name in product.flavors
                                       if 'multi' in name][0]
                flavor = product.flavors[flavor_name]
                for rsc in flavor.keys():
                    if rsc not in node_consumption:
                        node_consumption[rsc] = 0
                    node_consumption[rsc] += count * int(flavor[rsc])
        for rsc in user_quota.keys():
            rsc_consumption = node_consumption[rsc] + \
                current_user_quota_usage[rsc]
            if (rsc_consumption / user_quota[rsc] >= 1):
                db.session.rollback()
                logger.exception('Failed to create cluster. Quota Exceeded')
                return problem(500, 'Internal Server Error',
                                    'Quota Exceeded. Please resize cluster')

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
            user_id=user,
            date=date_now(),
            tower_id=region.tower_id,
            tower_job_id=tower_job['id'],
            status=model.ClusterStatus.QUEUED,
        )
        db.session.add(cluster_event)

        cluster.status = model.ClusterStatus.QUEUED

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return problem(500, 'Internal Server Error',
                       'Failed to trigger cluster creation.')

    db.session.commit()
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) created by user {user}')

    return cluster.to_dict() | {'_href': _cluster_href(cluster)}


def get_cluster(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return cluster.to_dict() | {'_href': _cluster_href(cluster)}


def update_cluster(cluster_id, body, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    if cluster.status.is_deleted:
        return problem(400, 'Bad Request',
                       f"Can't update, cluster {cluster_id} is in deleted state")

    cluster_data = body.copy()

    for key in ['name', 'region_id', 'product_id', 'product_params']:
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

        cluster_event = model.ClusterLifespanChangeEvent(
            cluster_id=cluster.id,
            user_id=user,
            date=date_now(),
            old_value=cluster.lifespan_expiration,
            new_value=cluster_data['lifespan_expiration']
        )
        db.session.add(cluster_event)

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

        cluster_event = model.ClusterReservationChangeEvent(
            cluster_id=cluster.id,
            user_id=user,
            date=date_now(),
            old_value=cluster.reservation_expiration,
            new_value=cluster_data['reservation_expiration']
        )
        db.session.add(cluster_event)

    if 'status' in cluster_data:
        if not _user_is_cluster_admin(user):
            return problem(
                403, 'Forbidden',
                "You don't have permissions to change the cluster status."
            )

        cluster_data['status'] = model.ClusterStatus(cluster_data['status'])

        cluster_event = model.ClusterStatusChangeEvent(
            cluster_id=cluster.id,
            user_id=user,
            date=date_now(),
            old_value=cluster.status,
            new_value=cluster_data['status']
        )
        db.session.add(cluster_event)

    cluster.update_from_dict(cluster_data)

    db.session.commit()
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) updated by user {user}')

    return cluster.to_dict() | {'_href': _cluster_href(cluster)}


def delete_cluster(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    if cluster.status.is_deleting:
        return problem(400, 'Bad Request',
                       f'Cluster {cluster_id} is already in deleting state')

    if cluster.status.is_deleted:
        return problem(400, 'Bad Request',
                       f'Cluster {cluster_id} was already deleted')

    if cluster.status.is_creating:
        return problem(
            400, 'Bad Request',
            f'Cluster {cluster_id} is in creating state. Before deleting, '
            'the cluster must be in the Active state or in any of failed states.',
        )

    try:
        lab_utils.delete_cluster(cluster, user)
    except Exception:
        return problem(500, 'Internal Server Error',
                       'Failed to trigger cluster deletion.')


def list_cluster_events(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return [
        event.to_dict() | {'_href': _cluster_event_href(event)}
        for event in cluster.events
    ]
    logger.info(f'Cluster {cluster.name} (id {cluster.id}) deleted by user {user}')


def get_cluster_event(event_id, user):
    event = model.ClusterEvent.query.get(event_id)
    if not event:
        return problem(404, 'Not Found', f'Event {event_id} does not exist')

    if not _user_can_access_cluster(event.cluster, user):
        return problem(403, 'Forbidden', "You don't have access to related cluster.")

    return event.to_dict() | {'_href': _cluster_event_href(event)}


def get_cluster_event_stdout(event_id, user):
    event = model.ClusterTowerJobEvent.query.get(event_id)
    if not event:
        return problem(404, 'Not Found', f'Event {event_id} does not exist')

    if not _user_can_access_cluster(event.cluster, user):
        return problem(403, 'Forbidden', "You don't have access to related cluster.")

    return Response(event.get_tower_job_output(), 200, content_type='text/plain')


def list_cluster_hosts(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    return [
        host.to_dict() | {'_href': _cluster_host_href(host)}
        for host in cluster.hosts
    ]


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

    return [
        host.to_dict() | {'_href': _cluster_host_href(host)}
        for host in hosts
    ]


@route_require_admin
def delete_cluster_hosts(cluster_id, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    for host in cluster.hosts:
        db.session.delete(host)
    db.session.commit()


def reboot_hosts(cluster_id, body, user):
    cluster = model.Cluster.query.get(cluster_id)
    if not cluster:
        return problem(404, 'Not Found', f'Cluster {cluster_id} does not exist')

    if not _user_can_access_cluster(cluster, user):
        return problem(403, 'Forbidden', "You don't have access to this cluster.")

    reboot_type = body.get('type', 'soft').upper()

    if body['hosts'] == 'all':
        hosts_to_reboot = {host.fqdn: host for host in cluster.hosts}
    else:
        hosts_to_reboot = {
            host.fqdn: host
            for host in model.ClusterHost.query.filter(
                sqlalchemy.and_(
                    model.ClusterHost.cluster_id == cluster.id,
                    sqlalchemy.or_(
                        model.ClusterHost.id.in_(
                            [i['id'] for i in body['hosts'] if 'id' in i]
                        ),
                        model.ClusterHost.fqdn.in_(
                            [i['fqdn'] for i in body['hosts'] if 'fqdn' in i]
                        ),
                    ),
                )
            ).all()
        }

    rebooted_hosts = []

    try:
        os_project_name = cluster.region.get_user_project_name(cluster.owner_id)
        os_client = cluster.region.create_openstack_client(os_project_name)
        for server in os_client.compute.servers():
            if server.hostname in hosts_to_reboot:
                logger.info(f'Rebooting cluster host {server.hostname}, '
                            f'cluster_id={cluster.id}')
                os_client.compute.reboot_server(server, reboot_type)
                rebooted_hosts.append(hosts_to_reboot[server.hostname])
    except Exception as e:
        logger.exception(f'Failed to reboot nodes, {e!s}')
        return problem(500, 'Server Error', 'Failed to reboot nodes')

    return [{'id': host.id, 'fqdn': host.fqdn} for host in rebooted_hosts]
