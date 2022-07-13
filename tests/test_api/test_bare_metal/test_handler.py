from rhub.bare_metal.model import (
    BareMetalHandler,
    BareMetalIronicHandler,
    BareMetalHandlerType,
    BareMetalHandlerStatus,
    BareMetalArch,
)

API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)

    return side_effect


def test_list_handlers(client):
    BareMetalIronicHandler.query.all.return_value = [
        BareMetalIronicHandler(
            id=1,
            name='setup1',
            type=BareMetalHandlerType.IRONIC,
            arch=BareMetalArch.x86_64,
            status=BareMetalHandlerStatus.AVAILABLE,
            last_check=None,
            last_check_error=None,
            location_id=1,
            user_name='admin',
            base_url='http://ironic-server-host.example.com:6385',
            hostname='ironic-server-host.example.com',
            created_at='2000-01-01T00:00:00.000000+00:00',
            updated_at='2000-01-01T00:00:00.000000+00:00',
        ),
    ]
    BareMetalIronicHandler.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/bare_metal/handler',
    )

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'setup1',
                'type': BareMetalHandlerType.IRONIC,
                'arch': BareMetalArch.x86_64,
                'status': BareMetalHandlerStatus.AVAILABLE,
                'last_check': None,
                'last_check_error': None,
                'location_id': 1,
                'user_name': 'admin',
                'base_url': 'http://ironic-server-host.example.com:6385',
                'hostname': 'ironic-server-host.example.com',
                'created_at': '2000-01-01T00:00:00.000000+00:00',
                'updated_at': '2000-01-01T00:00:00.000000+00:00',
            }
        ],
        'total': 1,
    }


def test_get_handler(client):
    BareMetalHandler.query.get.return_value = BareMetalIronicHandler(
        id=1,
        name='setup1',
        type=BareMetalHandlerType.IRONIC,
        arch=BareMetalArch.x86_64,
        status=BareMetalHandlerStatus.AVAILABLE,
        last_check=None,
        last_check_error=None,
        location_id=1,
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
        user_name='admin',
        base_url='http://ironic-server-host.example.com:6385',
        hostname='ironic-server-host.example.com',
    )

    rv = client.get(f'{API_BASE}/bare_metal/handler/1')

    BareMetalHandler.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'name': 'setup1',
        'type': BareMetalHandlerType.IRONIC,
        'arch': BareMetalArch.x86_64,
        'status': BareMetalHandlerStatus.AVAILABLE,
        'last_check': None,
        'last_check_error': None,
        'location_id': 1,
        'created_at': '2000-01-01T00:00:00.000000+00:00',
        'updated_at': '2000-01-01T00:00:00.000000+00:00',
        'user_name': 'admin',
        'base_url': 'http://ironic-server-host.example.com:6385',
        'hostname': 'ironic-server-host.example.com',
    }


def test_create_handler(client, db_session_mock, mocker):
    handler_data = {
        'name': 'setup1',
        'arch': BareMetalArch.x86_64,
        'location_id': 1,
        'user_name': 'admin',
        'password': 'pass',
        'base_url': 'http://ironic-server-host.example.com:6385',
        'hostname': 'ironic-server-host.example.com',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})
    task_mock = mocker.patch(
        'rhub.bare_metal.tasks.handler.ironic_update_status_task.delay'
    )

    rv = client.post(
        f'{API_BASE}/bare_metal/handler',
        json=handler_data,
    )

    db_session_mock.add.assert_called()
    task_mock.assert_called_once_with(1)

    assert rv.status_code == 200, rv.data

    handler = db_session_mock.add.call_args.args[0]
    for k, v in handler_data.items():
        assert getattr(handler, k) == v
