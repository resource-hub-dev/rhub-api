import pytest

from rhub.policies import model
from rhub.api import db
from test_tower import _db_add_row_side_effect
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


def test_list_policy(client, mocker):
    def row(data):
        row = mocker.Mock()
        row._asdict.return_value = data
        return row

    db.session.query.return_value.limit.return_value.offset.return_value = [
        row({'id': 1, 'name': 'test', 'department': 'test'}),
        row({'id': 2, 'name': 'test', 'department': 'test'}),
    ]
    db.session.query.return_value.count.return_value = 2

    rv = client.get(
        f'{API_BASE}/policies',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'department': 'test',
                'id': 1,
                'name': 'test'
            },
            {
                'department': 'test',
                'id': 2,
                'name': 'test'
            }
        ],
        'total': 2,
    }


def test_get_policy(client):
    model.Policy.query.get.return_value = model.Policy(
        id=1,
        name='test',
        department='',
        constraint_sched_avail=[],
        constraint_serv_avail=3,
        constraint_limit={},
        constraint_density='',
        constraint_tag=[],
        constraint_cost=1.23,
        constraint_location='',
    )

    rv = client.get(
        f'{API_BASE}/policies/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Policy.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'department': '',
        'constraint': {
            'sched_avail': [],
            'serv_avail': 3,
            'limit': {},
            'density': '',
            'tag': [],
            'cost': 1.23,
            'location': '',
        }
    }


def test_create_policy(client, keycloak_mock, db_session_mock):
    user_data = {'id': 'uuid', 'name': 'user'}
    policy_data = {
        'name': 'test',
        'department': 'test server',
    }
    group_id = '00000004-0003-0002-0001-000000000000'

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_create.return_value = group_id

    rv = client.post(
        f'{API_BASE}/policies',
        headers={'Authorization': 'Bearer foobar'},
        json=policy_data,
    )

    keycloak_mock.group_role_add.assert_called_with('policy-owner', group_id)
    keycloak_mock.group_user_add.assert_called_with(
        '00000000-0000-0000-0000-000000000000', group_id)

    server = db_session_mock.add.call_args.args[0]
    for k, v in policy_data.items():
        assert getattr(server, k) == v

    assert rv.status_code == 200


def test_delete_policy(client, keycloak_mock, db_session_mock):
    user_id = '00000000-0000-0000-0000-000000000000'

    policy = model.Policy(
        id=1,
        name='test',
        department='',
        constraint_sched_avail=[],
        constraint_serv_avail=3,
        constraint_limit={},
        constraint_density='',
        constraint_tag=[],
        constraint_cost=1.23,
        constraint_location='',
    )
    model.Policy.query.get.return_value = policy
    model.Policy.query.delete.return_value = policy
    keycloak_mock.user_group_list.return_value = [{'id': 'uuid', 'name': 'policy-1-owners'}]
    keycloak_mock.group_list.return_value = [{'id': 'uuid', 'name': 'policy-1-owners'}]

    rv = client.delete(
        f'{API_BASE}/policies/1',
        headers={'Authorization': 'Bearer foobar'},
    )
    model.Policy.query.get.assert_called_with(1)
    keycloak_mock.user_group_list.assert_called_with(user_id)

    db_session_mock.delete.assert_called_with(policy)

    assert rv.status_code == 204


def test_update_policy(client, keycloak_mock, db_session_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    policy = model.Policy(
        id=1,
        name='test',
        department='test2',
        constraint_sched_avail=[],
        constraint_serv_avail=3,
        constraint_limit={},
        constraint_density='',
        constraint_tag=[],
        constraint_cost=1.23,
        constraint_location='',
    )
    model.Policy.query.get.return_value = policy
    keycloak_mock.user_group_list.return_value = [{'name': 'policy-1-owners'}]

    rv = client.patch(
        f'{API_BASE}/policies/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'department': 'new desc',
        },
    )

    model.Policy.query.get.assert_called_with(1)
    keycloak_mock.user_group_list.assert_called_with(user_id)
    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'new',
        'department': 'new desc',
        'constraint': {
            'sched_avail': [],
            'serv_avail': 3,
            'limit': {},
            'density': '',
            'tag': [],
            'cost': 1.23,
            'location': '',
        }
    }
