from io import BytesIO

from rhub.api import db
from rhub.bare_metal.model import (
    BareMetalProvision,
    BareMetalProvisionISO,
    BareMetalProvisionType,
    BareMetalBootType,
    BareMetalProvisionStatus,
    BareMetalHost,
    BareMetalHostStatus, 
    BareMetalHardwareType,
    BareMetalIronicHandler,
    BareMetalHandlerStatus,
    BareMetalHandlerType,
    BareMetalImage,
    BareMetalImageISO,
    ImageBaseOS,
    BareMetalImageType,
)
from rhub.bare_metal.model.common import BareMetalArch

API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)

    return side_effect


def test_list_provisions(client):
    db.session.query.return_value.all.return_value = [
        BareMetalProvisionISO(
            id=1,
            description='description',
            type=BareMetalProvisionType.ISO,
            boot_type=BareMetalBootType.UEFI,
            status=BareMetalProvisionStatus.QUEUED,
            host_id=1,
            host_reservation_expires_at=None,
            logs_path=None,
            kickstart='test_kickstart',
            image_id=1,
            created_at='2000-01-01T00:00:00.000000+00:00',
            updated_at='2000-01-01T00:00:00.000000+00:00',
        ),
    ]
    db.session.query.return_value.count.return_value = 1

    rv = client.get(f'{API_BASE}/bare_metal/provision')

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'description': 'description',
                'type': BareMetalProvisionType.ISO,
                'boot_type': BareMetalBootType.UEFI,
                'status': BareMetalProvisionStatus.QUEUED,
                'host_id': 1,
                'host_reservation_expires_at': None,
                'logs_path': None,
                'kickstart': 'test_kickstart',
                'image_id': 1,
                'created_at': '2000-01-01T00:00:00.000000+00:00',
                'updated_at': '2000-01-01T00:00:00.000000+00:00',
            },
        ],
        'total': 1,
    }


def test_get_provision(client):
    BareMetalProvision.query.get.return_value = BareMetalProvisionISO(
        id=1,
        description='description',
        type=BareMetalProvisionType.ISO,
        boot_type=BareMetalBootType.UEFI,
        status=BareMetalProvisionStatus.QUEUED,
        host_id=1,
        host_reservation_expires_at=None,
        logs_path=None,
        kickstart='test_kickstart',
        image_id=1,
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    rv = client.get(f'{API_BASE}/bare_metal/provision/1')

    BareMetalProvision.query.get.assert_called_with(1)
    
    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'description': 'description',
        'type': BareMetalProvisionType.ISO,
        'boot_type': BareMetalBootType.UEFI,
        'status': BareMetalProvisionStatus.QUEUED,
        'host_id': 1,
        'host_reservation_expires_at': None,
        'logs_path': None,
        'kickstart': 'test_kickstart',
        'image_id': 1,
        'created_at': '2000-01-01T00:00:00.000000+00:00',
        'updated_at': '2000-01-01T00:00:00.000000+00:00',
    }


