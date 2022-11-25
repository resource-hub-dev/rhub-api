import base64
from unittest.mock import ANY

import pytest
import sqlalchemy.exc

from rhub.auth import model as auth_model
from rhub.openstack import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


@pytest.fixture
def auth_user(mocker):
    return auth_model.User(
        id=1,
        name='testuser',
        email='testuser@example.com',
    )


@pytest.fixture
def auth_group(mocker):
    return auth_model.Group(
        id=1,
        name='testuser',
    )


def test_list_clouds(client, auth_group):
    model.Cloud.query.limit.return_value.offset.return_value = [
        model.Cloud(
            id=1,
            name='test',
            description='',
            owner_group_id=auth_group.id,
            owner_group=auth_group,
            url='https://openstack.example.com:13000',
            credentials='kv/test',
            domain_name='Default',
            domain_id='default',
            networks=['test_net'],
        ),
    ]
    model.Cloud.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/openstack/cloud',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'test',
                'description': '',
                'owner_group_id': auth_group.id,
                'owner_group_name': auth_group.name,
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


def test_get_cloud(client, auth_group):
    model.Cloud.query.get.return_value = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )

    rv = client.get(
        f'{API_BASE}/openstack/cloud/1',
        headers=AUTH_HEADER,
    )

    model.Cloud.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'name': 'test',
        'description': '',
        'owner_group_id': auth_group.id,
        'owner_group_name': auth_group.name,
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
        headers=AUTH_HEADER,
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


def test_create_cloud(client, db_session_mock, auth_group, mocker):
    cloud_data = {
        'name': 'test',
        'description': '',
        'owner_group_id': auth_group.id,
        'url': 'https://openstack.example.com:13000',
        'credentials': 'kv/test',
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'owner_group': auth_group,
    })

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers=AUTH_HEADER,
        json=cloud_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    cloud = db_session_mock.add.call_args.args[0]
    for k, v in cloud_data.items():
        assert getattr(cloud, k) == v


def test_create_cloud_existing_name(
        client,
        db_session_mock,
        db_unique_violation,
        vault_mock,
    ):
    cloud_data = {
        'name': 'test-name',
        'description': '',
        'owner_group_id': 1,
        'url': 'https://openstack.example.com:13000',
        'credentials': {'username': 'foo', 'password': 'bar'},
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    db_unique_violation('name', 'test-name')

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers=AUTH_HEADER,
        json=cloud_data,
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'Key (name)=(test-name) already exists.'

    vault_mock.write.assert_not_called()


def test_create_cloud_missing_name(client, db_session_mock, vault_mock):
    cloud_data = {
        'description': '',
        'owner_group_id': 1,
        'url': 'https://openstack.example.com:13000',
        'credentials': {'username': 'foo', 'password': 'bar'},
        'domain_name': 'Default',
        'domain_id': 'default',
        'networks': ['test_net'],
    }

    rv = client.post(
        f'{API_BASE}/openstack/cloud',
        headers=AUTH_HEADER,
        json=cloud_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == '\'name\' is a required property'

    vault_mock.write.assert_not_called()


def test_create_cloud_unauthorized(client, db_session_mock, vault_mock):
    cloud_data = {
        'name': 'test',
        'description': '',
        'owner_group_id': 1,
        'url': 'https://openstack.example.com:13000',
        'credentials': {'username': 'foo', 'password': 'bar'},
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

    vault_mock.write.assert_not_called()


def test_update_cloud(client, auth_group):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/1',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.Cloud.query.get.assert_called_with(1)

    assert cloud.name == 'new'
    assert cloud.description == 'new desc'


def test_update_cloud_existing_name(
        client,
        db_session_mock,
        vault_mock,
        auth_group,
        db_unique_violation,
    ):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    db_unique_violation('name', 'new')

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/1',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'credentials': {'username': 'foo', 'password': 'bar'},
        },
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'Key (name)=(new) already exists.'

    model.Cloud.query.get.assert_called_with(1)

    vault_mock.write.assert_not_called()


def test_update_cloud_non_existent(client, vault_mock):
    cloud_id = 1

    model.Cloud.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/{cloud_id}',
        headers=AUTH_HEADER,
        json={
            'name': 'new',
            'description': 'new desc',
            'credentials': {'username': 'foo', 'password': 'bar'},
        },
    )

    model.Cloud.query.get.assert_called_with(cloud_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Cloud {cloud_id} does not exist'

    vault_mock.write.assert_not_called()


def test_update_cloud_unauthorized(client, auth_group, vault_mock):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    rv = client.patch(
        f'{API_BASE}/openstack/cloud/{cloud.id}',
        json={
            'name': 'new',
            'description': 'new desc',
            'credentials': {'username': 'foo', 'password': 'bar'},
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'

    assert cloud.name == 'test'
    assert cloud.description == ''

    vault_mock.write.assert_not_called()


def test_delete_cloud(client, db_session_mock, auth_group):
    cloud = model.Cloud(
        id=1,
        name='test',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
        url='https://openstack.example.com:13000',
        credentials='kv/test',
        domain_name='Default',
        domain_id='default',
        networks=['test_net'],
    )
    model.Cloud.query.get.return_value = cloud

    rv = client.delete(
        f'{API_BASE}/openstack/cloud/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204, rv.data

    model.Cloud.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(cloud)


def test_delete_cloud_non_existent(client, db_session_mock):
    cloud_id = 1

    model.Cloud.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/openstack/cloud/{cloud_id}',
        headers=AUTH_HEADER,
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


def test_list_projects(client, auth_group, auth_user):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
            owner_id=auth_user.id,
            owner=auth_user,
        ),
    ]
    model.Project.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/openstack/project',
        headers=AUTH_HEADER,
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
                'owner_id': auth_user.id,
                'owner_name': auth_user.name,
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


def test_get_project(client, auth_user, auth_group):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
        owner_id=auth_user.id,
        owner=auth_user,
    )

    rv = client.get(
        f'{API_BASE}/openstack/project/1',
        headers=AUTH_HEADER,
    )

    model.Project.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'cloud_id': 1,
        'cloud_name': 'test_cloud',
        'name': 'test_project',
        'description': '',
        'owner_id': auth_user.id,
        'owner_name': auth_user.name,
        'group_id': None,
        'group_name': None,
        '_href': ANY,
    }


def test_get_project_non_existent(client):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/openstack/project/{project_id}',
        headers=AUTH_HEADER,
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


def test_create_project(client, db_session_mock, auth_user, auth_group, mocker):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
        'owner_id': auth_user.id,
    }

    model.Project.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({
        'id': 1,
        'cloud': cloud,
        'owner': auth_user,
    })

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers=AUTH_HEADER,
        json=project_data,
    )

    assert rv.status_code == 200, rv.data

    db_session_mock.add.assert_called()

    project = db_session_mock.add.call_args.args[0]
    for k, v in project_data.items():
        assert getattr(project, k) == v


