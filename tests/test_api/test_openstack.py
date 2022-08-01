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


def test_get_cloud(client, keycloak_mock):
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
