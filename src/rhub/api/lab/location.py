import logging

from connexion import problem
from flask import url_for

from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.lab.region import _region_href
from rhub.api.utils import db_sort
from rhub.auth import utils as auth_utils
from rhub.lab import model


logger = logging.getLogger(__name__)


def _location_href(location):
    href = {
        'location': url_for('.rhub_api_lab_location_location_get',
                            location_id=location.id),
        'location_regions': url_for('.rhub_api_lab_location_location_region_list',
                                    location_id=location.id),
    }
    return href


def location_list(sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    locations = model.Location.query

    if sort:
        locations = db_sort(locations, sort)

    return {
        'data': [
            location.to_dict() | {'_href': _location_href(location)}
            for location in locations.limit(limit).offset(page * limit)
        ],
        'total': locations.count(),
    }


@auth_utils.route_require_admin
def location_create(body, user):
    body.setdefault('description', '')

    query = model.Location.query.filter(model.Location.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Location with name {body["name"]!r} already exists',
        )

    location = model.Location.from_dict(body)

    db.session.add(location)
    db.session.commit()

    logger.info(
        f'Location {location.name} (ID {location.id}) created by user {user}',
        extra={'user_id': user, 'location_id': location.id},
    )

    return location.to_dict() | {'_href': _location_href(location)}


def location_get(location_id):
    location = model.Location.query.get(location_id)
    if not location:
        return problem(404, 'Not Found', f'Location {location_id} does not exist')
    return location.to_dict() | {'_href': _location_href(location)}


@auth_utils.route_require_admin
def location_update(location_id, body, user):
    location = model.Location.query.get(location_id)
    if not location:
        return problem(404, 'Not Found', f'Location {location_id} does not exist')

    location.update_from_dict(body)
    db.session.commit()

    logger.info(
        f'Location {location.name} (ID {location.id}) updated by user {user}',
        extra={'user_id': user, 'location_id': location.id},
    )

    return location.to_dict() | {'_href': _location_href(location)}


@auth_utils.route_require_admin
def location_delete(location_id, user):
    location = model.Location.query.get(location_id)
    if not location:
        return problem(404, 'Not Found', f'Location {location_id} does not exist')

    db.session.delete(location)
    db.session.commit()

    logger.info(
        f'Location {location.name} (ID {location.id}) deleted by user {user}',
        extra={'user_id': user, 'location_id': location.id},
    )


def location_region_list(location_id):
    location = model.Location.query.get(location_id)
    if not location:
        return problem(404, 'Not Found', f'Location {location_id} does not exist')

    return [
        region.to_dict() | {'_href': _region_href(region)}
        for region in location.regions
    ]
