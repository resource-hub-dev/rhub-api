import logging
import subprocess
from datetime import timedelta

from rhub.api import db
from rhub.worker import celery
from rhub.api.utils import date_now
from rhub.bare_metal.model import (
    BareMetalBootType,
    BareMetalException,
    BareMetalIronicHandler,
    BareMetalProvision,
    BareMetalProvisionISO,
    BareMetalProvisionQCOW2,
    BareMetalProvisionStatus,
    IronicNode,
)
from rhub.bare_metal.tasks.host import return_host_to_pool
from rhub.bare_metal.tasks.image import _ironic_sync_image

logger = logging.getLogger(__name__)


@celery.task()
def ironic_provision_task(provision_id):
    provision: BareMetalProvision = BareMetalProvision.query.get(provision_id)

    if not isinstance(provision.host.handler, BareMetalIronicHandler):
        return_host_to_pool(provision.host)
        raise NotImplementedError()

    logger.info(f"Provisioning {provision}")

    try:
        provision.status = BareMetalProvisionStatus.PROVISIONING_SYNC_IMAGE
        db.session.commit()

        _ironic_sync_image(provision)
    except subprocess.CalledProcessError:
        return_host_to_pool(provision.host)
        provision.status = BareMetalProvisionStatus.FAILED_PROVISIONING_SYNC_IMAGE
        db.session.commit()
        raise

    try:
        provision.status = BareMetalProvisionStatus.PROVISIONING_DEPLOY_HOST
        db.session.commit()

        if not isinstance(provision, (BareMetalProvisionISO, BareMetalProvisionQCOW2)):
            return_host_to_pool(provision.host)
            raise NotImplementedError()

        ironic: BareMetalIronicHandler = provision.host.handler
        ironic_client = ironic.get_client()

        operations = provision.ironic_operations

        # TODO: do it with other types
        if provision.boot_type is BareMetalBootType.UEFI_SECURE_BOOT:
            operations.append(ironic_client.operation_for_uefi_secure_boot())

        logger.debug(f"Ironic node creation data: {operations}")

        ironic_node: IronicNode = ironic_client.node.update(
            provision.host.handler_uuid,
            operations,
        )
        logger.debug(f"Updated node: {ironic_node}")

        # TODO: change the state and create a beat-task to update status on bg
        logger.info(f"Waiting for provisioning {provision}")
        ironic_client.change_and_wait_provision_state(ironic_node.uuid, "active")
        # TODO: discuss: ironic 'active' state is set after ironic reboots the
        #  host, after deploying it, it does not mean that the host is on an
        #  "usable" state
        provision.status = BareMetalProvisionStatus.ACTIVE

        # TODO: get from policy
        provision.host_reservation_expires_at = date_now() + timedelta(days=14)

        db.session.commit()
    except Exception:
        return_host_to_pool(provision.host)
        provision.status = BareMetalProvisionStatus.FAILED_PROVISIONING_DEPLOY_HOST
        db.session.commit()
        raise

    logger.info(f"Provisioning {provision} done - host {provision.host}")


@celery.task()
def ironic_provision_stop_task(provision_id):
    # TODO: change the state and create a beat-task to update status on bg

    provision: BareMetalProvision = BareMetalProvision.query.get(provision_id)
    logger.info(f"Finishing provisioning {provision} and returning host to pool")
    provision.status = BareMetalProvisionStatus.PROVISIONING_ENDING
    db.session.commit()

    ironic: BareMetalIronicHandler = provision.host.handler
    if not ironic.is_available():
        msg = f"Ironic {ironic} is not available"
        logger.error(msg)
        raise BareMetalException(msg)
    ironic_client = ironic.get_client()

    try:
        provision.status = BareMetalProvisionStatus.RETURNING_HOST
        db.session.commit()

        # TODO: discuss the recover states
        ironic_client.change_and_wait_provision_state(
            provision.host.handler_uuid, "deleted"
        )

        return_host_to_pool(provision.host)
    except BareMetalException:
        provision.status = BareMetalProvisionStatus.FAILED_RETURNING_HOST
        db.session.commit()
        raise

    provision.status = BareMetalProvisionStatus.FINISHED
    db.session.commit()


@celery.task()
def stop_provision_after_expiration_task():
    provisions = BareMetalProvision.query.filter(
        BareMetalProvision.status == BareMetalProvisionStatus.ACTIVE,
        BareMetalProvision.host_reservation_expires_at <= date_now(),
    )

    for provision in provisions.all():
        ret = ironic_provision_stop_task.delay(provision.id)
        logger.debug(f"Queued background task {ret}")
