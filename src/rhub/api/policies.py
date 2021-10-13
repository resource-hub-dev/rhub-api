import logging
import functools

from connexion import problem

from rhub.policies import model
from rhub.api import db, di, DEFAULT_PAGE_LIMIT
from rhub.auth.keycloak import (
    KeycloakClient, KeycloakGetError, problem_from_keycloak_error,
)


"""
API Schema:
{
    "id": "",
    "department": "",
    "name": "",
    "constraint": {
        "sched_avail": "",
        "serv_avail": "",
        "limit": "",
        "density": "",
        "tag": "",
        "cost": "",
        "location": ""
    }
}

Table Schema: ['id', 'department', 'name', 'constraint_sched_avail', '
constraint_serv_avail', 'constraint_limit', 'constraint_density',
'constraint_tag', 'constraint_cost', 'constraint_location']
"""

logger = logging.getLogger(__name__)


def check_access(func):
    """
    Check whether user is in policy owners group
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        keycloak = di.get(KeycloakClient)
        if 'policy_id' in kwargs:
            current_user = kwargs['user']
            group_name = f'policy-{kwargs["policy_id"]}-owners'
            group_list = keycloak.user_group_list(current_user)
            groups = {group['name']: group for group in group_list}
            if group_name in groups.keys():
                # User has access to delete/edit policy
                return func(*args, **kwargs)
            else:
                # User does not have access to delete/edit policy
                return problem(403, 'Forbidden', 'You do not own this policy')
        else:
            return func(*args, **kwargs)
    return inner


def list_policies(user, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    """
    API endpoint to provide a list of policies
    """
    policies = db.session.query(
        model.Policy.id,
        model.Policy.name,
        model.Policy.department,
    )

    if 'name' in filter_:
        policies = policies.filter(model.Policy.name.ilike(filter_['name']))

    if 'department' in filter_:
        policies = policies.filter(model.Policy.department.ilike(filter_['department']))

    return {
        'data': [
            policy._asdict() for policy in policies.limit(limit).offset(page * limit)
        ],
        'total': policies.count(),
    }


def create_policy(keycloak: KeycloakClient, user, body):
    """
    API endpoint to create a policy (JSON formatted)
    """
    policy = model.Policy.from_dict(body)

    try:
        db.session.add(policy)
        db.session.flush()
        group_id = keycloak.group_create({'name': f'policy-{policy.id}-owners'})
        keycloak.group_user_add(user, group_id)
        keycloak.group_role_add('policy-owner', group_id)
        db.session.commit()
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error',
                       f'Failed to delete owner group in Keycloak, {e}')

    return policy.to_dict()


def get_policy(user, policy_id):
    """
    API endpoint to get policy by id
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', f'Policy {policy_id} does not exist')
    return policy.to_dict()


@check_access
def update_policy(user, policy_id, body):
    """
    API endpoint to update policy attributes
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', 'Record Does Not Exist')

    policy.update_from_dict(body)
    db.session.commit()

    return policy.to_dict()


@check_access
def delete_policy(keycloak: KeycloakClient, user, policy_id):
    """
    API endpoint to delete policy given policy id
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', 'Record Does Not Exist')

    try:
        groups = {group['name']: group for group in keycloak.group_list()}
        group_name = f'policy-{policy_id}-owners'
        group_id = groups[group_name]['id']
        keycloak.group_delete(group_id)
    except KeycloakGetError as e:
        logger.exception(e)
        return problem_from_keycloak_error(e)
    except Exception as e:
        logger.exception(e)
        return problem(500, 'Unknown Error',
                       f'Failed to delete owner group in Keycloak, {e}')

    db.session.delete(policy)
    db.session.commit()