def test_create_project_existing_name(client, db_session_mock, db_unique_violation):
    project_data = {
        'cloud_id': 1,
        'name': 'test_project',
        'description': '',
        'owner_id': 1,
    }

    db_unique_violation('cloud_id, name', '1, test_project')

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers=AUTH_HEADER,
        json=project_data,
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == (
        f'Key (cloud_id, name)=(1, test_project) already exists.'
    )


def test_create_project_missing_name(client, db_session_mock):
    project_data = {
        'cloud_id': 1,
        'description': '',
        'owner_id': 1,
    }

    rv = client.post(
        f'{API_BASE}/openstack/project',
        headers=AUTH_HEADER,
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
        'owner_id': 1,
    }

    rv = client.post(
        f'{API_BASE}/openstack/project',
        json=project_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_project(client, auth_user, auth_group):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
        owner_id=auth_user.id,
        owner=auth_user,
    )
    model.Project.query.get.return_value = project

    rv = client.patch(
        f'{API_BASE}/openstack/project/1',
        headers=AUTH_HEADER,
        json={
            'description': 'new desc',
        },
    )

    assert rv.status_code == 200, rv.data

    model.Project.query.get.assert_called_with(1)

    assert project.description == 'new desc'


def test_update_project_non_existent(client):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/openstack/project/{project_id}',
        headers=AUTH_HEADER,
        json={
            'description': 'new desc',
        },
    )

    model.Project.query.get.assert_called_with(project_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'Project {project_id} does not exist'


def test_update_project_unauthorized(client, auth_user, auth_group):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
        owner_id=auth_user.id,
        owner=auth_user,
    )
    model.Project.query.get.return_value = project

    rv = client.patch(
        f'{API_BASE}/openstack/project/{project.id}',
        json={
            'description': 'new desc',
        },
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'

    assert project.description == ''


@pytest.mark.parametrize(
    'field, value',
    [
        pytest.param('name', 'newname', id='name'),
        pytest.param('cloud_id', 100, id='cluster_id'),
    ]
)
def test_update_project_ro_field(
    client, db_session_mock, auth_user, auth_group, field, value
):
    cloud = model.Cloud(
        id=1,
        name='test_cloud',
        description='',
        owner_group_id=auth_group.id,
        owner_group=auth_group,
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
        owner_id=auth_user.id,
        owner=auth_user,
    )
    model.Project.query.get.return_value = project

    rv = client.patch(
        f'{API_BASE}/openstack/project/1',
        headers=AUTH_HEADER,
        json={field: value},
    )

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'Project {field} field cannot be changed.'

    db_session_mock.commit.assert_not_called()


def test_delete_project(client, db_session_mock, auth_user):
    project = model.Project(
        id=1,
        cloud_id=1,
        name='test_project',
        description='',
        owner_id=auth_user.id,
        owner=auth_user,
    )
    model.Project.query.get.return_value = project

    rv = client.delete(
        f'{API_BASE}/openstack/project/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204, rv.data

    model.Project.query.get.assert_called_with(1)
    db_session_mock.delete.assert_called_with(project)


def test_delete_project_non_existent(client, db_session_mock):
    project_id = 1

    model.Project.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/openstack/project/{project_id}',
        headers=AUTH_HEADER,
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
