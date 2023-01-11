from rhub.api import db, di
from . import model
from .ldap import LdapClient


def update_groups():
    ldap_client = di.get(LdapClient)

    groups_query = model.Group.query.filter(model.Group.ldap_dn.isnot(None))
    for group in groups_query:
        group.update_from_ldap(ldap_client)

    db.session.commit()
