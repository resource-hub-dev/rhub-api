import base64
from unittest.mock import ANY

import pytest

from rhub.openstack import model


API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list_clouds(client, keycloak_mock):
    model.Cloud.query.limit.return_value.offset.return_value = [
        model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id='00000000-0000-0000-0000-000000000000',
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
    ]
    model.Cloud.query.count.return_value = 1

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.get(
        f'{API_BASE}/openstack/cloud',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'description': '',
                'owner_group_id': '00000000-0000-0000-0000-000000000000',
                'owner_group_name': 'test-group',
                'url': 'https://openstack.example.com:13000',
                'credentials': 'kv/test',
                'domain_name': 'Default',
                'domain_id': 'default',
                'networks': ['test_net'],
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_clouds_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/openstack/cloud',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_cloud(client, keycloak_mock):
    model.Cloud.query.get.return_value = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.get(
        f'{API_BASE}/openstack/cloud/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Cloud.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'owner_group_name': 'test-group',
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
        '_href': ANY,
    }


def test_get_cloud_non_existent(client):
    cloud_id = 1

    model.Cloud.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/openstack/cloud/{cloud_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Cloud.query.get.assert_called_with(cloud_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cloud {cloud_id} does not exist'


def test_get_cloud_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/openstack/cloud/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_cloud(client, db_session_mock, keycloak_mock, mocker):
    cloud_data = {
        'name': 'test',
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    model.Cloud.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers={'Authorization': 'Bearer foobar'},
        json=cloud_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    cloud = db_session_mock.add.call_args.args[0]
    for k, v in cloud_data.items():
        assert getattr(cloud, k) == v


def test_create_cloud_existing_name(client, db_session_mock):
    cloud_data = {
        'name': 'test-name',
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    model.Cloud.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers={'Authorization': 'Bearer foobar'},
        json=cloud_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Cloud with name {cloud_data["name"]!r} already exists'
    )


def test_create_cloud_missing_name(client, db_session_mock):
    cloud_data = {
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers={'Authorization': 'Bearer foobar'},
        json=cloud_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == '\'name\' is a required property'


def test_create_cloud_unauthorized(client, db_session_mock):
    cloud_data = {
        'name': 'test',
        'description': '',
        'owner_group_id': '00000000-0000-0000-0000-000000000000',
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        json=cloud_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'    


def test_update_cloud(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.Cloud.query.get.assert_called_with(1)

    assert cloud.name == 'new'
    assert cloud.description == 'new desc'


@pytest.mark.skip('TODO')
def test_update_cloud_existing_name(client):
    pass


def test_update_cloud_non_existent(client):
    cloud_id = 1

    model.Cloud.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/{cloud_id}',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    model.Cloud.query.get.assert_called_with(cloud_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cloud {cloud_id} does not exist'


def test_update_cloud_unauthorized(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/{cloud.id}',
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'

    assert cloud.name == 'test'
    assert cloud.description == ''


def test_delete_cloud(client, db_session_mock, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    keycloak_mock.group_get_name.return_value = 'test-group'

    rv = client.delete(
        f'{API_BASE}/openstack/cloud/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204, rv.data

    model.Cloud.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(cloud)


def test_delete_cloud_non_existent(client, db_session_mock):
    cloud_id = 1

    model.Cloud.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/openstack/cloud/{cloud_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Cloud.query.get.assert_called_with(cloud_id)
    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cloud {cloud_id} does not exist'


def test_delete_cloud_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/openstack/cloud/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_list_projects(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    model.Project.query.limit.return_value.offset.return_value = [
        model.Project(
            id=1,
            cloud_id=1,
            cloud=cloud,
            name='test_project',
            description='',
            owner_id='00000000-0000-0000-0000-000000000000',
        ),
    ]
    model.Project.query.count.return_value = 1

    keycloak_mock.user_get_name.return_value = 'test-user'

    rv = client.get(
        f'{API_BASE}/openstack/project',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'cloud_id': 1,
                'cloud_name': 'test_cloud',
                'name': 'test_project',
                'description': '',
                'owner_id': '00000000-0000-0000-0000-000000000000',
                'owner_name': 'test-user',
                'group_id': None,
                'group_name': None,
                '_href': ANY,
            }
        ],
        'total': 1,
    }


def test_list_project_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/openstack/project',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_get_project(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    model.Project.query.get.return_value = model.Project(
        id=1,
        cloud_id=1,
        cloud=cloud,
        name='test_project',
        description='',
        owner_id='00000000-0000-0000-0000-000000000000',
    )

    keycloak_mock.user_get_name.return_value = 'test-user'

    rv = client.get(
        f'{API_BASE}/openstack/project/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Project.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'cloud_id': 1,
        'cloud_name': 'test_cloud',
        'name': 'test_project',
        'description': '',
        'owner_id': '00000000-0000-0000-0000-000000000000',
        'owner_name': 'test-user',
        'group_id': None,
        'group_name': None,
        '_href': ANY,
    }


def test_get_project_non_existent(client):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/openstack/project/{project_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Project.query.get.assert_called_with(project_id)

    assert rv.status_code == 404
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Project {project_id} does not exist'


def test_get_project_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/openstack/project/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_project(client, db_session_mock, keycloak_mock, mocker):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    project_data = {
        'cloud_id': 1,
        'name': 'test_project',
        'description': '',
        'owner_id': '00000000-0000-0000-0000-000000000000',
    }

    model.Project.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'cloud': cloud,
    })

    keycloak_mock.user_get_name.return_value = 'test-user'

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers={'Authorization': 'Bearer foobar'},
        json=project_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    project = db_session_mock.add.call_args.args[0]
    for k, v in project_data.items():
        assert getattr(project, k) == v


def test_create_project_existing_name(client, db_session_mock):
    project_data = {
        'cloud_id': 1,
        'name': 'test_project',
        'description': '',
        'owner_id': '00000000-0000-0000-0000-000000000000',
    }

    model.Project.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers={'Authorization': 'Bearer foobar'},
        json=project_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Project with the same name {project_data["name"]!r} in the cloud '
        f'{project_data["cloud_id"]!r} already exists'
    )


def test_create_project_existing_name(client, db_session_mock):
    project_data = {
        'cloud_id': 1,
        'description': '',
        'owner_id': '00000000-0000-0000-0000-000000000000',
    }

    model.Project.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers={'Authorization': 'Bearer foobar'},
        json=project_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == '\'name\' is a required property'


def test_create_project_unauthorized(client, db_session_mock):
    project_data = {
        'cloud_id': 1,
        'name': 'test_project',
        'description': '',
        'owner_id': '00000000-0000-0000-0000-000000000000',
    }

    rv = client.post(
        f'{API_BASE}/openstack/project',
        json=project_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_project(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    project = model.Project(
        id=1,
        cloud_id=1,
        cloud=cloud,
        name='test_project',
        description='',
        owner_id='00000000-0000-0000-0000-000000000000',
    )
    model.Project.query.get.return_value = project

    keycloak_mock.user_get_name.return_value = 'test-user'

    rv = client.patch(
        f'{API_BASE}/openstack/project/1',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new_name',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.Project.query.get.assert_called_with(1)

    assert project.name == 'new_name'
    assert project.description == 'new desc'
    

def test_update_project_non_existent(client):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/openstack/project/{project_id}',
        headers={'Authorization': 'Bearer foobar'},
        json={
            'name': 'new_name',
            'description': 'new desc',
        },
    )

    model.Project.query.get.assert_called_with(project_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Project {project_id} does not exist'


def test_update_project_unauthorized(client, keycloak_mock):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id='00000000-0000-0000-0000-000000000000',
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    project = model.Project(
        id=1,
        cloud_id=1,
        cloud=cloud,
        name='test_project',
        description='',
        owner_id='00000000-0000-0000-0000-000000000000',
    )
    model.Project.query.get.return_value = project

    keycloak_mock.user_get_name.return_value = 'test-user'

    rv = client.patch(
        f'{API_BASE}/openstack/project/{project.id}',
        json={
            'name': 'new_name',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'

    assert project.name == 'test_project'
    assert project.description == ''


def test_delete_project(client, db_session_mock, keycloak_mock):
    project = model.Project(
        id=1,
        cloud_id=1,
        name='test_project',
        description='',
        owner_id='00000000-0000-0000-0000-000000000000',
    )
    model.Project.query.get.return_value = project

    rv = client.delete(
        f'{API_BASE}/openstack/project/1',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 204, rv.data

    model.Project.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(project)


def test_delete_project_non_existent(client, db_session_mock):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/openstack/project/{project_id}',
        headers={'Authorization': 'Bearer foobar'},
    )

    model.Project.query.get.assert_called_with(project_id)
    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Project {project_id} does not exist'


def test_delete_project_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/openstack/project/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'
