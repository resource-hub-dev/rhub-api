import enum
import logging
from typing import Optional

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import expression
from sqlalchemy import func

from rhub.api import db
from rhub.api.utils import ModelMixin, TimestampMixin
from rhub.bare_metal.model.common import (
    BareMetalArch,
    BareMetalBootType,
    IronicNode,
    _BM_TABLE_NAME_HANDLER,
    _BM_TABLE_NAME_HOST,
    _BM_TABLE_NAME_HOST_DRAC,
    _BM_TABLE_NAME_HOST_REDFISH,
)

logger = logging.getLogger(__name__)


class BareMetalHostStatus(str, enum.Enum):
    AVAILABLE = "available"
    ENROLLING = "enrolling"
    FAILED_ENROLLING = "failed_enrolling"
    MAINTENANCE = "maintenance"
    NON_ENROLLED = "non_enrolled"
    RESERVED = "reserved"


class BareMetalHardwareType(str, enum.Enum):
    GENERIC = "generic"
    DRAC = "drac"
    REDFISH = "redfish"


class BareMetalHost(db.Model, ModelMixin, TimestampMixin):
    __tablename__ = _BM_TABLE_NAME_HOST

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    mac = db.Column(db.String(20), nullable=False)

    #: :type: :class:`BareMetalArch`
    arch = db.Column(db.Enum(BareMetalArch), nullable=False)

    # boot type - TODO: think of some bitwise operation
    legacy_bios = db.Column(db.Boolean, server_default=expression.true(), nullable=False)
    uefi = db.Column(db.Boolean, server_default=expression.true(), nullable=False)
    uefi_secure_boot = db.Column(db.Boolean, server_default=expression.true(), nullable=False)

    ipxe_support = db.Column(db.Boolean, server_default=expression.true(), nullable=False)

    #: :type: :class:`BareMetalHostStatus`
    status = db.Column(
        db.Enum(BareMetalHostStatus),
        server_default=BareMetalHostStatus.NON_ENROLLED.name,
        nullable=False,
    )

    #: :type: :class:`BareMetalHardwareType`
    type = db.Column(db.Enum(BareMetalHardwareType), nullable=False)

    handler_id = db.Column(
        db.Integer, db.ForeignKey(f"{_BM_TABLE_NAME_HANDLER}.id"), nullable=False
    )
    #: :type: :class:`BareMetalHandler`
    handler = db.relationship("BareMetalHandler", back_populates="hosts")
    handler_uuid = db.Column(postgresql.UUID)
    handler_data = db.Column(db.JSON)

    ipmi_username = db.Column(db.String(128), nullable=False)
    ipmi_password = db.Column(db.String(128), nullable=False)
    ipmi_address = db.Column(db.String(128), nullable=False)
    ipmi_port = db.Column(db.String(128), nullable=False)

    #: :type: :class:`BareMetalProvision`
    deployments = db.relationship("BareMetalProvision", back_populates="host")

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": BareMetalHardwareType.GENERIC,
    }

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        del data['ipmi_password']
        return data

    @classmethod
    def _credential_columns(cls) -> [str]:
        return ["ipmi_address", "ipmi_password", "ipmi_port", "ipmi_username"]

    def get_credentials(self) -> dict[str, str]:
        data = {}
        for column in self._credential_columns():
            value = getattr(self, column)
            if value is not None:
                data[column] = value
        return data

    def is_available(self) -> bool:
        return self.status is BareMetalHostStatus.AVAILABLE and self.handler.is_available()

    def can_be_enrolled(self) -> bool:
        return self.status is BareMetalHostStatus.NON_ENROLLED and self.handler.is_available()

    def _get_handler_node(self) -> IronicNode:
        # TODO: make this handler-agnostic
        if self.status is BareMetalHostStatus.NON_ENROLLED or not self.handler_uuid:
            raise RuntimeError("Not able to fetch handler data")
        return self.handler.get_client().get_node(self.handler_uuid)

    @property
    def power_state(self) -> Optional[str]:
        return self._get_handler_node().power_state

    @property
    def boot_type(self) -> str:
        if self.uefi_secure_boot:
            return BareMetalBootType.UEFI_SECURE_BOOT

        if self.uefi:
            return BareMetalBootType.UEFI

        if self.legacy_bios:
            return BareMetalBootType.LEGACY_BIOS


class BareMetalHostRedfish(BareMetalHost):
    __tablename__ = _BM_TABLE_NAME_HOST_REDFISH

    id = db.Column(
        db.Integer, db.ForeignKey(f"{BareMetalHost.__tablename__}.id"), primary_key=True
    )

    redfish_address = db.Column(db.String(128), nullable=False)
    redfish_username = db.Column(db.String(128), nullable=False)
    redfish_password = db.Column(db.String(128), nullable=False)
    redfish_system_id = db.Column(db.String(128), nullable=False)
    redfish_verify_ca = db.Column(
        db.Boolean, server_default=expression.true(), nullable=False
    )

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        del data['redfish_password']
        return data

    @classmethod
    def _credential_columns(cls) -> [str]:
        return super()._credential_columns() + [
            "redfish_address",
            "redfish_password",
            "redfish_system_id",
            "redfish_username",
            "redfish_verify_ca",
        ]

    __mapper_args__ = {
        "polymorphic_identity": BareMetalHardwareType.REDFISH,
    }


class BareMetalHostDrac(BareMetalHost):
    __tablename__ = _BM_TABLE_NAME_HOST_DRAC

    id = db.Column(
        db.Integer, db.ForeignKey(f"{BareMetalHost.__tablename__}.id"), primary_key=True
    )

    redfish_address = db.Column(db.String(128))
    redfish_username = db.Column(db.String(128))
    redfish_password = db.Column(db.String(128))
    redfish_system_id = db.Column(db.String(128))
    redfish_verify_ca = db.Column(db.Boolean, server_default=expression.true())

    drac_address = db.Column(db.String(128), nullable=False)
    drac_username = db.Column(db.String(128), nullable=False)
    drac_password = db.Column(db.String(128), nullable=False)

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        del data['redfish_password']
        del data['drac_password']
        return data

    @classmethod
    def _credential_columns(cls) -> [str]:
        return super()._credential_columns() + [
            "redfish_address",
            "redfish_password",
            "redfish_system_id",
            "redfish_username",
            "redfish_verify_ca",
            "drac_address",
            "drac_username",
            "drac_password",
        ]

    __mapper_args__ = {
        "polymorphic_identity": BareMetalHardwareType.DRAC,
    }


def get_bm_metrics():
    rows = []

    for model in [
        BareMetalHostRedfish(),
        BareMetalHostDrac()
    ]:
        sub_metrics = model.query(func.count(model.id)).group_by(
            model.arch,
            model.status,
        ).all()

        for row in sub_metrics:
            rows.append(row)

    by_arch = {}
    for row in rows:
        sub_status = {}
        if row.arch in by_arch:
            sub_status = by_arch[row.arch]

        sub_count = 0
        if row.status in sub_status:
            sub_count = sub_status[row.status]

        sub_count += row.count

        sub_status[row.status] = sub_count
        by_arch[row.arch] = sub_status

    # items will be returned in this dict pattern:
    # {arch="x86", provisioned=10, pending=5 ...}
    r = []
    for arch, arch_item in by_arch.items():
        rdict = {}
        rdict["arch"] = arch

        for status, the_count in arch_item.items():
            rdict[status] = the_count

        r.append(rdict)

    return r
