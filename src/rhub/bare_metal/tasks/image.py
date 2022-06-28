import logging
import subprocess
from tempfile import NamedTemporaryFile

from rhub.bare_metal.model import (
    BareMetalImage,
    BareMetalIronicHandler,
    BareMetalProvision,
    BareMetalProvisionISO,
)
from rhub.bare_metal.tasks.common import PLAYBOOKS_PATH

logger = logging.getLogger(__name__)


def _ironic_sync_image(provision: BareMetalProvision):
    # TODO: make sure only one of this (ironic, image) will run in parallel

    ironic: BareMetalIronicHandler = provision.host.handler
    image: BareMetalImage = provision.image

    logger.info(f"Syncing {image} on {ironic}")

    with NamedTemporaryFile(mode="w") as temp_file:  # TODO: only for ISO
        extra_variables = image.ansible_playbook_variables
        if isinstance(provision, BareMetalProvisionISO):
            kickstart_variables = provision.write_kickstart_content(temp_file)
            extra_variables.update(kickstart_variables)

        logger.debug(f"ansible-playbook extra variables: {extra_variables}")
        extra_variables = " ".join(
            f"{key}='{value}'" for key, value in extra_variables.items()
        )

        try:
            subprocess.run(
                [
                    "ansible-playbook",
                    image.ansible_playbook_file,
                    "-i",
                    f"{ironic.hostname},",
                    "--extra-vars",
                    extra_variables,
                ],
                cwd=PLAYBOOKS_PATH,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            logger.exception(f"Error running ansible - {error!r} - " f"{error.output}")
            raise

    logger.info(f"Synced {image} on {ironic}")
