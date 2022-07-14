from unittest.mock import PropertyMock
from rhub.api import db
from rhub.bare_metal.model import (
    BareMetalHost,
    BareMetalHostStatus,
    BareMetalHandlerStatus,
    BareMetalArch,
    BareMetalHardwareType,
    BareMetalIronicHandler,
    BareMetalHandlerType,
)

import pytest

API_BASE = '/v0'


@pytest.fixture()
def host_task_mock(mocker):
    yield mocker.patch(
        'rhub.bare_metal.tasks.host.ironic_enroll_host_task.delay'
    )


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)

    return side_effect


def test_list_hosts(client):
    db.session.query.return_value.all.return_value = [
        BareMetalHost(
            id=1,
            name='target-bm-host.example.com',
            mac='11:22:33:44:55:66',
            arch=BareMetalArch.x86_64,
            legacy_bios=True,
            uefi=True,
            uefi_secure_boot=True,
            ipxe_support=True,
            status=BareMetalHostStatus.NON_ENROLLED,
            type=BareMetalHardwareType.GENERIC,
            handler_id=1,
            handler_uuid=None,
            handler_data=None,
            ipmi_username='root',
            ipmi_address='target-bm-host-drac.mgmt.example.com',
            ipmi_port='623',
            created_at='2000-01-01T00:00:00.000000+00:00',
            updated_at='2000-01-01T00:00:00.000000+00:00',
        )
    ]
    db.session.query.return_value.count.return_value = 1

    rv = client.get(f'{API_BASE}/bare_metal/host')

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'target-bm-host.example.com',
                'mac': '11:22:33:44:55:66',
                'arch': BareMetalArch.x86_64,
                'legacy_bios': True,
                'uefi': True,
                'uefi_secure_boot': True,
                'ipxe_support': True,
                'status': BareMetalHostStatus.NON_ENROLLED,
                'type': BareMetalHardwareType.GENERIC,
                'handler_id': 1,
                'handler_uuid': None,
                'handler_data': None,
                'ipmi_username': 'root',
                'ipmi_address': 'target-bm-host-drac.mgmt.example.com',
                'ipmi_port': '623',
                'created_at': '2000-01-01T00:00:00.000000+00:00',
                'updated_at': '2000-01-01T00:00:00.000000+00:00',
            }
        ],
        'total': 1,
    }


def test_get_host(client):
    BareMetalHost.query.get.return_value = BareMetalHost(
        id=1,
        name='target-bm-host.example.com',
        mac='11:22:33:44:55:66',
        arch=BareMetalArch.x86_64,
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
        ipxe_support=True,
        status=BareMetalHostStatus.NON_ENROLLED,
        type=BareMetalHardwareType.GENERIC,
        handler_id=1,
        handler_uuid=None,
        handler_data=None,
        ipmi_username='root',
        ipmi_address='target-bm-host-drac.mgmt.example.com',
        ipmi_port='623',
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    rv = client.get(f'{API_BASE}/bare_metal/host/1')

    BareMetalHost.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'name': 'target-bm-host.example.com',
        'mac': '11:22:33:44:55:66',
        'arch': BareMetalArch.x86_64,
        'legacy_bios': True,
        'uefi': True,
        'uefi_secure_boot': True,
        'ipxe_support': True,
        'status': BareMetalHostStatus.NON_ENROLLED,
        'type': BareMetalHardwareType.GENERIC,
        'handler_id': 1,
        'handler_uuid': None,
        'handler_data': None,
        'ipmi_username': 'root',
        'ipmi_address': 'target-bm-host-drac.mgmt.example.com',
        'ipmi_port': '623',
        'created_at': '2000-01-01T00:00:00.000000+00:00',
        'updated_at': '2000-01-01T00:00:00.000000+00:00',
    }


