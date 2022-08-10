import logging
import subprocess

from rhub.api import db
from rhub.worker import celery
from rhub.api.utils import date_now
from rhub.bare_metal.model import (
    BareMetalHandlerStatus,
    BareMetalIronicHandler,
    IronicClientException,
)

logger = logging.getLogger(__name__)


@celery.task()
def ironic_update_status_task(ironic_id):
    ironic: BareMetalIronicHandler = BareMetalIronicHandler.query.get(ironic_id)
    if not ironic.can_update_status():
        return

    logger.info(f"Checking ironic client on {ironic}")
    try:
        ironic_client = ironic.get_client()

        # TODO: think of a better call
        driver_list = ironic_client.driver.list()
        if not isinstance(driver_list, list):
            raise RuntimeError("Failed to fetch data on ironic")

    except IronicClientException as error:
        msg = f"Error checking ironic client {ironic} - {error!r}"
        logger.exception(msg)

        ironic.status = BareMetalHandlerStatus.FAILED_API_CHECK
        ironic.last_check = date_now()
        ironic.last_check_error = msg
        db.session.commit()

        raise

    try:
        subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=60",
                f"root@{ironic.hostname}",
                "exit",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # TODO: set deployment as ok
    except subprocess.CalledProcessError as error:
        msg = f"Error checking ironic ssh - {error!r}"
        logger.exception(msg)

        ironic.status = BareMetalHandlerStatus.FAILED_SSH_CHECK
        ironic.last_check = date_now()
        ironic.last_check_error = msg
        db.session.commit()

        raise

    ironic.status = BareMetalHandlerStatus.AVAILABLE
    ironic.last_check = date_now()
    ironic.last_check_error = None
    db.session.commit()

    logger.info(f"Ironic status updated - {ironic}")


@celery.task()
def refresh_ironic_instances_status_task():
    handlers = BareMetalIronicHandler.query
    handlers = handlers.filter_by(status=BareMetalHandlerStatus.AVAILABLE)
    for ironic in handlers.all():
        ret = ironic_update_status_task.delay(ironic.id)
        logger.debug(f"Queued background task {ret}")
