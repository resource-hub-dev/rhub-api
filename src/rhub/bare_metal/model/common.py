import enum
from pathlib import Path

from ironicclient.exc import ClientException
from ironicclient.v1.node import Node

# TODO: add on ironic model
BARE_METAL_IMAGES_BASE_PATH = Path("/var/lib/ironic/httpboot/images")
BARE_METAL_KICKSTART_BASE_PATH = Path("/var/lib/ironic/httpboot/kickstart_files")
IRONIC_HTTP_IMAGES_URL = "http://192.168.1.1:8080/images"

BARE_METAL_UTILS_PATH = Path(__file__).parent / "data"

# TODO: fix.
#  May use: https://docs.sqlalchemy.org/en/14/orm/declarative_mixins.html
#           #mixing-in-relationships
_BM_TABLE_NAME_HANDLER = "bare_metal_handler"
_BM_TABLE_NAME_HOST = "bare_metal_host"
_BM_TABLE_NAME_HOST_DRAC = f"{_BM_TABLE_NAME_HOST}_drac"
_BM_TABLE_NAME_HOST_REDFISH = f"{_BM_TABLE_NAME_HOST}_redfish"
_BM_TABLE_NAME_IMAGE = "bare_metal_image"
_BM_TABLE_NAME_IMAGE_ISO = f"{_BM_TABLE_NAME_IMAGE}_iso"
_BM_TABLE_NAME_IMAGE_QCOW2 = f"{_BM_TABLE_NAME_IMAGE}_qcow2"
_BM_TABLE_NAME_PROVISION = "bare_metal_provision"
_BM_TABLE_NAME_PROVISION_ISO = f"{_BM_TABLE_NAME_PROVISION}_iso"
_BM_TABLE_NAME_PROVISION_QCOW2 = f"{_BM_TABLE_NAME_PROVISION}_qcow2"

IronicNode = Node
IronicClientException = ClientException


class BareMetalException(Exception):
    """Base bare metal exception"""


class BareMetalArch(str, enum.Enum):
    x86_64 = "x86_64"


class BareMetalBootType(str, enum.Enum):
    LEGACY_BIOS = "legacy_bios"
    UEFI = "UEFI"
    SECURE_BOOT = "secure_boot"
