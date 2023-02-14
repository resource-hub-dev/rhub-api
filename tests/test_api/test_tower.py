import base64
from unittest.mock import ANY

import pytest

from rhub.tower import model
from rhub.tower.client import TowerError
from rhub.lab import model as lab_model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


@pytest.fixture
def user_is_admin_mock(mocker):
    yield mocker.patch('rhub.auth.utils.user_is_admin')


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list_servers(client):
    model.Server.query.limit.return_value.offset.return_value = [
        model.Server(
            id=1,
            name='test',
            description='',
            enabled=True,
            url='https://tower.example.com',
            verify_ssl=True,
            credentials='kv/test',
        ),
    ]
    model.Server.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/tower/server',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'description': '',
                'enabled': True,
                'url': 'https://tower.example.com',
                'verify_ssl': True,
                'credentials': 'kv/test',
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_servers_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/server',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_server(client):
    model.Server.query.get.return_value = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        verify_ssl=True,
        credentials='kv/test',
    )

    rv = client.get(
        f'{API_BASE}/tower/server/1',
        headers=AUTH_HEADER,
    )

    model.Server.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'enabled': True,
        'url': 'https://tower.example.com',
        'verify_ssl': True,
        'credentials': 'kv/test',
        '_href': ANY,
    }


def test_get_server_non_existent(client):
    server_id = 1

    model.Server.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/tower/server/{server_id}',
        headers=AUTH_HEADER,
    )

    model.Server.query.get.assert_called_with(server_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'


def test_get_server_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/server/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_server(client, db_session_mock, mocker):
    server_data = {
        'name': 'test',
        'description': 'test server',
        'url': 'https://tower.example.com',
        'credentials': 'kv/test',
    }

    model.Server.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'enabled': True,  # DB default
        'verify_ssl': True,
    })

    rv = client.post(
        f'{API_BASE}/tower/server',
        headers=AUTH_HEADER,
        json=server_data,
    )

    db_session_mock.add.assert_called()

    server = db_session_mock.add.call_args.args[0]
    for k, v in server_data.items():
        assert getattr(server, k) == v

    assert rv.status_code == 200


@pytest.mark.parametrize(
    'server_data, missing_property',
    [
        pytest.param(
            {
                'name': 'test',
                'url': 'https://tower.example.com',
            },
            'credentials',
            id='missing_credentials',
        ),
        pytest.param(
            {
                'url': 'https://tower.example.com',
                'credentials': 'kv/test',
            },
            'name',
            id='missing_name',
        ),
        pytest.param(
            {
                'name': 'test',
                'credentials': 'kv/test',
            },
            'url',
            id='missing_url',
        ),
    ]
)
def test_create_server_missing_properties(
    client,
    db_session_mock,
    server_data,
    missing_property,
):
    model.Server.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/tower/server',
        headers=AUTH_HEADER,
        json=server_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'{missing_property!r} is a required property'


def test_create_server_duplicate_name(client, db_session_mock):
    server_data = {
        'name': 'test',
        'description': 'test server',
        'url': 'https://tower.example.com',
        'credentials': 'kv/test',
    }

    model.Server.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/tower/server',
        headers=AUTH_HEADER,
        json=server_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Server with name {server_data["name"]!r} already exists'
    )