def test_create_provision(client, db_session_mock, mocker):
    provision_data = {
        'description': 'description',
        'boot_type': 'legacy_bios',
        'host_id': 1,
        'image_id': 1,
        'kickstart': 'test_kickstart',
    }

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
            user_name='admin',
            base_url='http://ironic-server-host.example.com:6385',
            hostname='ironic-server-host.example.com',
            created_at='2000-01-01T00:00:00.000000+00:00',
            updated_at='2000-01-01T00:00:00.000000+00:00',
        ),
        handler_uuid=None,
        handler_data=None,
        ipmi_username='root',
        ipmi_address='target-bm-host-drac.mgmt.example.com',
        ipmi_port='623',
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    BareMetalImage.query.get.return_value = BareMetalImageISO(
        id=1,
        version='36',
        description='',
        base_os=ImageBaseOS.FEDORA,
        type=BareMetalImageType.ISO,
        arch='x86_64',
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
        download_url='https://download.fedoraproject.org/pub/fedora/linux/'
                     'releases/36/Server/x86_64/iso/Fedora-Server-dvd-x86_64'
                     '-36-1.5.iso',
        iso_sha256='a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492f562f0f1f94'
                   '49e89',
        kernel_sub_path='images/pxeboot/vmlinuz',
        initramfs_sub_path='images/pxeboot/initrd.img',
        source_sub_path='images/pxeboot/initrd.img',
        stage2_sub_path='images/install.img',
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})
    provision_task_mock = mocker.patch(
        'rhub.bare_metal.tasks.provision.ironic_provision_task.delay'
    )

    rv = client.post(
        f'{API_BASE}/bare_metal/provision',
        json=provision_data,
    )

    db_session_mock.add.assert_called()
    provision_task_mock.assert_called_once_with(1)

    provision = db_session_mock.add.call_args.args[0]
    for key, value in provision_data.items():
        assert getattr(provision, key) == value

    assert rv.status_code == 200, rv.data


def test_finish_provision(client, mocker):
    BareMetalProvision.query.get.return_value = BareMetalProvisionISO(
        id=1,
        description='description',
        type=BareMetalProvisionType.ISO,
        boot_type=BareMetalBootType.UEFI,
        status=BareMetalProvisionStatus.QUEUED,
        host_id=1,
        host_reservation_expires_at=None,
        logs_path=None,
        kickstart='test_kickstart',
        image_id=1,
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    provision_task_mock = mocker.patch(
        'rhub.bare_metal.tasks.provision.ironic_provision_stop_task.delay'
    )

    rv = client.post(f'{API_BASE}/bare_metal/provision/1/finish')

    BareMetalProvision.query.get.assert_called_with(1)
    provision_task_mock.assert_called_once_with(1)

    assert rv.status_code == 200, rv.data


def test_get_provision_kickstart(client):
    KICKSTART_VALUE = 'test_kickstart'

    BareMetalProvision.query.get.return_value = BareMetalProvisionISO(
        id=1,
        description='description',
        type=BareMetalProvisionType.ISO,
        boot_type=BareMetalBootType.UEFI,
        status=BareMetalProvisionStatus.QUEUED,
        host_id=1,
        host=BareMetalHost( 
            id=1,
            name='target-bm-host.example.com',
            mac='11:22:33:44:55:66',
            arch='x86_64',
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
        ),
        host_reservation_expires_at=None,
        logs_path=None,
        kickstart='test_kickstart',
        image_id=1,
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    rv = client.get(f'{API_BASE}/bare_metal/provision/1/kickstart')

    BareMetalProvision.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.text == KICKSTART_VALUE


def test_get_provision_kickstart_debug_list(client):
    BareMetalProvision.query.get.return_value = BareMetalProvisionISO(
        id=1,
        description='desc',
        boot_type=BareMetalBootType.UEFI,
        status=BareMetalProvisionStatus.QUEUED,
        host_id=1,
        kickstart='test_kickstart',
        image_id=1,
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    rv = client.get(f'{API_BASE}/bare_metal/provision/1/kickstart/debug_script')

    BareMetalProvision.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert b'#!/bin/bash' in rv.data


def test_post_provision_logs(client):
    file_data = { 'file': (BytesIO(b'foo'), 'foo.tbz') }

    BareMetalProvision.query.get.return_value = BareMetalProvisionISO(
        id=1,
        description='description',
        boot_type=BareMetalBootType.UEFI,
        status=BareMetalProvisionStatus.QUEUED,
        host_id=1,
        host_reservation_expires_at=None,
        logs_path=None,
        image_id=1,
        kickstart='test_kickstart',
        created_at='2000-01-01T00:00:00.000000+00:00',
        updated_at='2000-01-01T00:00:00.000000+00:00',
    )

    rv = client.post(
        f'{API_BASE}/bare_metal/provision/1/logs',
        data=file_data,
    )

    BareMetalProvision.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
