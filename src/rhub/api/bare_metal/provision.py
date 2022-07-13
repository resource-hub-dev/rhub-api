import logging
from io import BytesIO

import connexion
from connexion import problem
from flask import send_file

from rhub.api import db
from rhub.api._config import BARE_METAL_LOGS_PATH
from rhub.bare_metal.model import (
    BareMetalHost,
    BareMetalHostStatus,
    BareMetalImage,
    BareMetalImageISO,
    BareMetalImageQCOW2,
    BareMetalProvision,
    BareMetalProvisionISO,
    BareMetalProvisionQCOW2,
    bare_metal_provision_full,
)
from rhub.bare_metal.tasks import ironic_provision_stop_task, ironic_provision_task

logger = logging.getLogger(__name__)


def provision_list():
    provisions = db.session.query(bare_metal_provision_full)
    return {
        "data": [i.to_dict_with_super() for i in provisions.all()],
        "total": provisions.count(),
    }


def provision_create(body):
    host_id = body["host_id"]
    host: BareMetalHost = BareMetalHost.query.get(host_id)
    if not host:
        return problem(404, "Not Found", f"Host instance with ID {host_id} does not exist")

    if not host.is_available():
        return problem(403, "Forbidden", f"Host {host.name} is not available")

    image_id = body["image_id"]
    image = BareMetalImage.query.get(image_id)
    if not image:
        return problem(404, "Not Found", f"Image instance with ID {image_id} does not exist")

    # TODO: check arch, boot_type, ...

    if isinstance(image, BareMetalImageISO):
        provision = BareMetalProvisionISO.from_dict(body)
    elif isinstance(image, BareMetalImageQCOW2):
        provision = BareMetalProvisionQCOW2.from_dict(body)
    else:
        raise NotImplementedError()

    host.status = BareMetalHostStatus.RESERVED
    db.session.add(provision)
    db.session.commit()

    ret = ironic_provision_task.delay(provision.id)
    logger.debug(f"Queued background task {ret}")

    return provision.to_dict_with_super()


def provision_get(provision_id):
    provision = BareMetalProvision.query.get(provision_id)
    if not provision:
        return problem(404, "Not Found", f"Provision {provision_id} does not exist")
    return provision.to_dict_with_super()


def provision_finish(provision_id):
    provision = BareMetalProvision.query.get(provision_id)
    if not provision:
        return problem(404, "Not Found", f"Provision {provision_id} does not exist")

    ret = ironic_provision_stop_task.delay(provision.id)
    logger.debug(f"Queued background task {ret}")

    return provision.to_dict_with_super()


def provision_logs_upload(provision_id):
    provision = BareMetalProvision.query.get(provision_id)
    if not provision:
        return problem(404, "Not Found", f"Provision {provision_id} does not exist")

    if not isinstance(provision, BareMetalProvisionISO):
        return problem(403, "Forbidden", f"Provision {provision} does not support log upload at this point")

    file = connexion.request.files["file"]
    if not file.filename.lower().endswith(".tbz"):
        return problem(415, "Unsupported Media Type", "Provision debug logs needs to be *.tbz")

    final_file_name = BARE_METAL_LOGS_PATH / f"provision_{provision.id:08}_log.tbz"
    logger.info(f"Saving logs for provision ({provision}): {file.filename} -> {final_file_name}")
    file.save(final_file_name)

    provision.logs_path = str(final_file_name)
    db.session.commit()
    return provision


def provision_get_kickstart(provision_id):
    # this endpoint may not be on the released version
    # TODO: check with Carol and others if they find it helpful during the
    #  development of the kickstart feature

    provision = BareMetalProvision.query.get(provision_id)
    if not provision:
        return problem(404, "Not Found", f"Provision {provision_id} does not exist")

    if not isinstance(provision, BareMetalProvisionISO):
        return problem(403, "Forbidden", f"Provision {provision} does not support kickstart")

    return send_file(
        BytesIO(bytes(provision.kickstart_rendered, "utf-8")),
        as_attachment=True,
        attachment_filename="kickstart.cfg",
        mimetype="text/plain",
    )


def provision_kickstart_debug_script_get(provision_id):
    provision = BareMetalProvision.query.get(provision_id)
    if not provision:
        return problem(404, "Not Found", f"Provision {provision_id} does not exist")

    if not isinstance(provision, BareMetalProvisionISO):
        return problem(403, "Forbidden", f"Provision {provision} does not support kickstart")

    return send_file(
        BytesIO(bytes(provision.debug_script, "utf-8")),
        as_attachment=True,
        attachment_filename="kickstart_debug_script.sh",
        mimetype="text/plain",
    )
