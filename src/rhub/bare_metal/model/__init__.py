# flake8: noqa: F401

from sqlalchemy.orm import with_polymorphic

from .common import (
    BareMetalArch,
    BareMetalBootType,
    BareMetalException,
    IronicClientException,
)

from .handler import (
    BareMetalHandler,
    BareMetalHandlerStatus,
    BareMetalHandlerType,
    BareMetalIronicHandler,
    IronicClient,
    IronicNode,
)
from .host import (
    BareMetalHost,
    BareMetalHostDrac,
    BareMetalHostRedfish,
    BareMetalHostStatus,
    BareMetalHardwareType,
)
from .image import (
    BareMetalImage,
    BareMetalImageISO,
    BareMetalImageQCOW2,
    BareMetalImageType,
    ImageBaseOS,
)
from .provision import (
    BareMetalProvision,
    BareMetalProvisionISO,
    BareMetalProvisionQCOW2,
    BareMetalProvisionStatus,
    BareMetalProvisionType,
)

bare_metal_host_full = with_polymorphic(
    BareMetalHost, [BareMetalHostDrac, BareMetalHostRedfish]
)
bare_metal_image_full = with_polymorphic(
    BareMetalImage, [BareMetalImageISO, BareMetalImageQCOW2]
)
bare_metal_provision_full = with_polymorphic(
    BareMetalProvision, [BareMetalProvisionISO, BareMetalProvisionQCOW2]
)
