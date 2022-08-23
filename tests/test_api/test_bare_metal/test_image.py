from rhub.api import db
from rhub.bare_metal.model import (
    BareMetalImage,
    BareMetalImageISO,
    ImageBaseOS,
    BareMetalImageType,
    BareMetalArch,
)

API_BASE = '/v0'


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)

    return side_effect


def test_list_images(client):
    db.session.query.return_value.all.return_value = [
        BareMetalImageISO(
            id=1,
            version='36',
            description='',
            base_os=ImageBaseOS.FEDORA,
            type=BareMetalImageType.ISO,
            arch=BareMetalArch.x86_64,
            legacy_bios=True,
            uefi=True,
            uefi_secure_boot=True,
            download_url='https://download.fedoraproject.org/pub/fedora/linux'
                         '/releases/36/Server/x86_64/iso/Fedora-Server-dvd'
                         '-x86_64-36-1.5.iso',
            iso_sha256='a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492f562f0f'
                       '1f9449e89',
            kernel_sub_path='images/pxeboot/vmlinuz',
            initramfs_sub_path='images/pxeboot/initrd.img',
            source_sub_path='images/pxeboot/initrd.img',
            stage2_sub_path='images/install.img',
            created_at='2000-01-01T00:00:00.000000+00:00',
            updated_at='2000-01-01T00:00:00.000000+00:00',
        ),
    ]
    db.session.query.return_value.count.return_value = 1

    rv = client.get(f'{API_BASE}/bare_metal/image')

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'version': '36',
                'description': '',
                'base_os': ImageBaseOS.FEDORA,
                'type': BareMetalImageType.ISO,
                'arch': BareMetalArch.x86_64,
                'legacy_bios': True,
                'uefi': True,
                'uefi_secure_boot': True,
                'download_url':
                    'https://download.fedoraproject.org/pub/fedora/linux'
                    '/releases/36/Server/x86_64/iso/Fedora-Server-dvd-x86_64'
                    '-36-1.5.iso',
                'iso_sha256': 'a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492'
                              'f562f0f1f9449e89',
                'kernel_sub_path': 'images/pxeboot/vmlinuz',
                'initramfs_sub_path': 'images/pxeboot/initrd.img',
                'source_sub_path': 'images/pxeboot/initrd.img',
                'stage2_sub_path': 'images/install.img',
                'created_at': '2000-01-01T00:00:00.000000+00:00',
                'updated_at': '2000-01-01T00:00:00.000000+00:00',
            }
        ],
        'total': 1
    }


def test_get_image(client):
    BareMetalImage.query.get.return_value = BareMetalImageISO(
        id=1,
        version='36',
        description='',
        base_os=ImageBaseOS.FEDORA,
        type=BareMetalImageType.ISO,
        arch=BareMetalArch.x86_64,
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
        download_url='https://download.fedoraproject.org/pub/fedora/linux'
                     '/releases/36/Server/x86_64/iso/Fedora-Server-dvd-x86_64'
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

    rv = client.get(f'{API_BASE}/bare_metal/image/1')

    BareMetalImage.query.get.assert_called_with(1)

    assert rv.status_code == 200, rv.data
    assert rv.json == {
        'id': 1,
        'version': '36',
        'description': '',
        'base_os': ImageBaseOS.FEDORA,
        'type': BareMetalImageType.ISO,
        'arch': BareMetalArch.x86_64,
        'legacy_bios': True,
        'uefi': True,
        'uefi_secure_boot': True,
        'download_url': 'https://download.fedoraproject.org/pub/fedora/linux'
                        '/releases/36/Server/x86_64/iso/Fedora-Server-dvd'
                        '-x86_64-36-1.5.iso',
        'iso_sha256':
            'a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492f562f0f1f9449e89',
        'kernel_sub_path': 'images/pxeboot/vmlinuz',
        'initramfs_sub_path': 'images/pxeboot/initrd.img',
        'source_sub_path': 'images/pxeboot/initrd.img',
        'stage2_sub_path': 'images/install.img',
        'created_at': '2000-01-01T00:00:00.000000+00:00',
        'updated_at': '2000-01-01T00:00:00.000000+00:00',
    }


def test_create_image(client, db_session_mock):
    image_data = {
        'version': '36',
        'base_os': ImageBaseOS.FEDORA,
        'arch': BareMetalArch.x86_64,
        'download_url': 'https://download.fedoraproject.org/pub/fedora/linux'
                        '/releases/36/Server/x86_64/iso/Fedora-Server-dvd'
                        '-x86_64-36-1.5.iso',
        'iso_sha256':
            'a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492f562f0f1f9449e89',
        'kernel_sub_path': 'images/pxeboot/vmlinuz',
        'initramfs_sub_path': 'images/pxeboot/initrd.img',
        'source_sub_path': 'images/pxeboot/initrd.img',
        'stage2_sub_path': 'images/install.img',
    }

    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/bare_metal/image',
        json=image_data,
    )

    db_session_mock.add.assert_called()

    image = db_session_mock.add.call_args.args[0]
    for key, value in image_data.items():
        assert getattr(image, key) == value

    assert rv.status_code == 200, rv.data
