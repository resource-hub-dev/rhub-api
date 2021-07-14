import logging

from connexion import problem
from sqlalchemy import exc

from rhub.policies import model
from rhub.api import db
from rhub.api.utils import row2dict
from rhub.api import get_keycloak


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


def normalize(body):
    """
    Flatten constraint field in given JSON
    """
    new = {}
    for key, value in body.items():
        if key == "constraint":
            for key, value in value.items():
                new["constraint_" + key] = value
        else:
            new[key] = value
    return new


def denormalize(body):
    """
    Unflatten constraint field in given JSON
    """
    new = {}
    new["constraint"] = {}
    for key, value in body.items():
        if "constraint_" in key:
            new["constraint"][key[11:]] = value
        else:
            new[key] = value
    return new


def check_access(func):
    """
    Check whether user is in policy owners group
    """
    def inner(*args, **kwargs):
        keycloak = get_keycloak()
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


def list_policies(user):
    '''
    API endpoint to provide a list of policies
    '''
    policies = db.session.query(model.Policy.id,
                                model.Policy.name,
                                model.Policy.department).all()
    columns = ['id', 'name', 'department']
    return [dict(zip(columns, policy)) for policy in policies]


def create_policy(user, body):
    """
    API endpoint to create a policy (JSON formatted)
    """
    body = normalize(body)
    keycloak = get_keycloak()
    current_user = get_keycloak().user_get(user)
    policy = model.Policy(**body)
    db.session.add(policy)
    db.session.commit()
    group_name = f'policy-{policy.id}-owners'
    group = keycloak.group_create({'name': group_name})
    keycloak.group_user_add(current_user['id'], group)
    keycloak.group_role_add('policy-owner', group)
    return denormalize(row2dict(policy))


def search_policies(user, body):
    """
    API endpoint to list/search policies for attributes (UUID/Dept/Name*)
    """
    body = normalize(body)
    sql_query = model.Policy.query
    for key, value in body.items():
        sql_query.filter(getattr(model.Policy, key).like(value))
    policies = sql_query.all()
    return [denormalize(row2dict(policy)) for policy in policies]


def get_policy(user, policy_id):
    """
    API endpoint to get policy by id
    """
    policy = model.Policy.query.get(policy_id)
    if not policy:
        return problem(404, 'Not Found', f'Policy {policy_id} does not exist')
    return denormalize(row2dict(policy))


@check_access
def update_policy(user, policy_id, body, **kwargs):
    """
    API endpoint to update policy attributes
    """
    body = normalize(body)
    try:
        policy = model.Policy.query.get(policy_id)
        for k, v in body.items():
            setattr(policy, k, v)
        db.session.commit()
    except exc.NoResultFound:
        return problem(404, 'Not Found', 'Record Does Not Exist')
    return denormalize(row2dict(policy))


@check_access
def delete_policy(user, policy_id, **kwargs):
    """
    API endpoint to delete policy given policy id
    """
    try:
        policy = model.Policy.query.get(policy_id)
        db.session.delete(policy)
        db.session.commit()
    except exc.NoResultFound:
        return problem(404, 'Not Found', 'Record Does Not Exist')
    keycloak = get_keycloak()
    groups = {group['name']: group for group in keycloak.group_list()}
    group_name = f'policy-{policy_id}-owners'
    group_id = groups[group_name]['id']
    keycloak.group_delete(group_id)
    return denormalize(row2dict(policy))
