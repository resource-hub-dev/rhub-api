import logging

from rhub.api import db, di
from rhub.auth import ADMIN_GROUP, model
from rhub.auth.ldap import LdapClient
from rhub.dns import model as dns_model
from rhub.lab import model as lab_model
from rhub.messaging import Messaging
from rhub.openstack import model as openstack_model
from rhub.satellite import model as satellite_model


logger = logging.getLogger(__name__)


def update_users():
    ldap_client = di.get(LdapClient)

    users_query = model.User.query.filter(model.User.ldap_dn.isnot(None))
    for user in users_query:
        logger.info(
            f'Updating user ID={user.id} LDAP_DN={user.ldap_dn} from LDAP',
            extra={'user_id': user.id, 'user_ldap_dn': user.ldap_dn},
        )
        user.update_from_ldap(ldap_client)

    db.session.commit()


def update_groups():
    ldap_client = di.get(LdapClient)

    groups_query = model.Group.query.filter(model.Group.ldap_dn.isnot(None))
    for group in groups_query:
        logger.info(
            f'Updating group ID={group.id} LDAP_DN={group.ldap_dn} from LDAP',
            extra={'group_id': group.id, 'group_ldap_dn': group.ldap_dn},
        )
        group.update_from_ldap(ldap_client)

    db.session.commit()


def cleanup_users():
    ldap_client = di.get(LdapClient)
    messaging = di.get(Messaging)

    users_query = model.User.query.filter(model.User.ldap_dn.isnot(None))
    for user in users_query:
        ldap_query = ldap_client.get(user.ldap_dn)
        if len(ldap_query) > 0:
            continue

        logger.info(
            f'User ID={user.id} LDAP_DN={user.ldap_dn} has been removed from LDAP.',
            extra={'user_id': user.id, 'user_ldap_dn': user.ldap_dn},
        )

        openstack_model.Project.query.filter(
            openstack_model.Project.owner_id == user.id,
        ).update(
            {'owner_id': user.manager_id},
            synchronize_session='fetch',
        )

        messaging.send(
            'auth.user.delete',
            f'User "{user.name}" has been deleted.',
            extra={
                'user_id': user.id,
                'user_name': user.name,
                'manager_id': user.manager.id,
                'manager_name': user.manager.name,
            },
        )

        user.deleted = True

        db.session.commit()


def cleanup_groups():
    ldap_client = di.get(LdapClient)

    admin_group = model.Group.query.filter(model.Group.name == ADMIN_GROUP).first()

    groups_query = model.Group.query.filter(model.Group.ldap_dn.isnot(None))
    for group in groups_query:
        ldap_query = ldap_client.get(group.ldap_dn)
        if len(ldap_query) > 0:
            continue

        logger.info(
            f'Group ID={group.id} LDAP_DN={group.ldap_dn} has been removed from LDAP.',
            extra={'group_id': group.id, 'group_ldap_dn': group.ldap_dn},
        )

        lab_model.Region.query.filter(
            lab_model.Region.users_group_id == group.id,
        ).update(
            {'users_group_id': None},
            synchronize_session='fetch',
        )

        lab_model.Region.query.filter(
            lab_model.Region.owner_group_id == group.id
        ).update(
            {'owner_group_id': admin_group.id},
            synchronize_session='fetch',
        )

        openstack_model.Project.query.filter(
            openstack_model.Project.group_id == group.id,
        ).update(
            {'group_id': None},
            synchronize_session='fetch',
        )

        openstack_model.Cloud.query.filter(
            openstack_model.Cloud.owner_group_id == group.id
        ).update(
            {'owner_group_id': admin_group.id},
            synchronize_session='fetch',
        )

        satellite_model.SatelliteServer.query.filter(
            satellite_model.SatelliteServer.owner_group_id == group.id
        ).update(
            {'owner_group_id': admin_group.id},
            synchronize_session='fetch',
        )

        dns_model.DnsServer.query.filter(
            dns_model.DnsServer.owner_group_id == group.id
        ).update(
            {'owner_group_id': admin_group.id},
            synchronize_session='fetch',
        )

        model.UserGroup.query.filter(model.UserGroup.group_id == group.id).delete()

        db.session.delete(group)
        db.session.commit()
