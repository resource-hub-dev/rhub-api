from rhub.api import db, di
from rhub.auth import model
from rhub.auth.ldap import LdapClient
from rhub.messaging import Messaging
from rhub.openstack import model as openstack_model


def update_users():
    ldap_client = di.get(LdapClient)

    users_query = model.User.query.filter(model.User.ldap_dn.isnot(None))
    for user in users_query:
        user.update_from_ldap(ldap_client)

    db.session.commit()


def update_groups():
    ldap_client = di.get(LdapClient)

    groups_query = model.Group.query.filter(model.Group.ldap_dn.isnot(None))
    for group in groups_query:
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
