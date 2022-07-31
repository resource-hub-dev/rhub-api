import logging

from connexion import problem
from sqlalchemy.exc import IntegrityError

from rhub.api import db
from rhub.bare_metal.model import BareMetalHandler, BareMetalIronicHandler
from rhub.bare_metal.tasks import ironic_update_status_task

logger = logging.getLogger(__name__)


def handler_list():
    handlers = BareMetalIronicHandler.query
    return {
        "data": [i.to_dict() for i in handlers.all()],
        "total": handlers.count(),
    }


def handler_create(body):
    try:
        handler = BareMetalIronicHandler.from_dict(body)
        db.session.add(handler)
        db.session.commit()

        ret = ironic_update_status_task.delay(handler.id)
        logger.debug(f"Queued background task {ret}")

        return handler.to_dict()
    except IntegrityError as error:
        return problem(403, "Forbidden", repr(error))


def handler_get(handler_id):
    handler = BareMetalHandler.query.get(handler_id)
    if not handler:
        return problem(404, "Not Found", f"Handler {handler_id} does not exist")
    return handler.to_dict()