def test_create_server_unauthorized(client, db_session_mock):
    server_data = {
        'name': 'test',
        'description': 'test server',
        'url': 'https://tower.example.com',
        'credentials': 'kv/test',
    }

    rv = client.post(
        f'{API_BASE}/tower/server',
        json=server_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_server(client):
    server = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        verify_ssl=True,
        credentials='kv/test',
    )
    model.Server.query.get.return_value = server

    rv = client.patch(
        f'{API_BASE}/tower/server/1',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Server.query.get.assert_called_with(1)

    assert server.name == 'new'
    assert server.description == 'new desc'

    assert rv.status_code == 200


def test_update_server_duplicate_name(client, db_unique_violation):
    db_unique_violation('name', 'new')

    rv = client.patch(
        f'{API_BASE}/tower/server/1',
        headers=AUTH_HEADER,
        json={'name': 'new'},
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'Key (name)=(new) already exists.'


def test_update_server_non_existent(client, db_session_mock):
    server_id = 1

    model.Server.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/tower/server/1',
        headers=AUTH_HEADER,
        json={'name': 'new'},

    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'


def test_update_server_unauthorized(client, db_session_mock):
    expected_name = 'test'

    server = model.Server(
        id=1,
        name=expected_name,
        description='',
        enabled=True,
        url='https://tower.example.com',
        verify_ssl=True,
        credentials='kv/test',
    )
    model.Server.query.get.return_value = server

    rv = client.patch(
        f'{API_BASE}/tower/server/1',
        json={'name': 'new'},
    )

    db_session_mock.commit.assert_not_called()

    assert server.name == expected_name

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_delete_server(client, db_session_mock):
    server = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        verify_ssl=True,
        credentials='kv/test',
    )
    model.Server.query.get.return_value = server

    rv = client.delete(
        f'{API_BASE}/tower/server/1',
        headers=AUTH_HEADER,
    )

    model.Server.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(server)

    assert rv.status_code == 204


def test_delete_server_non_existent(client, db_session_mock):
    server_id = 1

    model.Server.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/tower/server/{server_id}',
        headers=AUTH_HEADER,
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Server {server_id} does not exist'


def test_delete_server_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/tower/server/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_list_templates(client):
    model.Template.query.limit.return_value.offset.return_value = [
        model.Template(
            id=1,
            name='test',
            description='',
            server_id=1,
            tower_template_id=1,
            tower_template_is_workflow=False,
            server=model.Server(
                id=1,
                name='test',
                description='',
                enabled=True,
                url='https://tower.example.com',
                verify_ssl=True,
                credentials='kv/test',
            ),
        ),
    ]
    model.Template.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/tower/template',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'description': '',
                'server_id': 1,
                'tower_template_id': 1,
                'tower_template_is_workflow': False,
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_templates_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/template',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'workflow',
    [
        pytest.param(False, id='workflow=False'),
        pytest.param(True, id='workflow=True'),
    ]
)
def test_get_template(client, mocker, workflow):
    template = model.Template.query.get.return_value = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=workflow,
    )
    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    if workflow:
        tower_client_mock.workflow_get_survey.return_value = {
            'name': '',
            'description': '',
            'spec': [],
        }
    else:
        tower_client_mock.template_get_survey.return_value = {
            'name': '',
            'description': '',
            'spec': [],
        }

    rv = client.get(
        f'{API_BASE}/tower/template/1',
        headers=AUTH_HEADER,
    )

    model.Template.query.get.assert_called_with(1)

    if workflow:
        tower_client_mock.workflow_get_survey.assert_called_with(1)
        tower_client_mock.template_get_survey.assert_not_called()
    else:
        tower_client_mock.template_get_survey.assert_called_with(1)
        tower_client_mock.workflow_get_survey.assert_not_called()

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'server_id': 1,
        'tower_template_id': 1,
        'tower_template_is_workflow': workflow,
        'tower_survey': {
            'name': '',
            'description': '',
            'spec': [],
        },
        '_href': ANY,
    }


def test_get_template_towererror(client, mocker):
    template = model.Template.query.get.return_value = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    response_mock = mocker.Mock()
    response_mock.status_code = 404
    response_mock.json.return_value = {'detail': 'Not found.'}

    tower_client_mock.template_get_survey.side_effect = TowerError(
        '...', response=response_mock)

    rv = client.get(
        f'{API_BASE}/tower/template/1',
        headers=AUTH_HEADER,
    )

    model.Template.query.get.assert_called_with(1)

    tower_client_mock.template_get_survey.assert_called_with(1)
    tower_client_mock.workflow_get_survey.assert_not_called()

    assert rv.status_code == 404
    # status_code from tower should be propagated but not problem detail
    assert rv.json['detail'] != 'Not found.'


def test_get_template_non_existent(client):
    template_id = 1

    model.Template.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/tower/template/{template_id}',
        headers=AUTH_HEADER,
    )

    model.Template.query.get.assert_called_with(template_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Template {template_id} does not exist'


def test_get_template_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/template/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_template(client, db_session_mock, mocker):
    template_data = {
        'name': 'test',
        'description': 'test tpl',
        'server_id': 1,
        'tower_template_id': 1,
        'tower_template_is_workflow': False,
    }

    model.Template.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})
    mocker.patch('rhub.api.tower._template_href').return_value = {}

    rv = client.post(
        f'{API_BASE}/tower/template',
        headers=AUTH_HEADER,
        json=template_data,
    )

    db_session_mock.add.assert_called()

    template = db_session_mock.add.call_args.args[0]
    for k, v in template_data.items():
        assert getattr(template, k) == v

    assert rv.status_code == 200


