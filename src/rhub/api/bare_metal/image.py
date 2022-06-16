import logging

from connexion import problem

from rhub.api import db
from rhub.bare_metal.model import (
    BareMetalImage,
    BareMetalImageISO,
    BareMetalImageQCOW2,
    bare_metal_image_full,
)

logger = logging.getLogger(__name__)


def image_list():
    images = db.session.query(bare_metal_image_full)
    return {
        "data": [i.to_dict_with_super() for i in images.all()],
        "total": images.count(),
    }


def image_create(body):
    if "iso_sha256" in body:
        image = BareMetalImageISO.from_dict(body)
    else:
        image = BareMetalImageQCOW2.from_dict(body)
    db.session.add(image)
    db.session.commit()

    return image.to_dict_with_super()


def image_get(image_id):
    image = BareMetalImage.query.get(image_id)
    if not image:
        return problem(404, "Not Found", f"Image {image_id} does not exist")
    return image.to_dict_with_super()
