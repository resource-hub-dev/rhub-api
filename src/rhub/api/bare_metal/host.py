import logging

from connexion import problem

from rhub.api import db
from rhub.bare_metal.model import BareMetalHost, BareMetalHostDrac, BareMetalHostRedfish, bare_metal_host_full
from rhub.bare_metal.tasks import ironic_enroll_host_task

logger = logging.getLogger(__name__)


def host_list():
    hosts = db.session.query(bare_metal_host_full)
    return {
        "data": [i.to_dict() for i in hosts.all()],
        "total": hosts.count(),
    }


def _host_create(host_model_cls, body):
    host = host_model_cls.from_dict(body)
    db.session.add(host)
    db.session.commit()

    ret = ironic_enroll_host_task.delay(host.id)
    logger.debug(f"Queued background task {ret}")

    return host.to_dict()


def host_create_ipmi(body):
    return _host_create(host_model_cls=BareMetalHost, body=body)


def host_create_redfish(body):
    return _host_create(host_model_cls=BareMetalHostRedfish, body=body)


def host_create_drac(body):
    return _host_create(host_model_cls=BareMetalHostDrac, body=body)


def host_get(host_id):
    host = BareMetalHost.query.get(host_id)
    if not host:
        return problem(404, "Not Found", f"Host {host_id} does not exist")
    return host.to_dict()


def host_get_power_state(host_id):
    host: BareMetalHost = BareMetalHost.query.get(host_id)
    if not host:
        return problem(404, "Not Found", f"Host {host_id} does not exist")

    return {"power_state": host.power_state}
