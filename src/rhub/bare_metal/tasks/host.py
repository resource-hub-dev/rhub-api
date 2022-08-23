import logging

from rhub.api import db
from rhub.worker import celery
from rhub.bare_metal.model import (
    BareMetalException,
    BareMetalHost,
    BareMetalHostDrac,
    BareMetalHostRedfish,
    BareMetalHostStatus,
    BareMetalIronicHandler,
    IronicNode,
)

logger = logging.getLogger(__name__)


def return_host_to_pool(host: BareMetalHost):
    host.status = BareMetalHostStatus.AVAILABLE
    db.session.commit()


@celery.task()
def ironic_enroll_host_task(host_id):
    host: BareMetalHost = BareMetalHost.query.get(host_id)

    if not host.can_be_enrolled():
        raise RuntimeError(f"Host {host} can't be enrolled")

    if not isinstance(host.handler, BareMetalIronicHandler):
        raise NotImplementedError()

    ironic: BareMetalIronicHandler = host.handler

    logger.info(f"Enrolling {host} on {ironic}")
    host.status = BareMetalHostStatus.ENROLLING
    db.session.commit()

    node_creation_data = dict(
        # TODO: discuss automated_clean - no need to disable on yoga
        automated_clean=False,
        boot_interface="ipxe" if host.ipxe_support else "pxe",
        driver_info=host.get_credentials(),
        driver="ipmi",
        name=host.name,
    )
    if isinstance(host, BareMetalHostDrac):
        node_creation_data["driver"] = "idrac"
        # node_creation_data['inspect_interface'] = 'idrac-wsman'
    elif isinstance(host, BareMetalHostRedfish):
        node_creation_data["driver"] = "redfish"

    logger.debug(f"Ironic node creation data: {node_creation_data}")

    try:
        ironic_client = ironic.get_client()
        ironic_node: IronicNode = ironic_client.node.create(**node_creation_data)
        logger.debug(f"Created node: {ironic_node}")

        port = ironic_client.port.create(
            address=host.mac,
            node_uuid=ironic_node.uuid,
        )
        logger.debug(f"Created port: {port}")

        ironic_client.change_and_wait_provision_state(ironic_node.uuid, "manage")
        ironic_client.change_and_wait_provision_state(ironic_node.uuid, "provide")

        host.status = BareMetalHostStatus.AVAILABLE
        host.handler_uuid = ironic_node.uuid
        db.session.commit()
    except BareMetalException:
        host.status = BareMetalHostStatus.FAILED_ENROLLING
        db.session.commit()
        raise

    logger.info(f"{host} enrolled on {ironic}")