def test_create_template_duplicate_name(client, db_session_mock):
    template_data = {
        'name': 'test',
        'description': 'test tpl',
        'server_id': 1,
        'tower_template_id': 1,
        'tower_template_is_workflow': False,
    }

    model.Template.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/tower/template',
        headers=AUTH_HEADER,
        json=template_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Template with name {template_data["name"]!r} already exists'
    )


@pytest.mark.parametrize(
    'template_data, missing_property',
    [
        pytest.param(
            {
                'server_id': 1,
                'tower_template_id': 1,
                'tower_template_is_workflow': False,
            },
            'name',
            id='missing_name',
        ),
        pytest.param(
            {
                'name': 'test',
                'tower_template_id': 1,
                'tower_template_is_workflow': False,
            },
            'server_id',
            id='missing_server_id',
        ),
        pytest.param(
            {
                'name': 'test',
                'server_id': 1,
                'tower_template_is_workflow': False,
            },
            'tower_template_id',
            id='missing_tower_template_id',
        ),
        pytest.param(
            {
                'name': 'test',
                'server_id': 1,
                'tower_template_id': 1,
            },
            'tower_template_is_workflow',
            id='missing_tower_template_is_workflow',
        ),
    ]
)
def test_create_template_missing_properties(
    client,
    db_session_mock,
    template_data,
    missing_property,
):
    rv = client.post(
        f'{API_BASE}/tower/template',
        headers=AUTH_HEADER,
        json=template_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'{missing_property!r} is a required property'


def test_create_template_unauthorized(client, db_session_mock):
    template_data = {
        'name': 'test',
        'description': 'test tpl',
        'server_id': 1,
        'tower_template_id': 1,
        'tower_template_is_workflow': False,
    }

    rv = client.post(
        f'{API_BASE}/tower/template',
        json=template_data,
    )

    db_session_mock.add.assert_not_called

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_template(client, mocker):
    template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    model.Template.query.get.return_value = template
    mocker.patch('rhub.api.tower._template_href').return_value = {}

    rv = client.patch(
        f'{API_BASE}/tower/template/1',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Template.query.get.assert_called_with(1)

    assert template.name == 'new'
    assert template.description == 'new desc'

    assert rv.status_code == 200


def test_update_template_duplicate_name(
    client,
    db_unique_violation,
    mocker,
):
    template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    model.Template.query.get.return_value = template
    mocker.patch('rhub.api.tower._template_href').return_value = {}

    db_unique_violation('name', 'new')

    rv = client.patch(
        f'{API_BASE}/tower/template/{template.id}',
        headers=AUTH_HEADER,
        json={'name': 'new'},
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'Key (name)=(new) already exists.'


def test_update_template_non_existent(client, db_session_mock):
    template_id = 1

    model.Template.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/tower/template/{template_id}',
        headers=AUTH_HEADER,
        json={'name': 'new'},
    )

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Template {template_id} does not exist'


def test_update_template_unauthorized(client, db_session_mock):
    expected_name = 'test'

    template = model.Template(
        id=1,
        name=expected_name,
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    model.Template.query.get.return_value = template

    rv = client.patch(
        f'{API_BASE}/tower/template/{template.id}',
        json={'name': 'new'},
    )

    db_session_mock.commit.assert_not_called()

    assert template.name == expected_name

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_delete_template(client, db_session_mock):
    template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    model.Template.query.get.return_value = template

    rv = client.delete(
        f'{API_BASE}/tower/template/1',
        headers=AUTH_HEADER,
    )

    model.Template.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(template)

    assert rv.status_code == 204


def test_delete_non_existent(client, db_session_mock):
    template_id = 1

    model.Template.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/tower/template/{template_id}',
        headers=AUTH_HEADER,
    )

    model.Template.query.get.assert_called_with(template_id)

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Template {template_id} does not exist'


def test_delete_template_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/tower/template/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@pytest.mark.parametrize(
    'workflow',
    [
        pytest.param(False, id='workflow=False'),
        pytest.param(True, id='workflow=True'),
    ]
)
def test_template_launch(client, db_session_mock, mocker, workflow):
    template = model.Template.query.get.return_value = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=workflow,
    )
    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    tower_data = {
        'id': 123,
        'status': 'finished',
        'created': '2020-01-01T00:00:00.001020Z',
        'started': '2020-01-01T00:00:00.001020Z',
        'finished': '2020-01-01T00:00:00.001020Z',
        'failed': False,
    }
    if workflow:
        tower_client_mock.workflow_launch.return_value = tower_data
    else:
        tower_client_mock.template_launch.return_value = tower_data

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    mocker.patch('rhub.api.tower._job_href').return_value = {}

    rv = client.post(
        f'{API_BASE}/tower/template/1/launch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    if workflow:
        tower_client_mock.workflow_launch.assert_called_with(1, {'extra_vars': {'foo': 'bar'}})
    else:
        tower_client_mock.template_launch.assert_called_with(1, {'extra_vars': {'foo': 'bar'}})

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'template_id': 1,
        'launched_by': 1,
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
        '_href': ANY,
    }


def test_template_launch_towererror(client, mocker):
    template = model.Template.query.get.return_value = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    response_mock = mocker.Mock()
    response_mock.status_code = 400
    response_mock.json.return_value = {
        'variables_needed_to_start': ["'foobar' value missing"],
    }

    tower_client_mock.template_launch.side_effect = TowerError(
        '...', response=response_mock)

    mocker.patch('rhub.api.tower._job_href').return_value = {}

    rv = client.post(
        f'{API_BASE}/tower/template/1/launch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    tower_client_mock.template_launch.assert_called_with(1, {'extra_vars': {'foo': 'bar'}})

    assert rv.status_code == 400
    assert rv.json['variables_needed_to_start'] == ["'foobar' value missing"]


def test_template_launch_non_existent(client):
    template_id = 1

    model.Template.query.get.return_value = None

    rv = client.post(
        f'{API_BASE}/tower/template/{template_id}/launch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    model.Template.query.get.assert_called_with(template_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Template {template_id} does not exist'


def test_template_launch_unauthorized(client):
    rv = client.post(
        f'{API_BASE}/tower/template/1/launch',
        json={'extra_vars': {'foo': 'bar'}},
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_job_relaunch(client, db_session_mock, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=1,
        launched_by=1,
    )
    template = job.template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )

    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    tower_data = {
        'id': 123,
        'status': 'finished',
        'created': '2020-01-01T00:00:00.001020Z',
        'started': '2020-01-01T00:00:00.001020Z',
        'finished': '2020-01-01T00:00:00.001020Z',
        'failed': False,
    }
    tower_client_mock.template_job_relaunch.return_value = tower_data

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 10})

    rv = client.post(
        f'{API_BASE}/tower/job/1/relaunch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    tower_client_mock.template_job_relaunch.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 10,
        'template_id': 1,
        'launched_by': 1,
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
        '_href': ANY,
    }


def test_job_relaunch_forbidden(client, user_is_admin_mock, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=1,
        launched_by=1234,
    )
    template = job.template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )

    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    tower_data = {
        'id': 123,
        'status': 'finished',
        'created': '2020-01-01T00:00:00.001020Z',
        'started': '2020-01-01T00:00:00.001020Z',
        'finished': '2020-01-01T00:00:00.001020Z',
        'failed': False,
    }
    tower_client_mock.template_job_relaunch.return_value = tower_data

    user_is_admin_mock.return_value = False

    rv = client.post(
        f'{API_BASE}/tower/job/{job.id}/relaunch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    model.Job.query.get.assert_called_with(job.id)

    tower_client_mock.template_job_relaunch.assert_not_called()

    assert rv.status_code == 403, rv.data
    assert rv.json['title'] == 'Forbidden'
    assert rv.json['detail'] == f"You don't have permissions to relaunch job {job.id}"


def test_job_relaunch_non_existent(client):
    job_id = 1

    model.Job.query.get.return_value = None

    rv = client.post(
        f'{API_BASE}/tower/job/{job_id}/relaunch',
        headers=AUTH_HEADER,
        json={'extra_vars': {'foo': 'bar'}},
    )

    model.Job.query.get.assert_called_with(job_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Job {job_id} does not exist'


def test_job_relaunch_unauthorized(client):
    rv = client.post(
        f'{API_BASE}/tower/job/1/relaunch',
        json={'extra_vars': {'foo': 'bar'}},
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_list_jobs(client, mocker):
    model.Job.query.limit.return_value.offset.return_value = [
        model.Job(
            id=1,
            template_id=1,
            tower_job_id=1,
            launched_by=1,
        ),
    ]
    model.Job.query.count.return_value = 1

    mocker.patch('rhub.api.tower._job_href').return_value = {}

    rv = client.get(
        f'{API_BASE}/tower/job',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'template_id': 1,
                'tower_job_id': 1,
                'launched_by': 1,
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_jobs_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/job',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_job(client, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=123,
        launched_by=1,
    )
    template = job.template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )

    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    tower_data = {
        'id': 123,
        'status': 'finished',
        'created': '2020-01-01T00:00:00.001020Z',
        'started': '2020-01-01T00:00:00.001020Z',
        'finished': '2020-01-01T00:00:00.001020Z',
        'failed': False,
    }
    tower_client_mock.template_job_get.return_value = tower_data

    rv = client.get(
        f'{API_BASE}/tower/job/1',
        headers=AUTH_HEADER,
    )

    model.Job.query.get.assert_called_with(1)

    tower_client_mock.template_job_get.assert_called_with(123)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'template_id': 1,
        'launched_by': 1,
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
        '_href': ANY,
    }


def test_get_job_non_existent(client):
    job_id = 1

    model.Job.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/tower/job/{job_id}',
        headers=AUTH_HEADER,
    )

    model.Job.query.get.assert_called_with(job_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Job {job_id} does not exist'


def test_get_job_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/tower/job/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_job_towererror(client, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=123,
        launched_by=1,
    )
    template = job.template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )

    server_mock = template.server = mocker.Mock()
    tower_client_mock = server_mock.create_tower_client.return_value = mocker.Mock()

    response_mock = mocker.Mock()
    response_mock.status_code = 404
    response_mock.json.return_value = {
        'variables_needed_to_start': ["'foobar' value missing"],
    }

    tower_client_mock.template_job_get.side_effect = TowerError(
        '...', response=response_mock)

    rv = client.get(
        f'{API_BASE}/tower/job/1',
        headers=AUTH_HEADER,
    )

    model.Job.query.get.assert_called_with(1)

    tower_client_mock.template_job_get.assert_called_with(123)

    assert rv.status_code == 404
    # status_code from tower should be propagated but not problem detail
    assert rv.json['detail'] != 'Not found.'


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param(
            """
            {
                "id": 38,
                "name": "Demo Job Template",
                "url": "https://towerhost/#/jobs/playbook/38",
                "created_by": "bianca",
                "started": "2020-07-28T19:57:07.888193+00:00",
                "finished": null,
                "status": "running",
                "traceback": "",
                "inventory": "Demo Inventory",
                "project": "Demo Project",
                "playbook": "hello_world.yml",
                "credential": "Demo Credential",
                "limit": "",
                "extra_vars": "{}",
                "hosts": {}
            }
            """,
            id='template',
        ),
        pytest.param(
            """
            {
                "id": 38,
                "name": "Demo Job Template",
                "url": "https://towerhost/#/jobs/playbook/38",
                "created_by": "bianca",
                "started": "2020-07-28T19:57:07.888193+00:00",
                "finished": null,
                "status": "running",
                "traceback": "",
                "inventory": "Demo Inventory",
                "project": "Demo Project",
                "playbook": "hello_world.yml",
                "credential": "Demo Credential",
                "limit": "",
                "extra_vars": "{}",
                "hosts": {},
                "body": "Some extra info about workflow ??"
            }
            """,
            id='workflow template',
        ),
    ]
)
def test_webhook(client, mocker, payload):
    mocker.patch.dict(client.application.config, {
        'WEBHOOK_USER': 'user',
        'WEBHOOK_PASS': 'pass',
    })

    rv = client.post(
        f'{API_BASE}/tower/webhook_notification',
        headers=AUTH_HEADER | {
            'Content-Type': 'application/json',
        },
        data=payload,
    )

    assert rv.status_code == 204
