# MVP - Bare metal provisioning

## Preparation

### Setup - Ironic server

To be used as Ironic server the host's requirements are:

1. CentOS Stream 9
2. root access

#### Install

<!-- TODO: update after https://gitlab.cee.redhat.com/pnt-resource-hub/rhub-baremetal/-/merge_requests/11 -->

Run playbook available on: https://gitlab.cee.redhat.com/pnt-resource-hub/rhub-baremetal

```shell
$ ansible-playbook -i inventory/dsal.yml playbooks/bifrost_setup.yml --extra-vars "target=setup<N>"
```

Get the password, to be used on the next step, while inserting the handler on Resource Hub:

```shell
$ sudo grep -e password /etc/ironic/ironic.conf
```

#### Insertion on Resource Hub

```python
requests.post(
    BASE_URL + 'handler',
    json=dict(
        name='setup<N>',
        arch='x86_64',
        location_id='<LOCATION_ID>',
        user_name='admin',
        password='...',
        base_url='http://ironic-server-host.example.com:6385',
        hostname='ironic-server-host.example.com',
    )
)
```

Resource Hub will run some checks to validate the Ironic access.

### Insert host(s) on Resource Hub

```python
requests.post(
    BASE_URL + 'host/redfish',
    json=dict(
        handler_id='<IRONIC_ID>',
        name='target-bm-host.example.com',
        mac='11:22:33:44:55:66',
        arch='x86_64',
        ipmi_address='target-bm-host-drac.mgmt.example.com',
        ipmi_password='...',
        ipmi_port='623',
        ipmi_username='...',
        redfish_address="https://target-bm-host-drac.mgmt.example.com/redfish/v1",
        redfish_password="...",
        redfish_username="...",
        redfish_verify_ca=False,
        redfish_system_id="/redfish/v1/Systems/System.Embedded.1",
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
    )
)
```

Resource Hub will include this host on Ironic.

### Insert image(s) on Resource Hub

```python
requests.post(
    BASE_URL + 'image',
    json=dict(
        base_os='Fedora',
        version='36',
        arch='x86_64',
        download_url='https://download.fedoraproject.org/pub/fedora/linux/releases/36/Server/x86_64/iso/Fedora-Server-dvd-x86_64-36-1.5.iso',
        iso_sha256='a387f3230acf87ee38707ee90d3c88f44d7bf579e6325492f562f0f1f9449e89',
        kernel_sub_path='images/pxeboot/vmlinuz',
        initramfs_sub_path='images/pxeboot/initrd.img',
        source_sub_path='images/pxeboot/initrd.img',
        stage2_sub_path='images/install.img',
        legacy_bios=True,
        uefi=True,
        uefi_secure_boot=True,
    )
)
```

## Provisioning

### New provisioning
To request a provisioning, the host must be available.

```python
requests.post(
    BASE_URL + 'provision',
    json=dict(
        description='Demo kickstart provisioning',
        host_id='<HOST_ID>',
        image_id='<IMAGE_ID>',
        boot_type='UEFI',
        kickstart='<KICKSTART TEXT>',
    )
)
```

Kickstart example:
```
lang en_US
keyboard us
timezone UTC --utc
#platform x86_64
reboot

## with text, anaconda asks for user input
cmdline
#text

url --url {{ resource_hub.image_url }}
network --bootproto=dhcp --hostname="{{ hostname }}" --device 11:22:33:44:55:66 --activate
network --bootproto=dhcp --hostname="{{ hostname }}" --device 22:33:44:55:66:77 --activate

bootloader --location=mbr --append="rhgb quiet crashkernel=auto" --boot-drive=sda
zerombr
clearpart --drives=sda,sdb --all --initlabel --disklabel gpt
autopart --type=plain

%packages
@^minimal-environment
%end

selinux --enforcing
firewall --disabled
firstboot --disabled

rootpw --plaintext rhub

# Following %pre and %onerror sections are mandatory
%pre
{{ resource_hub.pre }}
%end

%onerror
{{ resource_hub.on_error }}
%end

# Config-drive information, if any.
{{ resource_hub.config_drive }}

# Sending callback after the installation is mandatory.
# This ought to be the last thing done; otherwise the
# ironic-conductor could reboot the node before anaconda
# finishes executing everything in this file.
# The sync makes sure that the data is flushed out to disk,
# before rebooting.
%post
{{ resource_hub.post }}
%end

```

### Finish the provisioning

```python
requests.post(
    BASE_URL + 'provision/<PROVISION_ID>/finish'
)
```