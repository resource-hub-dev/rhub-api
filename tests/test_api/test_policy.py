import datetime

import pytest

from rhub.api import db
from rhub.auth import model as auth_model
from rhub.lab import model as lab_model
from rhub.policies import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


@pytest.fixture
def auth_group(mocker):
    return auth_model.Group(
        id=1,
        name='testuser',
    )


@pytest.fixture(autouse=True)
def user_can_modify_policy_mock(mocker):
    m = mocker.patch('rhub.api.policies._user_can_modify_policy')
    m.return_value = True
    yield m


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
        headers=AUTH_HEADER,
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


def test_list_policy_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/policies',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_policy(client, auth_group):
    model.Policy.query.get.return_value = model.Policy(
        id=1,
        name='test',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        department='',
        constraint_sched_avail=[
            datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2100, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        ],
        constraint_serv_avail=3,
        constraint_limit={'foo': 'bar'},
        constraint_density='foo',
        constraint_tag=['foo', 'bar'],
        constraint_cost=1.23,
        constraint_location_id=1,
        constraint_location=lab_model.Location(id=1, name='RDU', description=''),
    )

    rv = client.get(
        f'{API_BASE}/policies/1',
        headers=AUTH_HEADER,
    )

    model.Policy.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'owner_group_id': auth_group.id,
        'owner_group_name': auth_group.name,
        'department': '',
        'constraint': {
            'sched_avail': ['2000-01-01T12:00:00+00:00', '2100-01-01T12:00:00+00:00'],
            'serv_avail': 3,
            'limit': {'foo': 'bar'},
            'density': 'foo',
            'tag': ['foo', 'bar'],
            'cost': 1.23,
            'location_id': 1,
            'location': {
                'id': 1,
                'name': 'RDU',
                'description': '',
            },
        }
    }


def test_get_policy_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/policies/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_policy_non_existent(client):
    policy_id = 1

    model.Policy.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/policies/{policy_id}',
        headers=AUTH_HEADER,
    )

    model.Policy.query.get.assert_called_with(policy_id)

    assert rv.status_code == 404
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Policy {policy_id} does not exist'


def test_create_policy(client, auth_group, db_session_mock):
    policy_data = {
        'name': 'test',
        'owner_group_id': auth_group.id,
        'department': 'test server',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'owner_group': auth_group,
    })

    rv = client.post(
        f'{API_BASE}/policies',
        headers=AUTH_HEADER,
        json=policy_data,
    )

    server = db_session_mock.add.call_args.args[0]
    for k, v in policy_data.items():
        assert getattr(server, k) == v

    assert rv.status_code == 200


def test_create_policy_unauthorized(client, db_session_mock):
    policy_data = {
        'name': 'test',
        'department': 'test server',
    }

    rv = client.post(
        f'{API_BASE}/policies',
        json=policy_data,
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'policy_data, missing_property',
    [
        pytest.param(
            {
                'name': 'test server'
            },
            'department',
            id='missing_department'
        ),
        pytest.param(
            {
                'department': 'test'
            },
            'name',
            id='missing_name'
        )
    ]
)
def test_create_policy_missing_properties(
    client,
    db_session_mock,
    policy_data,
    missing_property
):
    rv = client.post(
        f'{API_BASE}/policies',
        headers=AUTH_HEADER,
        json=policy_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'\'{missing_property}\' is a required property'


def test_delete_policy(client, auth_group, db_session_mock):
    policy = model.Policy(
        id=1,
        name='test',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        department='',
        constraint_sched_avail=[
            datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2100, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        ],
        constraint_serv_avail=3,
        constraint_limit={'foo': 'bar'},
        constraint_density='foo',
        constraint_tag=['foo', 'bar'],
        constraint_cost=1.23,
        constraint_location_id=1,
        constraint_location=lab_model.Location(id=1, name='RDU', description=''),
    )
    model.Policy.query.get.return_value = policy
    model.Policy.query.delete.return_value = policy

    rv = client.delete(
        f'{API_BASE}/policies/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204

    model.Policy.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(policy)


def test_delete_policy_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/policies/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_delete_policy_non_existent(client, db_session_mock):
    policy_id = 1

    model.Policy.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/policies/{policy_id}',
        headers=AUTH_HEADER,
    )

    model.Policy.query.get.assert_called_with(policy_id)
    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == 'Record Does Not Exist'


def test_update_policy(client, db_session_mock, auth_group):
    policy = model.Policy(
        id=1,
        name='test',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        department='test2',
        constraint_sched_avail=[
            datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2100, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        ],
        constraint_serv_avail=3,
        constraint_limit={'foo': 'bar'},
        constraint_density='foo',
        constraint_tag=['foo', 'bar'],
        constraint_cost=1.23,
        constraint_location_id=1,
        constraint_location=lab_model.Location(id=1, name='RDU', description=''),
    )
    model.Policy.query.get.return_value = policy

    rv = client.patch(
        f'{API_BASE}/policies/1',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'department': 'new desc',
        },
    )

    model.Policy.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'new',
        'owner_group_id': auth_group.id,
        'owner_group_name': auth_group.name,
        'department': 'new desc',
        'constraint': {
            'sched_avail': ['2000-01-01T12:00:00+00:00', '2100-01-01T12:00:00+00:00'],
            'serv_avail': 3,
            'limit': {'foo': 'bar'},
            'density': 'foo',
            'tag': ['foo', 'bar'],
            'cost': 1.23,
            'location_id': 1,
            'location': {
                'id': 1,
                'name': 'RDU',
                'description': '',
            },
        }
    }


def test_update_policy_unauthorized(client):
    rv = client.patch(
        f'{API_BASE}/policies/1',
        json={
            'name': 'new',
            'department': 'new desc',
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_policy_non_existent(client):
    policy_id = 1

    model.Policy.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/policies/{policy_id}',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'department': 'new desc',
        },
    )

    model.Policy.query.get.assert_called_with(policy_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == 'Record Does Not Exist'
