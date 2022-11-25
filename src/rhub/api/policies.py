import logging

from connexion import problem

from rhub.api import DEFAULT_PAGE_LIMIT, db
from rhub.api.utils import db_sort
from rhub.auth import utils as auth_utils
from rhub.policies import model


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


def _user_can_modify_policy(policy, user_id):
    if auth_utils.user_is_admin(user_id):
        return True
    return policy.owner_group_id in auth_utils.user_group_ids(user_id)


def list_policies(user, filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    """
    API endpoint to provide a list of policies
    """
    # TODO owner id and name
    policies = db.session.query(
        model.Policy.id,
        model.Policy.name,
        model.Policy.department,
    )

    if 'name' in filter_:
        policies = policies.filter(model.Policy.name.ilike(filter_['name']))

    if 'department' in filter_:
        policies = policies.filter(model.Policy.department.ilike(filter_['department']))

    if sort:
        policies = db_sort(policies, sort)

    return {
        'data': [
            policy._asdict() for policy in policies.limit(limit).offset(page * limit)
        ],
        'total': policies.count(),
    }


def create_policy(user, body):
    """
    API endpoint to create a policy (JSON formatted)
    """
    policy = model.Policy.from_dict(body)

    db.session.add(policy)
    db.session.commit()

    return policy.to_dict()


def get_policy(user, policy_id):
    """
    API endpoint to get policy by id
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', f'Policy {policy_id} does not exist')
    return policy.to_dict()


def update_policy(user, policy_id, body):
    """
    API endpoint to update policy attributes
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', 'Record Does Not Exist')

    if not _user_can_modify_policy(policy, user):
        return problem(403, 'Forbidden',
                       "You don't have permissions to update this policy.")

    policy.update_from_dict(body)
    db.session.commit()

    return policy.to_dict()


def delete_policy(user, policy_id):
    """
    API endpoint to delete policy given policy id
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', 'Record Does Not Exist')

    if not _user_can_modify_policy(policy, user):
        return problem(403, 'Forbidden',
                       "You don't have permissions to delete this policy.")

    db.session.delete(policy)
    db.session.commit()
