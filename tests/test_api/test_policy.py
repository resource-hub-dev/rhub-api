import pytest

from rhub.policies import model
from rhub.api import db
from test_tower import _db_add_row_side_effect
from rhub.auth.keycloak import KeycloakClient


API_BASE = '/v0'


@pytest.fixture
def keycloak_mock(mocker):
    keycloak_mock = mocker.Mock(spec=KeycloakClient)

    for m in ['policies']:
        get_keycloak_mock = mocker.patch(f'rhub.api.{m}.get_keycloak')
        get_keycloak_mock.return_value = keycloak_mock

    yield keycloak_mock


def test_list_policy(client):
    db.session.query(model.Policy.id,
                     model.Policy.name,
                     model.Policy.department).all.return_value = [(1, "test", "test"), (2, "test", "test")]

    rv = client.get(
        f'{API_BASE}/policies',
        headers={'Authorization': 'Bearer foobar'},
    )
    print(rv)
    assert rv.status_code == 200
    assert rv.json == [
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
    ]


def test_get_policy(client):
    model.Policy.query.get.return_value = model.Policy(
        id=1,
        name='test',
        department='',
        constraint_sched_avail='',
        constraint_serv_avail='',
        constraint_consumption='',
        constraint_density='',
        constraint_attribute='',
        constraint_cost='',
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
            'sched_avail': '',
            'serv_avail': '',
            'consumption': '',
            'density': '',
            'attribute': '',
            'cost': '',
            'location': '',
        }
    }


def test_create_policy(client, keycloak_mock, db_session_mock):
    user_data = {'id': 'uuid', 'name': 'user'}
    policy_data = {
        'name': 'test',
        'department': 'test server',
    }
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})
    keycloak_mock.user_get.return_value = user_data
    rv = client.post(
        f'{API_BASE}/policies',
        headers={'Authorization': 'Bearer foobar'},
        json=policy_data,
    )

    keycloak_mock.user_get.assert_called_with('00000000-0000-0000-0000-000000000000')
    server = db_session_mock.add.call_args.args[0]
    for k, v in policy_data.items():
        assert getattr(server, k) == v

    assert rv.status_code == 200


def test_search_policy(client):
    model.Policy.query.all.return_value = [model.Policy(
        id=1,
        name='test',
        department='',
        constraint_sched_avail='',
        constraint_serv_avail='',
        constraint_consumption='',
        constraint_density='',
        constraint_attribute='',
        constraint_cost='',
        constraint_location='',
    )]

    rv = client.post(
        f'{API_BASE}/policies/search',
        headers={'Authorization': 'Bearer foobar'},
        json={'name': 'test'}
    )

    model.Policy.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == [{
        'constraint': {
            'attribute': '',
            'consumption': '',
            'cost': '',
            'density': '',
            'location': '',
            'sched_avail': '',
            'serv_avail': '',
        },
        'department': '',
        'id': 1,
        'name': 'test',
    }]


def test_delete_policy(client, keycloak_mock, db_session_mock):
    user_id = '00000000-0000-0000-0000-000000000000'

    policy = model.Policy(
        id=1,
        name='test',
        department='',
        constraint_sched_avail='',
        constraint_serv_avail='',
        constraint_consumption='',
        constraint_density='',
        constraint_attribute='',
        constraint_cost='',
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

    assert rv.status_code == 200


def test_update_policy(client, keycloak_mock, db_session_mock):
    user_id = '00000000-0000-0000-0000-000000000000'
    policy = model.Policy(
        id=1,
        name='test',
        department='test2',
        constraint_sched_avail='',
        constraint_serv_avail='',
        constraint_consumption='',
        constraint_density='',
        constraint_attribute='',
        constraint_cost='',
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
            'sched_avail': '',
            'serv_avail': '',
            'consumption': '',
            'density': '',
            'attribute': '',
            'cost': '',
            'location': '',
        }
    }
