import logging

from connexion import problem

from rhub.api import db
from rhub.bare_metal.model import (
    BareMetalHost,
    BareMetalHostDrac,
    bare_metal_host_full,
    BareMetalHostRedfish,
)
from rhub.bare_metal.tasks import ironic_enroll_host_task

logger = logging.getLogger(__name__)


def host_list():
    hosts = db.session.query(bare_metal_host_full)
    return {
        "data": [i.to_dict_with_super() for i in hosts.all()],
        "total": hosts.count(),
    }


def host_create(body):
    if "drac_username" in body:  # TODO: improve
        host = BareMetalHostDrac.from_dict(body)
    elif "redfish_username" in body:  # TODO: improve
        host = BareMetalHostRedfish.from_dict(body)
    else:
        host = BareMetalHost.from_dict(body)
    db.session.add(host)
    db.session.commit()

    ret = ironic_enroll_host_task.delay(host.id)
    logger.debug(f"Queued background task {ret}")

    return host.to_dict_with_super()


def host_get(host_id):
    host = BareMetalHost.query.get(host_id)
    if not host:
        return problem(404, "Not Found", f"Host {host_id} does not exist")
    return host.to_dict_with_super()


def host_get_power_state(host_id):
    host: BareMetalHost = BareMetalHost.query.get(host_id)
    if not host:
        return problem(404, "Not Found", f"Host {host_id} does not exist")

    return {"power_state": host.power_state}
