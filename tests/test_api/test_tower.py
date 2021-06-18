import base64

import pytest

from rhub.tower import model
from rhub.tower.client import TowerError


API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list_servers(client):
    model.Server.query.all.return_value = [
        model.Server(
            id=1,
            name='test',
            description='',
            enabled=True,
            url='https://tower.example.com',
            credentials='kv/test',
        ),
    ]

    rv = client.get(
        f'{API_BASE}/tower/server',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [
        {
            'id': 1,
            'name': 'test',
            'description': '',
            'enabled': True,
            'url': 'https://tower.example.com',
            'credentials': 'kv/test',
        }
    ]


def test_get_server(client):
    model.Server.query.get.return_value = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        credentials='kv/test',
    )

    rv = client.get(
        f'{API_BASE}/tower/server/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Server.query.get.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'enabled': True,
        'url': 'https://tower.example.com',
        'credentials': 'kv/test',
    }


def test_create_server(client, db_session_mock, mocker):
    server_data = {
        'name': 'test',
        'description': 'test server',
        'url': 'https://tower.example.com',
        'credentials': 'kv/test',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'enabled': True,  # DB default
    })

    rv = client.post(
        f'{API_BASE}/tower/server',
        headers={'Authorization': 'Bearer foobar'},
        json=server_data,
    )

    db_session_mock.add.assert_called()

    server = db_session_mock.add.call_args.args[0]
    for k, v in server_data.items():
        assert getattr(server, k) == v

    assert rv.status_code == 200


def test_update_server(client):
    server = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        credentials='kv/test',
    )
    model.Server.query.get.return_value = server

    rv = client.patch(
        f'{API_BASE}/tower/server/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Server.query.get.assert_called_with(1)

    assert server.name == 'new'
    assert server.description == 'new desc'

    assert rv.status_code == 200


def test_delete_server(client, db_session_mock):
    server = model.Server(
        id=1,
        name='test',
        description='',
        enabled=True,
        url='https://tower.example.com',
        credentials='kv/test',
    )
    model.Server.query.get.return_value = server

    rv = client.delete(
        f'{API_BASE}/tower/server/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Server.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(server)

    assert rv.status_code == 204


def test_list_templates(client):
    model.Template.query.all.return_value = [
        model.Template(
            id=1,
            name='test',
            description='',
            server_id=1,
            tower_template_id=1,
            tower_template_is_workflow=False,
        ),
    ]

    rv = client.get(
        f'{API_BASE}/tower/template',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [
        {
            'id': 1,
            'name': 'test',
            'description': '',
            'server_id': 1,
            'tower_template_id': 1,
            'tower_template_is_workflow': False,
        }
    ]


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
        headers={'Authorization': 'Bearer foobar'},
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
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Template.query.get.assert_called_with(1)

    tower_client_mock.template_get_survey.assert_called_with(1)
    tower_client_mock.workflow_get_survey.assert_not_called()

    assert rv.status_code == 404
    # status_code from tower should be propagated but not problem detail
    assert rv.json['detail'] != 'Not found.'


def test_create_template(client, db_session_mock, mocker):
    template_data = {
        'name': 'test',
        'description': 'test tpl',
        'server_id': 1,
        'tower_template_id': 1,
        'tower_template_is_workflow': False,
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/tower/template',
        headers={'Authorization': 'Bearer foobar'},
        json=template_data,
    )

    db_session_mock.add.assert_called()

    template = db_session_mock.add.call_args.args[0]
    for k, v in template_data.items():
        assert getattr(template, k) == v

    assert rv.status_code == 200


def test_update_template(client):
    template = model.Template(
        id=1,
        name='test',
        description='',
        server_id=1,
        tower_template_id=1,
        tower_template_is_workflow=False,
    )
    model.Template.query.get.return_value = template

    rv = client.patch(
        f'{API_BASE}/tower/template/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Template.query.get.assert_called_with(1)

    assert template.name == 'new'
    assert template.description == 'new desc'

    assert rv.status_code == 200


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
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Template.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(template)

    assert rv.status_code == 204


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

    rv = client.post(
        f'{API_BASE}/tower/template/1/launch',
        headers={'Authorization': 'Bearer foobar'},
        json={'extra_vars': {'foo': 'bar'}},
    )

    if workflow:
        tower_client_mock.workflow_launch.assert_called_with(1, {'foo': 'bar'})
    else:
        tower_client_mock.template_launch.assert_called_with(1, {'foo': 'bar'})

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'template_id': 1,
        'launched_by': '00000000-0000-0000-0000-000000000000',
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
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

    rv = client.post(
        f'{API_BASE}/tower/template/1/launch',
        headers={'Authorization': 'Bearer foobar'},
        json={'extra_vars': {'foo': 'bar'}},
    )

    tower_client_mock.template_launch.assert_called_with(1, {'foo': 'bar'})

    assert rv.status_code == 400
    assert rv.json['variables_needed_to_start'] == ["'foobar' value missing"]


def test_job_relaunch(client, db_session_mock, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=1,
        launched_by='00000000-0000-0000-0000-000000000000',
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
        headers={'Authorization': 'Bearer foobar'},
        json={'extra_vars': {'foo': 'bar'}},
    )

    tower_client_mock.template_job_relaunch.assert_called_with(1)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 10,
        'template_id': 1,
        'launched_by': '00000000-0000-0000-0000-000000000000',
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
    }


def test_list_jobs(client):
    model.Job.query.all.return_value = [
        model.Job(
            id=1,
            template_id=1,
            tower_job_id=1,
            launched_by='00000000-0000-0000-0000-000000000000',
        ),
    ]

    rv = client.get(
        f'{API_BASE}/tower/job',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert rv.json == [
        {
            'id': 1,
            'template_id': 1,
            'tower_job_id': 1,
            'launched_by': '00000000-0000-0000-0000-000000000000',
        }
    ]


def test_get_job(client, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=123,
        launched_by='00000000-0000-0000-0000-000000000000',
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
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Job.query.get.assert_called_with(1)

    tower_client_mock.template_job_get.assert_called_with(123)

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'template_id': 1,
        'launched_by': '00000000-0000-0000-0000-000000000000',
        'tower_job_id': tower_data['id'],
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
    }


def test_get_job_towererror(client, mocker):
    job = model.Job.query.get.return_value = model.Job(
        id=1,
        template_id=1,
        tower_job_id=123,
        launched_by='00000000-0000-0000-0000-000000000000',
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
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Job.query.get.assert_called_with(1)

    tower_client_mock.template_job_get.assert_called_with(123)

    assert rv.status_code == 404
    # status_code from tower should be propagated but not problem detail
    assert rv.json['detail'] != 'Not found.'