def test_create_ipmi_host(client, db_session_mock, host_task_mock):
    host_data = {
        'name': 'target-bm-host.example.com',
        'mac': '11:22:33:44:55:66',
        'arch': BareMetalArch.x86_64,
        'handler_id': 1,
        'ipmi_username': 'root',
        'ipmi_password': 'pass',
        'ipmi_address': 'target-bm-host-drac.mgmt.example.com',
        'ipmi_port': '623',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/bare_metal/host/ipmi',
        json=host_data,
    )

    db_session_mock.add.assert_called()
    host_task_mock.assert_called_once_with(1)

    assert rv.status_code == 200, rv.data

    host = db_session_mock.add.call_args.args[0]
    for k, v in host_data.items():
        assert getattr(host, k) == v


def test_create_redfish_host(client, db_session_mock, host_task_mock):
    host_data = {
        'name': 'target-bm-host.example.com',
        'mac': '11:22:33:44:55:66',
        'arch': BareMetalArch.x86_64,
        'handler_id': 1,
        'ipmi_username': 'root',
        'ipmi_password': 'pass',
        'ipmi_address': 'target-bm-host-drac.mgmt.example.com',
        'ipmi_port': '623',
        'redfish_address': 'https://target-bm-host-drac.mgmt.example.com'
                           '/redfish/v1',
        'redfish_username': 'root',
        'redfish_password': 'pass',
        'redfish_system_id': '/redfish/v1/Systems/System.Embedded.1',
        'redfish_verify_ca': True,
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/bare_metal/host/redfish',
        json=host_data,
    )

    db_session_mock.add.assert_called()
    host_task_mock.assert_called_once_with(1)

    assert rv.status_code == 200, rv.data

    host = db_session_mock.add.call_args.args[0]
    for k, v in host_data.items():
        assert getattr(host, k) == v


def test_create_drac_host(client, db_session_mock, host_task_mock):
    host_data = {
        'name': 'target-bm-host.example.com',
        'mac': '11:22:33:44:55:66',
        'arch': BareMetalArch.x86_64,
        'handler_id': 1,
        'ipmi_username': 'root',
        'ipmi_password': 'pass',
        'ipmi_address': 'target-bm-host-drac.mgmt.example.com',
        'ipmi_port': '623',
        'redfish_address': 'https://target-bm-host-drac.mgmt.example.com'
                           '/redfish/v1',
        'redfish_username': 'root',
        'redfish_password': 'pass',
        'redfish_system_id': '/redfish/v1/Systems/System.Embedded.1',
        'redfish_verify_ca': True,
        'drac_address': 'target-bm-host-drac.mgmt.example.com',
        'drac_username': 'root',
        'drac_password': 'pass',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/bare_metal/host/drac',
        json=host_data,
    )

    db_session_mock.add.assert_called()
    host_task_mock.assert_called_once_with(1)

    assert rv.status_code == 200, rv.data

    host = db_session_mock.add.call_args.args[0]
    for k, v in host_data.items():
        assert getattr(host, k) == v


def test_get_host_power_state(client, mocker):
    BareMetalHost.query.get.return_value = BareMetalHost(
        id=1,
        name='target-bm-host.example.com',
        mac='11:22:33:44:55:66',
        arch=BareMetalArch.x86_64,
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
        ipxe_support=True,
        status=BareMetalHostStatus.AVAILABLE,
        type=BareMetalHardwareType.GENERIC,
        handler_id=1,
        handler=BareMetalIronicHandler(
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
            hostname='ironic-server-host.example.com', ),
        handler_uuid='00000000-0000-0000-0000-000000000000',
        handler_data=None,
        ipmi_username='root',
        ipmi_address='target-bm-host-drac.mgmt.example.com',
        ipmi_port='623',
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    power_state_mock = mocker.patch(
        'rhub.bare_metal.model.BareMetalHost.power_state',
        new_callable=PropertyMock,
    )
    power_state_mock.return_value = 'power_on'

    rv = client.get(f'{API_BASE}/bare_metal/host/1/power_state')

    BareMetalHost.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {'power_state': 'power_on'}
